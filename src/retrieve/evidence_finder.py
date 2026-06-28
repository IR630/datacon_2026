"""Hybrid evidence finder for parsed PDF artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.retrieve.bm25 import BM25
from src.retrieve.patterns import ACTIVITY_QUERY, NANOPARTICLE_QUERY, REGEX_PATTERNS, SYNTHESIS_QUERY
from src.utils.io import read_json


GROUP_QUERIES = {
    "activity": ACTIVITY_QUERY,
    "nanoparticle": NANOPARTICLE_QUERY,
    "synthesis": SYNTHESIS_QUERY,
}


def load_chunks(parsed_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(parsed_dir) / "chunks.json"
    if not path.exists():
        raise FileNotFoundError(f"Parsed chunks not found: {path}")
    chunks = read_json(path)
    return [chunk for chunk in chunks if chunk.get("text")]


def _regex_hits(text: str) -> list[str]:
    return [name for name, pattern in REGEX_PATTERNS.items() if pattern.search(text)]


def find_evidence(parsed_dir: str | Path, top_k: int = 12) -> dict[str, list[dict[str, Any]]]:
    chunks = load_chunks(parsed_dir)
    docs = [chunk.get("text", "") for chunk in chunks]
    bm25 = BM25(docs)
    grouped: dict[str, list[dict[str, Any]]] = {}

    for group, query in GROUP_QUERIES.items():
        scores = bm25.score(query)
        ranked = []
        for chunk, score in zip(chunks, scores):
            hits = _regex_hits(chunk.get("text", ""))
            keyword_bonus = 0.25 * len(hits)
            source_bonus = 0.5 if chunk.get("source_type") == "table" else 0.0
            total = score + keyword_bonus + source_bonus
            if total <= 0:
                continue
            item = dict(chunk)
            item["score"] = round(total, 4)
            item["regex_hits"] = hits
            ranked.append(item)
        grouped[group] = sorted(ranked, key=lambda row: row["score"], reverse=True)[:top_k]
    return grouped

