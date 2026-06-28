"""Synthesis extraction agent placeholder."""

from __future__ import annotations

import re

from src.postprocess.normalize import normalize_number
from src.schemas.selt import blank_record


class SynthesisExtractorAgent:
    def extract(self, evidence: list[dict]) -> dict:
        record = blank_record()
        text = "\n".join(item.get("text", "") for item in evidence)
        lower = text.lower()
        if "green synthesis" in lower or "plant extract" in lower:
            record["np_synthesis"] = "green_synthesis"
        if "agno3" in lower or "silver nitrate" in lower:
            record["precursor_of_np"] = "AgNO3"
        ph = re.search(r"\bpH\s*[-=]?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if ph:
            record["ph_during_synthesis"] = normalize_number(ph.group(1))
        temp = re.search(r"(\d+(?:\.\d+)?)\s*(?:°\s*)?C\b", text, re.IGNORECASE)
        if temp:
            record["temperature_for_extract_C"] = normalize_number(temp.group(1))
        time = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hours)\b", text, re.IGNORECASE)
        if time:
            record["duration_preparing_extract_min"] = str(float(normalize_number(time.group(1))) * 60).removesuffix(".0")
        return record

