"""
app.py
-------
Flask dashboard for the Policy Conflict & Staleness Detector.

Reads the JSON artifacts produced by src/pipeline.py (outputs/*.json) and
serves them to a static HTML/JS/D3 front-end. Run `python scripts/run_pipeline.py`
first (or use the /api/run endpoint) to generate fresh data.
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, Response

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline import run_pipeline, OUTPUTS_DIR  # noqa: E402

app = Flask(__name__, static_folder=str(Path(__file__).parent / "static"))


def _load_json(name: str):
    path = OUTPUTS_DIR / name
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


@app.route("/")
def index():
    return send_from_directory(Path(__file__).parent / "templates", "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(Path(__file__).parent / "static", filename)


@app.route("/api/report")
def api_report():
    data = _load_json("policy_health_report.json")
    if data is None:
        return jsonify({"error": "No report yet. POST /api/run first."}), 404
    return jsonify(data)


@app.route("/api/relationships")
def api_relationships():
    data = _load_json("relationships.json")
    return jsonify(data or [])


@app.route("/api/obligations")
def api_obligations():
    data = _load_json("obligations.json")
    return jsonify(data or [])


@app.route("/api/staleness")
def api_staleness():
    data = _load_json("staleness.json")
    return jsonify(data or [])


@app.route("/api/graph")
def api_graph():
    data = _load_json("graph.json")
    return jsonify(data or {"nodes": [], "edges": []})


@app.route("/api/policy_scores")
def api_policy_scores():
    data = _load_json("policy_scores.json")
    return jsonify(data or [])


@app.route("/api/run", methods=["POST", "GET"])
def api_run():
    report = run_pipeline()
    return jsonify(report)


if __name__ == "__main__":
    if not (OUTPUTS_DIR / "policy_health_report.json").exists():
        print("[dashboard] No outputs found yet - running pipeline once...")
        run_pipeline()
    app.run(host="0.0.0.0", port=5050, debug=False)
