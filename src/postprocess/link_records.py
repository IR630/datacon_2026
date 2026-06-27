"""Record linking helpers."""

from __future__ import annotations

from src.schemas.selt import blank_record


def merge_article_level_records(*records: dict) -> dict:
    merged = blank_record()
    for record in records:
        for key, value in record.items():
            if value not in (None, "", "NOT_DETECTED"):
                merged[key] = value
    return merged

