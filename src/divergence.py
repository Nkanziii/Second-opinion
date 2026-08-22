"""
Divergence scoring between the two personas' responses on a given turn.

The concept doc specifies: "embedding similarity + confidence gap". This
module implements a real, working version of both today, with the semantic
similarity piece deliberately kept dependency-light for day-1 experimentation:

- confidence_gap: parsed from each persona's self-reported "Confidence: NN%"
  line (see personas.py). Simple absolute difference, 0-100.
- semantic_similarity: bag-of-words cosine similarity, pure Python + numpy,
  no model downloads or API calls needed. This is a *placeholder* for a real
  embedding model (e.g. an API embedding endpoint, or sentence-transformers
  once you're ready to add that dependency) — swap in upgrade_to_embeddings()
  when that's decided. Documented here so it's an explicit, visible decision
  in the weblog rather than a silent shortcut.

divergence_score combines both into a single 0-1 value where 1 = maximally
divergent (opposite confidence + dissimilar wording), 0 = fully aligned.
This drives the TouchDesigner visual sync/fracture behaviour via OSC later.
"""

import re
from collections import Counter

import numpy as np

CONFIDENCE_PATTERN = re.compile(r"Confidence:\s*(\d{1,3})\s*%", re.IGNORECASE)


def parse_confidence(text: str) -> float | None:
    match = CONFIDENCE_PATTERN.search(text)
    if not match:
        return None
    value = float(match.group(1))
    return max(0.0, min(100.0, value))


def strip_confidence_line(text: str) -> str:
    return CONFIDENCE_PATTERN.sub("", text).strip()


def _bow_vector(text: str, vocab: dict) -> np.ndarray:
    words = re.findall(r"[a-z']+", text.lower())
    counts = Counter(words)
    vec = np.zeros(len(vocab))
    for word, count in counts.items():
        if word in vocab:
            vec[vocab[word]] = count
    return vec


def bow_cosine_similarity(text_a: str, text_b: str) -> float:
    """Crude bag-of-words cosine similarity in [0, 1]. Placeholder for real
    embeddings — see module docstring."""
    words_a = set(re.findall(r"[a-z']+", text_a.lower()))
    words_b = set(re.findall(r"[a-z']+", text_b.lower()))
    vocab = {w: i for i, w in enumerate(sorted(words_a | words_b))}
    if not vocab:
        return 0.0
    vec_a = _bow_vector(text_a, vocab)
    vec_b = _bow_vector(text_b, vocab)
    denom = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if denom == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / denom)


def divergence_score(response_a: str, response_b: str) -> dict:
    conf_a = parse_confidence(response_a)
    conf_b = parse_confidence(response_b)
    confidence_gap = abs(conf_a - conf_b) / 100.0 if conf_a is not None and conf_b is not None else None

    text_a = strip_confidence_line(response_a)
    text_b = strip_confidence_line(response_b)
    similarity = bow_cosine_similarity(text_a, text_b)
    semantic_divergence = 1.0 - similarity

    # combine: if we have a confidence gap, weight it evenly with semantic
    # divergence; otherwise fall back to semantic divergence alone.
    if confidence_gap is not None:
        combined = 0.5 * confidence_gap + 0.5 * semantic_divergence
    else:
        combined = semantic_divergence

    return {
        "confidence_a": conf_a,
        "confidence_b": conf_b,
        "confidence_gap": confidence_gap,
        "semantic_similarity": similarity,
        "semantic_divergence": semantic_divergence,
        "divergence_score": combined,
    }
