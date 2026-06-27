"""Deduplication helpers."""

from __future__ import annotations


def deduplicate_records(records: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for record in records:
        key = tuple(sorted((k, str(v)) for k, v in record.items()))
        if key in seen:
            continue
        seen.add(key)
        out.append(record)
    return out

