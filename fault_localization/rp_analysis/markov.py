from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable


BOS = "<s>"
EOS = "</s>"


@dataclass
class MarkovModel:
    """Simple add-k smoothed n-gram Markov model"""

    n: int
    smoothing: float
    vocab: set[str]
    history_counts: dict[tuple[str, ...], int]
    transition_counts: dict[tuple[str, ...], Counter[str]]

    def score_sequence(self, sequence: list[str]) -> dict[str, float]:
        """Return log-probability-derived metrics for one sequence"""
        seq = [str(t) for t in sequence if str(t)]
        padded = list((BOS,) * max(self.n - 1, 0)) + seq + list((EOS,))
        events = 0
        log_prob = 0.0
        vocab_size = len(self.vocab) + 1

        for i in range(self.n - 1, len(padded)):
            hist = tuple(padded[i - self.n + 1 : i]) if self.n > 1 else tuple()
            tok = padded[i]
            numer = float(self.transition_counts.get(hist, Counter()).get(tok, 0)) + self.smoothing
            denom = float(self.history_counts.get(hist, 0)) + self.smoothing * vocab_size
            log_prob += math.log(numer / denom)
            events += 1

        avg_neg_log_prob = -log_prob / max(events, 1)
        perplexity = math.exp(avg_neg_log_prob)
        return {
            "log_prob": float(log_prob),
            "avg_neg_log_prob": float(avg_neg_log_prob),
            "perplexity": float(perplexity),
            "token_count": float(len(seq)),
        }


def fit_markov_model(
    sequences: Iterable[list[str]],
    *,
    n: int,
    smoothing: float = 1.0,
) -> MarkovModel:
    """Fit an n-gram model from token sequences"""
    history_counts: dict[tuple[str, ...], int] = Counter()
    transition_counts: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    vocab: set[str] = set()

    for sequence in sequences:
        seq = [str(t) for t in sequence if str(t)]
        vocab.update(seq)
        padded = list((BOS,) * max(n - 1, 0)) + seq + list((EOS,))
        for i in range(n - 1, len(padded)):
            hist = tuple(padded[i - n + 1 : i]) if n > 1 else tuple()
            tok = padded[i]
            history_counts[hist] += 1
            transition_counts[hist][tok] += 1

    return MarkovModel(
        n=n,
        smoothing=float(smoothing),
        vocab=vocab,
        history_counts=dict(history_counts),
        transition_counts=dict(transition_counts),
    )
