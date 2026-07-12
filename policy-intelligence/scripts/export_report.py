#!/usr/bin/env python3
"""
Render outputs/policy_health_report.json into a shareable Markdown report,
suitable for pasting into an audit meeting doc or emailing to policy owners.

Usage:
    python scripts/export_report.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline import OUTPUTS_DIR  # noqa: E402


def fmt_pair(d: dict) -> str:
    return (
        f"**{d['relationship']}** — {d['policy_a']} §{d['section_a']} vs "
        f"{d['policy_b']} §{d['section_b']}  (topic: `{d['topic']}`, "
        f"confidence: {round(d['confidence'] * 100)}%)\n\n"
        f"> **A.** \"{d['text_a']}\"\n"
        f">\n"
        f"> **B.** \"{d['text_b']}\"\n\n"
        f"{d['explanation']}\n\n"
        f"*Controls:* {', '.join(d['controls']) or '—'}\n"
    )


def main():
    report_path = OUTPUTS_DIR / "policy_health_report.json"
    if not report_path.exists():
        print("No report found — run `python scripts/run_pipeline.py` first.")
        sys.exit(1)

    report = json.loads(report_path.read_text())
    s = report["summary"]
    lines = []
    lines.append("# Policy Governance Health Report")
    lines.append("")
    lines.append(f"*Generated {report['generated_at']} · mode: `{report['mode']}` "
                  f"· as-of: {report.get('as_of_date', '—')}*")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Policies analyzed: **{s['policies_analyzed']}**")
    lines.append(f"- Obligations extracted: **{s['obligations_extracted']}**")
    lines.append(f"- Candidate pairs evaluated: **{s['candidate_pairs_evaluated']}**")
    rel = s["relationships"]
    lines.append(f"- Conflicts: **{rel.get('CONFLICT', 0)}** · "
                  f"Redundant: **{rel.get('REDUNDANT', 0)}** · "
                  f"Complementary: **{rel.get('COMPLEMENTARY', 0)}**")
    lines.append(f"- Policies stale or critical: **{s['policies_stale_or_critical']}** "
                  f"/ {s['policies_analyzed']}")
    lines.append("")

    lines.append("## Top Conflicts (unreconciled)")
    lines.append("")
    if not report["top_conflicts"]:
        lines.append("_None detected._")
    for d in report["top_conflicts"]:
        lines.append(fmt_pair(d))
        lines.append("---")
    lines.append("")

    lines.append("## Top Redundancies (consolidation candidates)")
    lines.append("")
    if not report["top_redundancies"]:
        lines.append("_None detected._")
    for d in report["top_redundancies"]:
        lines.append(fmt_pair(d))
        lines.append("---")
    lines.append("")

    lines.append("## Complementary (reconciled exceptions / authorized processes)")
    lines.append("")
    if not report.get("top_complementary"):
        lines.append("_None detected._")
    for d in report.get("top_complementary", []):
        lines.append(fmt_pair(d))
        lines.append("---")
    lines.append("")

    lines.append("## Stalest Policies")
    lines.append("")
    lines.append("| Policy | Last Reviewed | Months Since | Status | Deprecated References |")
    lines.append("|---|---|---|---|---|")
    for f in report["stalest_policies"]:
        refs = ", ".join(r["reference"] for r in f["deprecated_references"]) or "—"
        lines.append(f"| {f['policy_title']} ({f['policy_id']}) | {f['last_reviewed']} | "
                      f"{f['months_since_review']} | {f['review_status']} | {refs} |")
    lines.append("")

    lines.append("## Policy Health Scores (lowest first)")
    lines.append("")
    lines.append("| Policy | Team | Conflicts | Redundant | Review Status | Health |")
    lines.append("|---|---|---|---|---|---|")
    for p in report["policy_scores"]:
        lines.append(f"| {p['title']} ({p['policy_id']}) | {p['team']} | "
                      f"{p['conflict_count']} | {p['redundant_count']} | "
                      f"{p['review_status']} | {p['health_score']}/100 |")
    lines.append("")

    out_path = OUTPUTS_DIR / "policy_health_report.md"
    out_path.write_text("\n".join(lines))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
