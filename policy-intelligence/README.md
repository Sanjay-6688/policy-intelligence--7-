# Policy Conflict & Staleness Detector

**Track:** Policy Governance · **Approach:** Option A — LLM-Powered Policy Intelligence

Ingests a corpus of enterprise security/compliance policies, extracts structured
obligations from free text, finds cross-policy relationships (conflicts,
redundancies, and intentional complementary exceptions), flags stale policies,
maps everything to ISO 27001 / NIST 800-53 / GDPR / COBIT controls, and
presents it all in an interactive audit dashboard.

```
┌────────────┐   ┌───────────────┐   ┌───────────────┐   ┌────────────────┐
│  Policies   │──▶│  Obligation    │──▶│  Candidate     │──▶│  Relationship   │
│  (.md +     │   │  Extraction    │   │  Pair Finder   │   │  Classifier     │
│  frontmatter)│   │ (LLM / rules)  │   │ (TF-IDF cosine)│   │ (LLM / rules)   │
└────────────┘   └───────────────┘   └───────┬───────┘   └────────┬───────┘
                                              │                     │
                        ┌─────────────────────┘                     │
                        ▼                                           ▼
               ┌────────────────┐                          ┌────────────────┐
               │   Staleness     │                          │  Compliance     │
               │   Assessment    │                          │  Mapping        │
               └───────┬────────┘                          └────────┬───────┘
                       │                                            │
                       └───────────────┬────────────────────────────┘
                                        ▼
                              ┌──────────────────┐
                              │  Knowledge Graph   │
                              │  (NetworkX)         │
                              └─────────┬──────────┘
                                        ▼
                              ┌──────────────────┐
                              │  Flask Dashboard   │
                              │  (D3 graph, tables) │
                              └──────────────────┘
```

## Quick start

```bash
pip install -r requirements.txt

# 1. Run the pipeline (writes outputs/*.json)
python scripts/run_pipeline.py

# 2. Launch the dashboard
python dashboard/app.py
# -> open http://localhost:5050
```

That's it — the pipeline runs **fully offline** out of the box (see "Two
modes" below), so there's nothing else to configure for a first run.

## Two modes: LIVE (LLM) vs OFFLINE (heuristic)

This is the core design decision described in the Option A brief: *use an
LLM to extract obligations and reason about conflicts*. Real LLM calls cost
money and require credentials, so the whole pipeline is built around a
single abstraction (`src/llm_client.py`) that transparently swaps between:

| | **LIVE mode** | **OFFLINE mode** (default) |
|---|---|---|
| Trigger | `GROQ_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY` set in env | no key set |
| Extraction | LLM reads full policy text, returns structured obligations (`extraction.py::extract_with_llm`) | regex/keyword rules over trigger words (must/shall/should/prohibited/exempt/…) (`extraction.py::extract_with_heuristic`) |
| Classification | LLM reasons about scope + conditions to decide CONFLICT/REDUNDANT/COMPLEMENTARY/UNRELATED, with a written explanation (`classifier.py::classify_with_llm`) | rule engine mirroring Option B, with explicit precision guards (see below) (`classifier.py::classify_with_heuristic`) |
| Similarity / candidate pairing | same in both modes — TF-IDF cosine + topic matching (`similarity.py`). Swap in a real embeddings call here for higher recall if desired. |

To enable LIVE mode, pick one:

**Groq — free, no credit card, no expiration, high rate limits (recommended)**:
```bash
# 1. Get a key at https://console.groq.com/keys
export GROQ_API_KEY=gsk_...
python scripts/run_pipeline.py
```
No extra `pip install` needed — uses only the Python standard library
(`urllib`). Free tier is ~30 requests/min and 14,400 requests/day, which
comfortably covers a full pipeline run (~25 calls total). Override the model
with `GROQ_MODEL` (default `llama-3.3-70b-versatile`).

**Google Gemini — also free, no credit card required to sign up** (note:
some accounts see the free quota gated at 0 until a billing account is
linked — Groq is the more reliably zero-friction option as of mid-2026):
```bash
export GEMINI_API_KEY=AIza...
python scripts/run_pipeline.py
```

**Anthropic or OpenAI** (paid, but new accounts get a small free trial credit):
```bash
export ANTHROPIC_API_KEY=sk-ant-...
pip install anthropic
python scripts/run_pipeline.py
```

Provider precedence when multiple keys are set: Groq → Anthropic → OpenAI →
Gemini → offline. Pass `LLMClient(provider="...")` explicitly to force a
specific provider regardless of which keys are present.

The dashboard masthead always shows which mode produced the current data,
and displays a banner when running in offline mode so nobody mistakes
heuristic output for LLM reasoning.

Both modes emit the **identical JSON schema** (see below), so the graph
builder, compliance mapper, and dashboard don't know or care which backend
ran — this is what makes the two modes fully interchangeable.

## Pipeline stages (`src/pipeline.py`)

1. **Load policies** (`extraction.py::load_policies`) — 17 synthetic
   policies in `data/policies/*.md` with YAML frontmatter (`policy_id`,
   `team`, `owner`, `version`, `effective_date`, `last_reviewed`,
   `references`), covering the exact ambiguous scenarios called out in the
   brief: rotation vs. MFA, retention vs. erasure, VPN vs. CI/CD exception,
   on-prem backup vs. cloud replication exception, legacy TLS/SHA-1 vs.
   modern encryption standards, and a legacy admin console that was never
   reconciled with a newer MFA mandate.

2. **Obligation extraction** (`extraction.py`) — every sentence containing
   an obligation trigger (must/shall/required/prohibited/should/exempt/…)
   becomes a structured record:
   ```json
   {
     "obligation_id": "POL-001-3.1-o1",
     "policy_id": "POL-001",
     "section": "3.1",
     "text": "All employees must rotate passwords every 90 days...",
     "obligation": "rotate_password",
     "topic": "password_rotation",
     "scope": "all_employees",
     "strength": "mandatory",
     "polarity": "require",
     "frequency": "90_days",
     "conditions": null
   }
   ```

3. **Candidate pairing** (`similarity.py`) — comparing every obligation
   against every other is O(n²) LLM calls. Instead we TF-IDF-vectorize
   obligation text, compute cosine similarity, and keep pairs that are
   either text-similar *or* share a governance topic (including a small
   `CROSS_TOPIC_GROUPS` table for topics that are related despite different
   labels, e.g. `data_retention` ↔ `data_deletion`). Same-policy pairs are
   dropped — we care about cross-policy governance conflicts.

4. **Relationship classification** (`classifier.py`) — for each candidate
   pair, decide **CONFLICT / REDUNDANT / COMPLEMENTARY / UNRELATED** with a
   1–3 sentence audit-ready explanation. The offline heuristic encodes the
   same scope-awareness the LLM prompt asks for:
   - opposite polarity + same/overlapping scope + no exception clause →
     **CONFLICT**
   - opposite polarity + an explicit exception clause ("provided…",
     "except…", "unless…") → **COMPLEMENTARY** (a reconciled carve-out, not
     an unaddressed contradiction)
   - same polarity + same scope + same strength → **REDUNDANT**
   - a handful of precision guards prevent known false-positive patterns:
     comparing unlike quantities (a retention *duration* vs. a suspension
     *window*), treating "must be enabled" and "must not be disabled" as
     contradictory when they're the same mandate stated two ways, and
     capping broad catch-all topics (e.g. generic "password hygiene") at
     COMPLEMENTARY-for-review rather than an automatic CONFLICT verdict.

5. **Staleness assessment** (`staleness.py`) — flags policies not reviewed
   in 18+ months, and separately flags references to deprecated
   technologies (TLS 1.0/1.1, SHA-1, Windows Server 2012, NIST 800-53 Rev
   4) regardless of review date. Combines into a 0–100 staleness score and
   a `current / aging / stale / critical` status.

6. **Compliance mapping** (`compliance_mapping.py`) — every relationship
   and staleness finding is annotated with concrete control citations
   (NIST SP 800-53 control IDs, ISO 27001 clauses, GDPR articles, COBIT
   2019 processes) so findings translate directly into audit language.

7. **Knowledge graph** (`graph_builder.py`) — obligations are nodes,
   flagged relationships are edges, exported as D3-ready node-link JSON.

8. **Policy health scoring** (`pipeline.py::_compute_policy_health`) — per
   policy: `health = 100 − (20 × conflicts) − (8 × redundancies) − (0.4 ×
   staleness_score)`, giving a single sortable number for prioritizing
   remediation.

## Output artifacts (`outputs/`)

| File | Contents |
|---|---|
| `obligations.json` | every extracted obligation |
| `relationships.json` | every classified pair (including UNRELATED, kept for transparency) |
| `staleness.json` | per-policy staleness findings, sorted worst-first |
| `policy_scores.json` | per-policy health rollup |
| `graph.json` | D3 node-link graph |
| `policy_health_report.json` | the combined executive report the dashboard reads: summary counts, top conflicts, top redundancies, stalest policies, policy scores |

## Dashboard (`dashboard/`)

Flask app (`app.py`) serving a single-page dashboard (`templates/index.html`
+ `static/js/dashboard.js` + `static/css/style.css`, vanilla JS + D3, no
build step). Five views:

- **Conflicts** — redline "casefile" cards: the two contradicting clauses
  side by side, a verdict stamp, the reasoning, and the compliance controls
  at risk.
- **Redundant & Complementary** — same card format for the other two
  actionable relationship types.
- **Staleness** — sortable table of review age + deprecated-reference chips.
- **Policy Health** — sortable table with a health-score bar per policy.
- **Obligation Graph** — interactive D3 force-directed graph of the full
  obligation network, draggable, zoomable, colored by relationship type.

Re-run the pipeline and refresh the page (or `POST /api/run`) to regenerate
data after editing policies.

## Design rationale: why heuristics mirror the LLM prompt's reasoning

The offline fallback isn't just a placeholder — it's built to fail the same
way a careful human reviewer would reason, specifically around the brief's
own success criterion: *"false conflict alerts erode trust with policy
owners."* Every fix made during development (documented in the code
comments) was in service of precision: broad keyword collisions were split
into narrower topics, "the same mandate stated as a requirement vs. a
prohibition" was special-cased, and generic catch-all topics were capped
below CONFLICT severity. This means switching to LIVE mode is a strict
upgrade in *nuance*, not a fix for a fundamentally different set of bugs.

## Extending this project

- **Real embeddings** — swap `similarity.py::vectorize()` for an
  embeddings API call; nothing downstream needs to change.
- **More policies** — drop additional `.md` files with the same frontmatter
  schema into `data/policies/`; the pipeline picks them up automatically.
- **New topics** — add entries to `TOPIC_KEYWORDS` in `extraction.py` and
  `TOPIC_CONTROLS` in `compliance_mapping.py`.
- **Export for an audit meeting** — run `python scripts/export_report.py`
  to render `outputs/policy_health_report.json` into a shareable Markdown
  summary at `outputs/policy_health_report.md`.

## Known limitations (offline mode)

- Sentence-level regex extraction can occasionally mis-tag a topic when a
  sentence uses vocabulary from more than one governance area — this is the
  category of error a real LLM extraction pass is meant to fix.
- Frequency/duration parsing is a simple regex (`\d+ (day|month|year|hour)`)
  and won't catch prose like "on a quarterly basis."
- Scope inference relies on a small fixed pattern list; a new policy that
  introduces a novel scope phrase (e.g. "contractors in the EMEA region")
  will fall back to `general` until a pattern is added.

None of these affect LIVE mode, which reasons over the full clause text
directly.
