"""Minimal BM25 implementation to avoid a mandatory dependency."""

from __future__ import annotations

import math
import re
from collections import Counter


TOKEN_RE = re.compile(r"[\wµ%.-]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in TOKEN_RE.findall(text)]


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(doc) for doc in docs]
        self.doc_freqs = [Counter(tokens) for tokens in self.doc_tokens]
        self.lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        df: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            df.update(set(tokens))
        self.idf = {
            term: math.log(1 + (len(docs) - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def score(self, query: str) -> list[float]:
        terms = tokenize(query)
        scores: list[float] = []
        for freqs, length in zip(self.doc_freqs, self.lengths):
            total = 0.0
            for term in terms:
                tf = freqs.get(term, 0)
                if tf == 0:
                    continue
                denom = tf + self.k1 * (1 - self.b + self.b * length / (self.avgdl or 1))
                total += self.idf.get(term, 0.0) * tf * (self.k1 + 1) / denom
            scores.append(total)
        return scores

