"""
classifier.py
--------------
Step 3 of the pipeline: for each candidate obligation pair, decide the
relationship and produce an audit-ready explanation.

Relationship labels (matching the problem statement's Option A spec):
    CONFLICT       - contradictory requirements that are NOT reconciled by
                      scope or an explicit exception clause
    REDUNDANT       - same obligation, same scope, restated in different words
    COMPLEMENTARY   - related obligations that coexist by design (a scoped
                      exception, an authorized override process, or a
                      reinforcing requirement in a different scope)
    UNRELATED       - candidate pair that turned out not to be meaningfully
                      related (kept for false-positive transparency)

Two backends:
    classify_with_llm()        - real LLM reasoning (Option A "advanced" path)
    classify_with_heuristic()  - deterministic rules mirroring Option B, used
                                  as an offline fallback / sanity baseline.

Both produce the same schema so the graph/dashboard layer doesn't care
which one ran.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from .extraction import Obligation
from .similarity import CandidatePair
from .llm_client import LLMClient, LLMError

# Topic pairs that are governance-related even though the keyword-based
# `topic` field differs (e.g. retention vs. deletion are in tension by
# nature). Similarity.py also consults this so cross-topic pairs aren't
# dropped before they ever reach the classifier.
CROSS_TOPIC_GROUPS = [
    {"data_retention", "data_deletion"},
    {"password_rotation", "mfa"},
    {"admin_console_auth", "mfa"},
    {"encryption_in_transit", "legacy_crypto"},
    {"backup", "cloud_storage_access"},
]


def topics_related(topic_a: str, topic_b: str) -> bool:
    if topic_a == topic_b:
        return True
    pair = {topic_a, topic_b}
    return any(pair == group or pair.issubset(group) for group in CROSS_TOPIC_GROUPS)


@dataclass
class Relationship:
    pair_id: str
    obligation_a_id: str
    obligation_b_id: str
    policy_a: str
    policy_b: str
    section_a: str
    section_b: str
    text_a: str
    text_b: str
    topic: str
    relationship: str      # CONFLICT | REDUNDANT | COMPLEMENTARY | UNRELATED
    confidence: float
    explanation: str
    similarity: float
    match_reason: str

    def to_dict(self):
        return asdict(self)


# ----------------------------------------------------------------------
# Offline heuristic backend (mirrors Option B rule engine, used as fallback)
# ----------------------------------------------------------------------
# Coarse, catch-all topics where "same topic + opposite polarity" is too weak a
# signal for an automatic CONFLICT verdict (they bundle several distinct
# underlying actions, e.g. password_hygiene covers reuse rules, complexity
# rules, and general guidance, which can legitimately have mixed polarity
# without contradicting each other). Downgrade to COMPLEMENTARY-for-review
# instead of asserting a conflict a human would likely reject.
GENERIC_TOPICS = {"password_hygiene", "general"}


def _classify_pair_heuristic(pair: CandidatePair) -> Relationship:
    a, b = pair.a, pair.b
    topic = a.topic if a.topic == b.topic else f"{a.topic}/{b.topic}"

    related = topics_related(a.topic, b.topic)
    if not related:
        return Relationship(
            pair_id=f"{a.obligation_id}__{b.obligation_id}",
            obligation_a_id=a.obligation_id, obligation_b_id=b.obligation_id,
            policy_a=a.policy_id, policy_b=b.policy_id,
            section_a=a.section, section_b=b.section,
            text_a=a.text, text_b=b.text, topic=topic,
            relationship="UNRELATED", confidence=0.55,
            explanation=(
                f"Obligations share vocabulary (cosine similarity {pair.similarity}) "
                f"but cover different governance topics ('{a.topic}' vs '{b.topic}'). "
                "No action needed; kept for transparency."
            ),
            similarity=pair.similarity, match_reason=pair.match_reason,
        )

    scope_differs = a.scope != b.scope
    has_condition = bool(a.conditions or b.conditions)
    condition_text = a.conditions or b.conditions

    # Guard: "must be enabled" (require) and "must not be disabled" (prohibit)
    # are the SAME real-world mandate stated two ways, not a contradiction.
    # Naive polarity comparison would otherwise flag these as CONFLICT.
    a_low, b_low = a.text.lower(), b.text.lower()
    same_intent_opposite_phrasing = (
        ("enable" in a_low and "disab" in b_low) or ("enable" in b_low and "disab" in a_low)
    )

    if a.polarity != b.polarity and same_intent_opposite_phrasing:
        relationship = "REDUNDANT"
        confidence = 0.75
        explanation = (
            f"{a.policy_id} §{a.section} and {b.policy_id} §{b.section} both govern '{topic}': one "
            "requires the control stay enabled, the other prohibits disabling it. These are the same "
            "underlying mandate expressed in opposite grammatical form, not a genuine contradiction."
        )
    elif a.polarity != b.polarity:
        if a.topic in GENERIC_TOPICS or b.topic in GENERIC_TOPICS:
            relationship = "COMPLEMENTARY"
            confidence = 0.5
            explanation = (
                f"{a.policy_id} §{a.section} and {b.policy_id} §{b.section} both touch on '{topic}' "
                "with superficially opposite polarity, but the topic is broad enough (general password/"
                "credential guidance rather than one specific rule) that this doesn't read as a real "
                "contradiction. Flagged for human review rather than auto-classified as CONFLICT."
            )
        # One side requires X, the other prohibits/exempts X.
        elif has_condition:
            relationship = "COMPLEMENTARY"
            confidence = 0.82 if scope_differs else 0.7
            scope_note = (
                f"narrows this to '{b.scope}' " if scope_differs else "applies within the same scope "
            )
            explanation = (
                f"{a.policy_id} §{a.section} ('{a.text}') requires '{topic}', while {b.policy_id} "
                f"§{b.section} ('{b.text}') appears to prohibit it — but {b.policy_id} defines an "
                f"explicit, authorized exception/process: \"{condition_text}\". This reads as a "
                "reconciled carve-out rather than an unaddressed contradiction — confirm the exception "
                "process is still actively enforced."
            )
            relationship = "COMPLEMENTARY"
            confidence = 0.82
            explanation = (
                f"{b.policy_id} carves out a scoped exception to {a.policy_id}'s "
                f"'{topic}' requirement for '{b.scope}' rather than contradicting it outright. "
                f"{a.policy_id} §{a.section} applies to '{a.scope}'; {b.policy_id} §{b.section} "
                f"narrows this to '{b.scope}', conditioned on: \"{condition_text}\". "
                "This reads as an authorized carve-out, not an unreconciled conflict — "
                "but confirm the exception is still actively enforced."
            )
        else:
            relationship = "CONFLICT"
            confidence = 0.88 if not scope_differs else 0.74
            scope_note = (
                f"Both apply to overlapping scope ('{a.scope}' vs '{b.scope}')."
                if not scope_differs else
                f"Scopes differ ('{a.scope}' vs '{b.scope}') but no exception clause reconciles them — "
                "this looks like an unaddressed gap rather than an intentional carve-out."
            )
            explanation = (
                f"{a.policy_id} §{a.section} ('{a.text}') requires '{topic}', while "
                f"{b.policy_id} §{b.section} ('{b.text}') prohibits or exempts the same obligation. "
                f"{scope_note} These are both active, approved policies."
            )
    else:
        # Same polarity - either redundant, a reinforcing complement, or (rarely) a parameter conflict.
        # IMPORTANT: check for an explicit exception/process clause FIRST. An obligation like
        # "...may authorize suspension for 4 hours, provided X" is an authorized PROCESS, not a
        # competing baseline parameter -- comparing its duration against an unrelated retention
        # period (e.g. "retained for 3 years") would compare unlike quantities and produce a
        # nonsensical false-positive conflict.
        freq_conflict = (
            a.frequency and b.frequency and a.frequency != b.frequency and not scope_differs
        )
        if has_condition:
            relationship = "COMPLEMENTARY"
            confidence = 0.78
            scope_note = (
                f"applying to a different scope ('{a.scope}' vs '{b.scope}')" if scope_differs
                else "within the same general scope"
            )
            explanation = (
                f"{a.policy_id} §{a.section} and {b.policy_id} §{b.section} both govern '{topic}', "
                f"{scope_note}. One of them defines an authorized process/exception: "
                f"\"{condition_text}\". This reads as a reconciled carve-out rather than a competing "
                "baseline rule — confirm the exception process is still active."
            )
        elif freq_conflict:
            relationship = "CONFLICT"
            confidence = 0.8
            explanation = (
                f"{a.policy_id} §{a.section} specifies '{a.frequency}' while {b.policy_id} §{b.section} "
                f"specifies '{b.frequency}' for the same '{topic}' obligation and overlapping scope "
                f"('{a.scope}'). These parameters cannot both be satisfied simultaneously."
            )
        elif not scope_differs and a.strength == b.strength:
            relationship = "REDUNDANT"
            confidence = 0.8
            explanation = (
                f"{a.policy_id} §{a.section} and {b.policy_id} §{b.section} impose the same "
                f"'{topic}' obligation ('{a.strength}') on the same scope ('{a.scope}') in "
                "different wording. Consider consolidating ownership or cross-referencing "
                "one policy from the other to reduce maintenance burden."
            )
        else:
            relationship = "COMPLEMENTARY"
            confidence = 0.65
            explanation = (
                f"{a.policy_id} §{a.section} and {b.policy_id} §{b.section} both address '{topic}' "
                f"in different scopes ('{a.scope}' vs '{b.scope}') without contradicting each other. "
                "Related but not duplicative."
            )

    return Relationship(
        pair_id=f"{a.obligation_id}__{b.obligation_id}",
        obligation_a_id=a.obligation_id, obligation_b_id=b.obligation_id,
        policy_a=a.policy_id, policy_b=b.policy_id,
        section_a=a.section, section_b=b.section,
        text_a=a.text, text_b=b.text, topic=topic,
        relationship=relationship, confidence=confidence, explanation=explanation,
        similarity=pair.similarity, match_reason=pair.match_reason,
    )


def classify_with_heuristic(pairs: list[CandidatePair]) -> list[Relationship]:
    return [_classify_pair_heuristic(p) for p in pairs]


# ----------------------------------------------------------------------
# LLM backend
# ----------------------------------------------------------------------
CLASSIFY_SYSTEM_PROMPT = """You are a senior policy governance analyst. You will be shown pairs of \
obligations extracted from two different enterprise policies. For each pair, classify the \
relationship as exactly one of:

  - CONFLICT: contradictory requirements that are not reconciled by scope or an explicit exception.
  - REDUNDANT: the same obligation restated in different words, same scope.
  - COMPLEMENTARY: related obligations that coexist by design (e.g. a scoped exception, an \
authorized override process, or a reinforcing requirement in a different scope).
  - UNRELATED: not meaningfully related despite superficial keyword overlap.

Reason carefully about SCOPE (who/what each obligation applies to) and CONDITIONS (explicit \
exception or override clauses) before concluding CONFLICT — a scoped, conditioned exception is \
COMPLEMENTARY, not a conflict, even if the raw actions look opposite. High precision matters: false \
CONFLICT alerts erode trust with policy owners, so only use CONFLICT when the contradiction is real \
and unreconciled.

For each pair return a JSON object:
{
  "pair_id": "<obligation_a_id>__<obligation_b_id>",
  "relationship": "CONFLICT" | "REDUNDANT" | "COMPLEMENTARY" | "UNRELATED",
  "confidence": 0.0-1.0,
  "explanation": "1-3 sentence audit-ready explanation citing policy IDs and section numbers"
}

Return ONLY a JSON array, one object per pair, in the same order given. No prose, no markdown fences.
"""


def _pair_to_prompt_block(pair: CandidatePair, idx: int) -> str:
    a, b = pair.a, pair.b
    return (
        f"Pair {idx}:\n"
        f"  A: [{a.obligation_id}] {a.policy_id} §{a.section} (\"{a.policy_title}\") "
        f"scope={a.scope} strength={a.strength} polarity={a.polarity} "
        f"conditions={a.conditions!r}\n  text: \"{a.text}\"\n"
        f"  B: [{b.obligation_id}] {b.policy_id} §{b.section} (\"{b.policy_title}\") "
        f"scope={b.scope} strength={b.strength} polarity={b.polarity} "
        f"conditions={b.conditions!r}\n  text: \"{b.text}\"\n"
    )


def classify_with_llm(pairs: list[CandidatePair], client: LLMClient, batch_size: int = 6) -> list[Relationship]:
    results: list[Relationship] = []
    n_batches = (len(pairs) + batch_size - 1) // batch_size
    for batch_num, start in enumerate(range(0, len(pairs), batch_size), 1):
        batch = pairs[start:start + batch_size]
        print(f"[classification] batch {batch_num}/{n_batches} ({len(batch)} pairs)...", end=" ", flush=True)
        prompt = "\n".join(_pair_to_prompt_block(p, i) for i, p in enumerate(batch))
        try:
            raw = client.complete_json(CLASSIFY_SYSTEM_PROMPT, prompt, max_tokens=3072)
        except LLMError as e:
            print(f"LLM error, falling back to heuristic for this batch ({e})", flush=True)
            results.extend(classify_with_heuristic(batch))
            continue
        print("done", flush=True)

        raw_list = raw if isinstance(raw, list) else []
        for i, pair in enumerate(batch):
            item = raw_list[i] if i < len(raw_list) else None
            if not item:
                results.append(_classify_pair_heuristic(pair))
                continue
            a, b = pair.a, pair.b
            topic = a.topic if a.topic == b.topic else f"{a.topic}/{b.topic}"
            results.append(Relationship(
                pair_id=item.get("pair_id") or f"{a.obligation_id}__{b.obligation_id}",
                obligation_a_id=a.obligation_id, obligation_b_id=b.obligation_id,
                policy_a=a.policy_id, policy_b=b.policy_id,
                section_a=a.section, section_b=b.section,
                text_a=a.text, text_b=b.text, topic=topic,
                relationship=item.get("relationship", "UNRELATED"),
                confidence=float(item.get("confidence", 0.5)),
                explanation=item.get("explanation", ""),
                similarity=pair.similarity, match_reason=pair.match_reason,
            ))
    return results


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------
def classify_all(pairs: list[CandidatePair], client: LLMClient) -> list[Relationship]:
    if client.is_live:
        return classify_with_llm(pairs, client)
    return classify_with_heuristic(pairs)
