"""
extraction.py
--------------
Step 1 of the pipeline: turn free-text policy clauses into structured
"obligation" records.

    "All employees must rotate passwords every 90 days."
        -> {
             "obligation": "rotate_password",
             "topic": "password_rotation",
             "scope": "all_employees",
             "strength": "mandatory",
             "polarity": "require",
             "frequency": "90_days",
             ...
           }

Two extraction backends are provided:
  - extract_with_llm()      -> real LLM call, used when LLMClient.is_live
  - extract_with_heuristic() -> deterministic regex/keyword extraction,
                                 used as an offline fallback so the pipeline
                                 always produces a complete, demoable run.

Both return the same schema (see OBLIGATION_SCHEMA_DOC below), which is
what makes the rest of the pipeline (similarity, classification, graph)
agnostic to which backend produced the data.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import frontmatter  # python-frontmatter

from .llm_client import LLMClient, LLMError

OBLIGATION_SCHEMA_DOC = """
{
  "obligation_id": "POL-001-3.1-o1",   // unique, stable id
  "policy_id": "POL-001",
  "policy_title": "Password Policy",
  "section": "3.1",
  "text": "<verbatim clause sentence>",
  "obligation": "rotate_password",     // short snake_case predicate
  "topic": "password_rotation",        // coarse governance topic, used for candidate pairing
  "scope": "all_employees",            // who/what this obligation applies to
  "strength": "mandatory",             // mandatory | prohibited | recommended
  "polarity": "require",               // require | prohibit
  "frequency": "90_days",              // normalized duration, or null
  "conditions": null                   // free-text exception/condition clause, or null
}
"""

# Sentence-level obligation triggers (kept broad; both backends use this to
# locate candidate sentences before deeper parsing).
OBLIGATION_TRIGGERS = re.compile(
    r"\b(must|shall|required|prohibited|may not|should|recommended|"
    r"encouraged|exempt|not require|deprecated|expected)\b",
    re.IGNORECASE,
)

# Topic keyword map used by the offline heuristic (and to sanity-check LLM output).
TOPIC_KEYWORDS = {
    # NOTE: order matters. _guess_topic() returns the FIRST matching topic,
    # so specific/narrow keyword sets must precede generic/broad ones.
    # "password_hygiene" (bare "password") is deliberately last so it only
    # catches leftover generic mentions not already claimed by a more
    # specific topic (rotation, MFA, admin-console auth, etc.) -- otherwise
    # every sentence that merely contains the word "password" gets wrongly
    # bundled into rotation/MFA conflict comparisons.
    "password_rotation": ["password rotat", "rotate password", "credential refresh", "periodic password rotation"],
    "mfa": ["multi-factor", "mfa"],
    "encryption_at_rest": ["encrypt", "aes-256", "aes256", "encryption at rest"],
    "encryption_in_transit": ["tls", "in transit"],
    "logging_monitoring": ["logging", "cloudtrail", "audit log", "monitoring", "log data"],
    "vpn_remote_access": ["vpn", "remote access", "split-tunnel"],
    "backup": ["backup"],
    "data_retention": ["retain", "retention"],
    "data_deletion": ["delete", "erasure", "right to be forgotten", "disposal", "destroyed"],
    "firewall_network": ["firewall", "inbound", "security group", "segmentation"],
    "admin_console_auth": ["admin console", "administrative console"],
    "vendor_risk": ["vendor", "third-party", "third party"],
    "legacy_crypto": ["sha-1", "sha1"],
    "cloud_storage_access": ["storage bucket", "publicly accessible", "object storage", "blob storage"],
    "key_management": ["key management", "kms", "hsm", "encryption keys"],
    "access_review": ["least privilege", "access review", "deprovision"],
    "password_hygiene": ["password"],
}

SCOPE_PATTERNS = [
    ("cloud_accounts", r"cloud[-\s]hosted|cloud account|cloud storage|s3|azure blob"),
    ("cicd_pipelines", r"ci/cd pipeline|automated pipeline|service account"),
    ("privileged_accounts", r"privileged|administrative account"),
    ("legacy_admin_console", r"legacy admin(istrative)? console"),
    ("eu_data_subjects", r"eu data subject|gdpr"),
    ("all_employees", r"all employees|employees and contractors|all employees, contractors"),
    ("production_systems", r"production system"),
    ("confidential_restricted_data", r"confidential.{0,20}restricted|restricted.{0,20}confidential|confidential or restricted"),
    ("vendors", r"vendor"),
]

DURATION_RE = re.compile(
    r"(\d+)[\s-](day|days|hour|hours|month|months|year|years)", re.IGNORECASE
)


@dataclass
class Obligation:
    obligation_id: str
    policy_id: str
    policy_title: str
    section: str
    text: str
    obligation: str
    topic: str
    scope: str
    strength: str
    polarity: str
    frequency: Optional[str] = None
    conditions: Optional[str] = None

    def to_dict(self):
        return asdict(self)


# ----------------------------------------------------------------------
# Policy loading
# ----------------------------------------------------------------------
def load_policies(policies_dir: Path) -> list[dict]:
    """Load every markdown policy file with YAML frontmatter metadata."""
    policies = []
    for path in sorted(Path(policies_dir).glob("*.md")):
        post = frontmatter.load(path)
        policies.append({
            "path": str(path),
            "metadata": dict(post.metadata),
            "body": post.content,
        })
    return policies


def split_sections(body: str) -> list[tuple[str, str]]:
    """
    Split policy body into (section_number, section_text) chunks based on
    markdown '### N.N Heading' patterns, falling back to the whole body.
    """
    pattern = re.compile(r"^###\s+([\d.]+)\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(body))
    if not matches:
        return [("0", body)]
    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_num = m.group(1)
        section_text = body[start:end].strip()
        sections.append((section_num, section_text))
    return sections


def split_sentences(text: str) -> list[str]:
    # Simple sentence splitter tuned for policy prose (avoids breaking on "e.g.", "i.e.")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    protected = text.replace("e.g.", "e_g_").replace("i.e.", "i_e_")
    raw_sentences = re.split(r"(?<=[.!?])\s+", protected)
    return [s.replace("e_g_", "e.g.").replace("i_e_", "i.e.").strip() for s in raw_sentences if s.strip()]


# ----------------------------------------------------------------------
# Offline heuristic extraction backend
# ----------------------------------------------------------------------
def _guess_topic(sentence: str) -> str:
    low = sentence.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in low for kw in keywords):
            # "logging_monitoring" is a broad bucket that otherwise conflates two
            # different obligation dimensions: how long logs must be RETAINED
            # (a duration) vs whether logging must stay ENABLED/never be
            # DISABLED (an availability guarantee). Comparing those two as if
            # they were the same parameter produces nonsensical conflicts
            # ("3 years" vs "must not be disabled"), so split them here.
            if topic == "logging_monitoring" and ("retain" in low or "retention" in low):
                return "log_retention"
            return topic
    return "general"


def _guess_scope(sentence: str) -> str:
    low = sentence.lower()
    for scope, pat in SCOPE_PATTERNS:
        if re.search(pat, low):
            return scope
    return "general"


def _guess_strength_polarity(sentence: str) -> tuple[str, str]:
    low = sentence.lower()
    if re.search(r"\bmust not\b|\bshall not\b|\bprohibited\b|\bmay not\b|\bnot require|\bexempt\b|\bdeprecated\b", low):
        return "prohibited", "prohibit"
    if re.search(r"\bmust\b|\bshall\b|\brequired\b|\brequires?\b", low):
        return "mandatory", "require"
    if re.search(r"\bshould\b|\brecommended\b|\bencouraged\b|\bexpected\b|\bmay\b", low):
        return "recommended", "require"
    return "mandatory", "require"


def _guess_frequency(sentence: str) -> Optional[str]:
    m = DURATION_RE.search(sentence)
    if not m:
        return None
    n, unit = m.group(1), m.group(2).lower()
    if not unit.endswith("s"):
        unit += "s"
    return f"{n}_{unit}"


def _guess_obligation_predicate(sentence: str, topic: str) -> str:
    verb_map = {
        "password_rotation": "rotate_password",
        "password_hygiene": "maintain_password_hygiene",
        "mfa": "enforce_mfa",
        "encryption_at_rest": "encrypt_data_at_rest",
        "encryption_in_transit": "encrypt_data_in_transit",
        "logging_monitoring": "maintain_logging",
        "log_retention": "retain_logs",
        "vpn_remote_access": "use_vpn",
        "data_retention": "retain_data",
        "data_deletion": "delete_data",
        "backup": "maintain_backup",
        "firewall_network": "restrict_network_access",
        "admin_console_auth": "authenticate_admin_console",
        "vendor_risk": "assess_vendor_risk",
        "legacy_crypto": "use_legacy_crypto",
        "cloud_storage_access": "restrict_storage_access",
        "key_management": "manage_encryption_keys",
        "access_review": "review_access",
    }
    return verb_map.get(topic, "general_obligation")


def extract_with_heuristic(policy: dict) -> list[Obligation]:
    meta = policy["metadata"]
    policy_id = meta.get("policy_id", "UNKNOWN")
    policy_title = meta.get("title", "Untitled Policy")
    obligations = []
    counter = 0

    for section_num, section_text in split_sections(policy["body"]):
        for sentence in split_sentences(section_text):
            if not OBLIGATION_TRIGGERS.search(sentence):
                continue
            counter += 1
            topic = _guess_topic(sentence)
            scope = _guess_scope(sentence)
            strength, polarity = _guess_strength_polarity(sentence)
            frequency = _guess_frequency(sentence)
            obligation_pred = _guess_obligation_predicate(sentence, topic)

            # crude "conditions" extraction: text after "provided", "except", "unless"
            cond_match = re.search(r"\b(provided|except|unless|if required)\b(.*)", sentence, re.IGNORECASE)
            conditions = cond_match.group(0).strip() if cond_match else None

            obligations.append(Obligation(
                obligation_id=f"{policy_id}-{section_num}-o{counter}",
                policy_id=policy_id,
                policy_title=policy_title,
                section=section_num,
                text=sentence,
                obligation=obligation_pred,
                topic=topic,
                scope=scope,
                strength=strength,
                polarity=polarity,
                frequency=frequency,
                conditions=conditions,
            ))
    return obligations


# ----------------------------------------------------------------------
# LLM extraction backend
# ----------------------------------------------------------------------
EXTRACTION_SYSTEM_PROMPT = f"""You are a policy analyst extracting structured obligations from \
enterprise security/compliance policy text.

For every sentence that expresses an obligation, permission, prohibition, or exception \
(look for: must, shall, required, prohibited, may not, should, recommended, exempt, deprecated), \
emit one JSON object matching this schema:

{OBLIGATION_SCHEMA_DOC}

Rules:
- obligation_id must follow "<policy_id>-<section>-o<n>" where n increments per policy.
- topic should be a short, reusable snake_case governance topic (e.g. password_rotation, mfa, \
encryption_at_rest, logging_monitoring, vpn_remote_access, data_retention, data_deletion, backup, \
firewall_network, admin_console_auth, vendor_risk, legacy_crypto). Reuse the same topic string \
across policies when they govern the same subject matter, even if worded differently.
- scope should capture WHO or WHAT the obligation applies to (e.g. all_employees, cloud_accounts, \
cicd_pipelines, privileged_accounts, eu_data_subjects, production_systems). Use "general" if unscoped.
- polarity is "require" if the clause mandates/recommends doing something, "prohibit" if it \
forbids/exempts/deprecates doing something.
- conditions should capture any exception clause verbatim (e.g. "provided replication is verified \
quarterly"), or null.
- Return ONLY a JSON array of obligation objects. No prose, no markdown fences.
"""


def extract_with_llm(policy: dict, client: LLMClient) -> list[Obligation]:
    meta = policy["metadata"]
    policy_id = meta.get("policy_id", "UNKNOWN")
    policy_title = meta.get("title", "Untitled Policy")

    user_prompt = (
        f"Policy ID: {policy_id}\nPolicy Title: {policy_title}\n\n"
        f"Policy text:\n{policy['body']}"
    )
    try:
        raw = client.complete_json(EXTRACTION_SYSTEM_PROMPT, user_prompt, max_tokens=4096)
    except LLMError as e:
        # Graceful degrade: fall back to heuristic for this document.
        print(f"[LLM error, using heuristic fallback for this policy: {e}]", end=" ", flush=True)
        return extract_with_heuristic(policy)

    obligations = []
    for i, item in enumerate(raw if isinstance(raw, list) else []):
        try:
            obligations.append(Obligation(
                obligation_id=item.get("obligation_id") or f"{policy_id}-x-o{i}",
                policy_id=policy_id,
                policy_title=policy_title,
                section=str(item.get("section", "0")),
                text=item.get("text", ""),
                obligation=item.get("obligation", "general_obligation"),
                topic=item.get("topic", "general"),
                scope=item.get("scope", "general"),
                strength=item.get("strength", "mandatory"),
                polarity=item.get("polarity", "require"),
                frequency=item.get("frequency"),
                conditions=item.get("conditions"),
            ))
        except Exception:
            continue
    return obligations or extract_with_heuristic(policy)


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------
def extract_all(policies_dir: Path, client: LLMClient) -> list[Obligation]:
    policies = load_policies(policies_dir)
    all_obligations: list[Obligation] = []
    for i, policy in enumerate(policies, 1):
        policy_id = policy["metadata"].get("policy_id", "?")
        print(f"[extraction] ({i}/{len(policies)}) {policy_id}...", end=" ", flush=True)
        if client.is_live:
            obligations = extract_with_llm(policy, client)
        else:
            obligations = extract_with_heuristic(policy)
        print(f"{len(obligations)} obligation(s)", flush=True)
        all_obligations.extend(obligations)
    return all_obligations
