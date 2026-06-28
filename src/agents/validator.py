"""Validation agent placeholder."""

from __future__ import annotations

from src.postprocess.normalize import validate_ranges


class ValidatorAgent:
    def validate(self, records: list[dict]) -> tuple[list[dict], list[dict]]:
        reports = []
        for idx, record in enumerate(records):
            reports.append({"record_index": idx, "warnings": validate_ranges(record)})
        return records, reports

