"""
similarity.py
--------------
Step 2 of the pipeline: find candidate obligation PAIRS worth classifying.

Comparing every obligation against every other one is O(n^2) LLM calls,
which is both slow and expensive. Instead we:

  1. Vectorize obligation text (TF-IDF by default; swap in a real embeddings
     API by replacing `vectorize()` if you have one available).
  2. Compute pairwise cosine similarity.
  3. Keep only pairs that are either:
       - textually similar (cosine >= SIMILARITY_THRESHOLD), OR
       - same governance `topic` (catches paraphrased obligations that don't
         share much vocabulary, e.g. "rotate passwords" vs "credential
         refresh cycles shall be enforced")
     ...and DROP pairs from the same policy (we care about cross-policy
     governance conflicts, not intra-document duplication).

This keeps the expensive classification step to a small, high-recall
candidate set instead of the full cross product.
"""
from __future__ import annotations

from itertools import combinations
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .extraction import Obligation

SIMILARITY_THRESHOLD = 0.12  # deliberately low recall-favoring threshold;
                              # the classifier step is precision's real gate


@dataclass
class CandidatePair:
    a: Obligation
    b: Obligation
    similarity: float
    match_reason: str  # "text_similarity" | "same_topic" | "both"


def vectorize(obligations: list[Obligation]) -> np.ndarray:
    """TF-IDF vectorization of obligation text. Swap for a real embeddings
    API (OpenAI/Anthropic/sentence-transformers) for higher recall on
    heavily paraphrased obligations -- the rest of the pipeline is agnostic
    to how vectors are produced."""
    texts = [f"{o.topic} {o.obligation} {o.text}" for o in obligations]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(texts)
    return matrix.toarray()


def find_candidate_pairs(obligations: list[Obligation]) -> list[CandidatePair]:
    if len(obligations) < 2:
        return []

    vectors = vectorize(obligations)
    sim_matrix = cosine_similarity(vectors)

    candidates = []
    for i, j in combinations(range(len(obligations)), 2):
        a, b = obligations[i], obligations[j]
        if a.policy_id == b.policy_id:
            continue  # focus on cross-policy governance relationships
        if a.topic == "general" and b.topic == "general":
            continue  # no reliable governance topic signal on either side

        sim = float(sim_matrix[i][j])
        same_topic = a.topic == b.topic and a.topic != "general"
        text_sim = sim >= SIMILARITY_THRESHOLD

        if not (same_topic or text_sim):
            continue

        if same_topic and text_sim:
            reason = "both"
        elif same_topic:
            reason = "same_topic"
        else:
            reason = "text_similarity"

        candidates.append(CandidatePair(a=a, b=b, similarity=round(sim, 4), match_reason=reason))

    # Highest-similarity pairs first (useful for triage / capping LLM calls)
    candidates.sort(key=lambda c: c.similarity, reverse=True)
    return candidates
