"""Nanoparticle characterization extraction agent placeholder."""

from __future__ import annotations

from src.postprocess.normalize import normalize_np, parse_nm_range
from src.schemas.selt import blank_record


class NanoparticleExtractorAgent:
    def extract(self, evidence: list[dict]) -> dict:
        record = blank_record()
        text = "\n".join(item.get("text", "") for item in evidence)
        if "AgNP" in text or "silver nanoparticle" in text.lower():
            record["np"] = normalize_np("AgNPs")
        low, high, avg = parse_nm_range(text)
        record["np_size_min_nm"] = low
        record["np_size_max_nm"] = high
        record["np_size_avg_nm"] = avg
        if "spherical" in text.lower():
            record["shape"] = "spherical"
        return record

