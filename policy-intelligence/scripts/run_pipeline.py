#!/usr/bin/env python3
"""
Run the full Policy Conflict & Staleness Detector pipeline.

Usage:
    python scripts/run_pipeline.py

Set ANTHROPIC_API_KEY or OPENAI_API_KEY in the environment to use a real
LLM for obligation extraction and relationship classification. Without a
key, the pipeline runs fully offline using deterministic heuristics.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import run_pipeline

if __name__ == "__main__":
    run_pipeline()
