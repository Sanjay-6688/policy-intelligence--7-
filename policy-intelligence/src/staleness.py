"""
staleness.py
-------------
Flags policies that are stale by metadata (last_reviewed older than the
18-month threshold called out in the problem statement) or by content
(references to deprecated technologies/standards).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import date
from typing import Optional

STALE_THRESHOLD_MONTHS = 18

# Pattern -> (human label, why it's deprecated)
DEPRECATED_REFERENCES = [
    (r"\bTLS\s?1\.0\b", "TLS 1.0", "Deprecated by IETF RFC 8996 (2021); superseded by TLS 1.2+"),
    (r"\bTLS\s?1\.1\b", "TLS 1.1", "Deprecated by IETF RFC 8996 (2021); superseded by TLS 1.2+"),
    (r"\bSHA-?1\b", "SHA-1", "Cryptographically broken since 2017 (SHAttered); superseded by SHA-256"),
    (r"Windows Server 2012", "Windows Server 2012", "End of extended support (Oct 2023)"),
    (r"NIST SP 800-53 Rev(?:ision)? 4", "NIST SP 800-53 Rev 4",
     "Superseded by NIST SP 800-53 Rev 5 (published Sept 2020)"),
]


@dataclass
class StalenessFinding:
    policy_id: str
    policy_title: str
    last_reviewed: str
    months_since_review: float
    review_status: str          # "current" | "aging" | "stale" | "critical"
    deprecated_references: list
    staleness_score: int        # 0-100, higher = more stale
    summary: str

    def to_dict(self):
        return asdict(self)


def _months_between(d1: date, d2: date) -> float:
    return (d2.year - d1.year) * 12 + (d2.month - d1.month) + (d2.day - d1.day) / 30.0


def _find_deprecated_references(body: str) -> list[dict]:
    found = []
    for pattern, label, reason in DEPRECATED_REFERENCES:
        if re.search(pattern, body, re.IGNORECASE):
            found.append({"reference": label, "reason": reason})
    return found


def assess_policy_staleness(policy: dict, as_of: Optional[date] = None) -> StalenessFinding:
    as_of = as_of or date.today()
    meta = policy["metadata"]
    policy_id = meta.get("policy_id", "UNKNOWN")
    policy_title = meta.get("title", "Untitled Policy")

    last_reviewed_raw = meta.get("last_reviewed")
    if hasattr(last_reviewed_raw, "isoformat"):
        last_reviewed = last_reviewed_raw
    else:
        last_reviewed = date.fromisoformat(str(last_reviewed_raw))

    months_since = round(_months_between(last_reviewed, as_of), 1)
    deprecated_refs = _find_deprecated_references(policy["body"])

    # Score: review-age component (capped) + deprecated-reference penalty
    age_component = min(60, months_since / STALE_THRESHOLD_MONTHS * 30)
    deprecated_component = min(40, len(deprecated_refs) * 20)
    staleness_score = int(round(age_component + deprecated_component))

    if months_since >= 48 or (months_since >= 24 and deprecated_refs):
        review_status = "critical"
    elif months_since >= STALE_THRESHOLD_MONTHS:
        review_status = "stale"
    elif months_since >= 12:
        review_status = "aging"
    else:
        review_status = "current"

    parts = [f"Last reviewed {months_since:.0f} months ago ({review_status})."]
    if deprecated_refs:
        ref_names = ", ".join(r["reference"] for r in deprecated_refs)
        parts.append(f"References deprecated standard(s): {ref_names}.")
    summary = " ".join(parts)

    return StalenessFinding(
        policy_id=policy_id,
        policy_title=policy_title,
        last_reviewed=str(last_reviewed),
        months_since_review=months_since,
        review_status=review_status,
        deprecated_references=deprecated_refs,
        staleness_score=staleness_score,
        summary=summary,
    )


def assess_all(policies: list[dict], as_of: Optional[date] = None) -> list[StalenessFinding]:
    findings = [assess_policy_staleness(p, as_of=as_of) for p in policies]
    findings.sort(key=lambda f: f.staleness_score, reverse=True)
    return findings
