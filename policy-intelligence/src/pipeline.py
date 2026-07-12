"""
pipeline.py
------------
Orchestrates the full Policy Conflict & Staleness Detector pipeline:

    load policies
      -> extract obligations           (extraction.py)
      -> find candidate pairs          (similarity.py)
      -> classify relationships        (classifier.py)
      -> assess staleness              (staleness.py)
      -> map to compliance controls    (compliance_mapping.py)
      -> build knowledge graph         (graph_builder.py)
      -> write outputs/*.json for the dashboard

Run with:  python scripts/run_pipeline.py
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from . import compliance_mapping
from .classifier import classify_all
from .extraction import extract_all, load_policies, Obligation
from .graph_builder import build_graph, graph_to_node_link
from .llm_client import LLMClient
from .similarity import find_candidate_pairs
from .staleness import assess_all
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
POLICIES_DIR = ROOT / "data" / "policies"
OUTPUTS_DIR = ROOT / "outputs"

# Fixed reference date for staleness scoring, simulating "the audit runs as of
# this date." Pinning this (rather than using wall-clock date.today()) keeps
# demo output meaningful and reproducible regardless of when the pipeline is
# actually executed relative to the synthetic policy corpus's dates.
AS_OF_DATE = date(2025, 6, 1)


def _severity_for_relationship(rel: str) -> str:
    return {"CONFLICT": "HIGH", "REDUNDANT": "MEDIUM", "COMPLEMENTARY": "INFO", "UNRELATED": "INFO"}.get(rel, "INFO")


def run_pipeline(policies_dir: Path = POLICIES_DIR, outputs_dir: Path = OUTPUTS_DIR) -> dict:
    t0 = time.time()
    outputs_dir.mkdir(parents=True, exist_ok=True)
    client = LLMClient()

    print(f"[pipeline] mode={'LIVE (' + client.provider + ')' if client.is_live else 'OFFLINE (heuristic)'}")

    # 1. Load & extract -----------------------------------------------------
    policies = load_policies(policies_dir)
    print(f"[pipeline] loaded {len(policies)} policies")

    obligations: list[Obligation] = extract_all(policies_dir, client)
    print(f"[pipeline] extracted {len(obligations)} obligations")

    # 2. Candidate pairs ------------------------------------------------------
    candidate_pairs = find_candidate_pairs(obligations)
    print(f"[pipeline] generated {len(candidate_pairs)} candidate cross-policy pairs")

    # 3. Classify -------------------------------------------------------------
    relationships = classify_all(candidate_pairs, client)
    counts = {"CONFLICT": 0, "REDUNDANT": 0, "COMPLEMENTARY": 0, "UNRELATED": 0}
    for r in relationships:
        counts[r.relationship] = counts.get(r.relationship, 0) + 1
    print(f"[pipeline] classified relationships: {counts}")

    # 4. Staleness --------------------------------------------------------------
    staleness_findings = assess_all(policies, as_of=AS_OF_DATE)
    stale_count = sum(1 for f in staleness_findings if f.review_status in ("stale", "critical"))
    print(f"[pipeline] {stale_count}/{len(staleness_findings)} policies flagged stale/critical")

    # 5. Compliance mapping -------------------------------------------------------
    relationship_dicts = []
    for r in relationships:
        d = r.to_dict()
        d["controls"] = compliance_mapping.map_relationship(r.topic, r.relationship)
        d["severity"] = _severity_for_relationship(r.relationship)
        relationship_dicts.append(d)

    staleness_dicts = []
    for f in staleness_findings:
        d = f.to_dict()
        d["controls"] = compliance_mapping.map_staleness()
        staleness_dicts.append(d)

    # 6. Graph ----------------------------------------------------------------
    graph = build_graph(obligations, relationships)
    graph_json = graph_to_node_link(graph)

    # 7. Policy health scoring --------------------------------------------------
    policy_scores = _compute_policy_health(policies, relationships, staleness_findings)

    # 8. Write outputs ----------------------------------------------------------
    obligations_out = [o.to_dict() for o in obligations]
    _write_json(outputs_dir / "obligations.json", obligations_out)
    _write_json(outputs_dir / "relationships.json", relationship_dicts)
    _write_json(outputs_dir / "staleness.json", staleness_dicts)
    _write_json(outputs_dir / "graph.json", graph_json)
    _write_json(outputs_dir / "policy_scores.json", policy_scores)

    def _dedup(items: list[dict]) -> list[dict]:
        """Collapse sentence-level duplicate findings (same policy pair +
        topic) down to their highest-confidence instance, so the dashboard
        never shows two near-identical cards for what a human would read as
        one finding. Deliberately NOT capped at a fixed N -- this is an audit
        tool, and the displayed count must always match any summary badge
        derived from it."""
        best: dict[tuple, dict] = {}
        for d in items:
            key = (min(d["policy_a"], d["policy_b"]), max(d["policy_a"], d["policy_b"]), d["topic"])
            if key not in best or d["confidence"] > best[key]["confidence"]:
                best[key] = d
        return sorted(best.values(), key=lambda d: d["confidence"], reverse=True)

    top_conflicts = _dedup([d for d in relationship_dicts if d["relationship"] == "CONFLICT"])
    top_redundancies = _dedup([d for d in relationship_dicts if d["relationship"] == "REDUNDANT"])
    top_complementary = _dedup([d for d in relationship_dicts if d["relationship"] == "COMPLEMENTARY"])

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "live:" + client.provider if client.is_live else "offline",
        "model": client.model,
        "as_of_date": str(AS_OF_DATE),
        "summary": {
            "policies_analyzed": len(policies),
            "obligations_extracted": len(obligations),
            "candidate_pairs_evaluated": len(candidate_pairs),
            "relationships": counts,
            # Deduplicated counts -- these are what the dashboard badges use,
            # so the number shown always matches the number of cards rendered.
            "relationships_deduped": {
                "CONFLICT": len(top_conflicts),
                "REDUNDANT": len(top_redundancies),
                "COMPLEMENTARY": len(top_complementary),
            },
            "policies_stale_or_critical": stale_count,
            "runtime_seconds": round(time.time() - t0, 2),
        },
        "top_conflicts": top_conflicts,
        "top_redundancies": top_redundancies,
        "top_complementary": top_complementary,
        "stalest_policies": staleness_dicts[:10],
        "policy_scores": policy_scores,
    }
    _write_json(outputs_dir / "policy_health_report.json", report)

    print(f"[pipeline] done in {report['summary']['runtime_seconds']}s -> outputs written to {outputs_dir}")
    return report


def _compute_policy_health(policies, relationships, staleness_findings) -> list[dict]:
    """Per-policy rollup: conflict/redundancy counts + staleness -> 0-100 health score."""
    by_policy = {}
    for p in policies:
        pid = p["metadata"].get("policy_id", "UNKNOWN")
        by_policy[pid] = {
            "policy_id": pid,
            "title": p["metadata"].get("title"),
            "team": p["metadata"].get("team"),
            "conflict_count": 0,
            "redundant_count": 0,
            "complementary_count": 0,
        }

    for r in relationships:
        for pid in (r.policy_a, r.policy_b):
            if pid not in by_policy:
                continue
            if r.relationship == "CONFLICT":
                by_policy[pid]["conflict_count"] += 1
            elif r.relationship == "REDUNDANT":
                by_policy[pid]["redundant_count"] += 1
            elif r.relationship == "COMPLEMENTARY":
                by_policy[pid]["complementary_count"] += 1

    staleness_by_id = {f.policy_id: f for f in staleness_findings}

    results = []
    for pid, rec in by_policy.items():
        sf = staleness_by_id.get(pid)
        staleness_score = sf.staleness_score if sf else 0
        review_status = sf.review_status if sf else "unknown"
        # Health = 100 minus penalties. Conflicts hurt most, then staleness, then redundancy.
        penalty = (rec["conflict_count"] * 20) + (rec["redundant_count"] * 8) + (staleness_score * 0.4)
        health = max(0, round(100 - penalty))
        rec.update({
            "staleness_score": staleness_score,
            "review_status": review_status,
            "health_score": health,
        })
        results.append(rec)

    results.sort(key=lambda r: r["health_score"])
    return results


def _write_json(path: Path, data) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


if __name__ == "__main__":
    run_pipeline()
