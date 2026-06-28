"""Activity extraction agent for SelTox antibacterial rows."""

from __future__ import annotations

import json
import re
from typing import Any

from src.agents.base import LLMClient, LLMNotConfigured
from src.postprocess.normalize import BACTERIA_SYNONYMS, normalize_bacteria, normalize_np, normalize_number
from src.schemas.selt import blank_record


class ActivityExtractorAgent:
    fields = [
        "np",
        "bacteria",
        "mdr",
        "strain",
        "method",
        "mic_np_µg_ml",
        "concentration",
        "zoi_np_mm",
        "time_set_hours",
    ]

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()
        self.last_raw_response = ""

    def extract(self, evidence: list[dict]) -> list[dict]:
        try:
            records = self._extract_with_llm(evidence)
            if records:
                return records
        except LLMNotConfigured:
            pass
        except Exception:
            # Keep the pipeline usable during hackathon iteration; inspect logs/raw artifacts later.
            pass
        return self._extract_deterministic(evidence)

    def _extract_with_llm(self, evidence: list[dict]) -> list[dict]:
        evidence_text = self._format_evidence(evidence)
        if not evidence_text.strip():
            return []
        system = (
            "You extract SelTox antibacterial activity rows from scientific PDF evidence. "
            "Use only the supplied evidence. Do not guess. Return compact JSON only."
        )
        user = f"""
Extract antibacterial activity records.

Fields:
{", ".join(self.fields)}

Rules:
- Return JSON object with key "records".
- Each record must contain all fields above.
- Use "NOT_DETECTED" for missing text fields and "nan" for missing numeric fields.
- Normalize common bacteria names when obvious, e.g. E. coli -> Escherichia coli.
- Numeric fields must contain only the number when possible, without units.
- MIC is usually in µg/mL; ZOI is usually in mm; time_set_hours is incubation/exposure time in hours.
- Prefer tables and table captions over abstract/background.

Evidence:
{evidence_text}
""".strip()
        self.last_raw_response = self.llm.complete_text(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_output_tokens=1200,
        )
        payload = self._parse_json_object(self.last_raw_response)
        raw_records = payload.get("records", []) if isinstance(payload, dict) else []
        if not isinstance(raw_records, list):
            return []
        return [self._normalize_activity_record(item) for item in raw_records if isinstance(item, dict)]

    def _extract_deterministic(self, evidence: list[dict]) -> list[dict]:
        text = "\n".join(str(item.get("text", "")) for item in evidence)
        if not text.strip():
            return []

        bacteria = self._find_bacteria(text)
        if not bacteria:
            return []

        base = blank_record()
        if re.search(r"\bAg\s*NPs?\b|\bAgNPs?\b|silver nanoparticles?", text, re.IGNORECASE):
            base["np"] = normalize_np("AgNPs")
        strain = re.search(r"\bATCC\s*[-:]?\s*\d+\b", text, re.IGNORECASE)
        if strain:
            base["strain"] = re.sub(r"\s+", " ", strain.group(0).upper())
        if re.search(r"\bMDR\b|multidrug[-\s]?resistant", text, re.IGNORECASE):
            base["mdr"] = "yes"

        mic = self._find_value_near_label(text, r"MIC|minimum inhibitory concentration", r"µg\s*/?\s*mL|ug\s*/?\s*mL|microg\s*/?\s*mL")
        zoi = self._find_value_near_label(text, r"ZOI|zone of inhibition|inhibition zone", r"mm")
        time_hours = self._find_time_hours(text)

        records = []
        for name in bacteria:
            record = dict(base)
            record["bacteria"] = name
            if mic != "nan":
                record["method"] = "MIC"
                record["mic_np_µg_ml"] = mic
            if zoi != "nan":
                record["method"] = "ZOI" if record["method"] == "NOT_DETECTED" else record["method"]
                record["zoi_np_mm"] = zoi
            if time_hours != "nan":
                record["time_set_hours"] = time_hours
            records.append(record)
        return records

    def _normalize_activity_record(self, raw: dict[str, Any]) -> dict:
        record = blank_record()
        for field in self.fields:
            value = raw.get(field, record[field])
            if value in (None, "", []):
                value = record[field]
            record[field] = str(value).strip()
        record["np"] = normalize_np(record["np"])
        record["bacteria"] = normalize_bacteria(record["bacteria"])
        for field in ("mic_np_µg_ml", "zoi_np_mm", "time_set_hours"):
            record[field] = normalize_number(record[field])
        return record

    def _format_evidence(self, evidence: list[dict], max_chars: int = 12000) -> str:
        parts = []
        used = 0
        for item in evidence:
            text = " ".join(str(item.get("text", "")).split())
            if not text:
                continue
            prefix = f"[{item.get('id', 'evidence')} page={item.get('page', '?')} type={item.get('source_type', '?')}] "
            remaining = max_chars - used - len(prefix)
            if remaining <= 0:
                break
            clipped = text[:remaining]
            parts.append(prefix + clipped)
            used += len(prefix) + len(clipped)
        return "\n".join(parts)

    def _parse_json_object(self, text: str) -> dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    def _find_bacteria(self, text: str) -> list[str]:
        found = []
        lower = text.lower()
        for synonym, canonical in sorted(BACTERIA_SYNONYMS.items(), key=lambda item: len(item[0]), reverse=True):
            pattern = r"(?<![a-z])" + re.escape(synonym).replace(r"\ ", r"\s+") + r"(?![a-z])"
            if re.search(pattern, lower, re.IGNORECASE) and canonical not in found:
                found.append(canonical)
        return found

    def _find_value_near_label(self, text: str, label_pattern: str, unit_pattern: str) -> str:
        label_first = re.search(
            rf"(?:{label_pattern})[^\d]{{0,80}}(\d+(?:[.,]\d+)?)[^\n\r]{{0,30}}(?:{unit_pattern})",
            text,
            re.IGNORECASE,
        )
        if label_first:
            return normalize_number(label_first.group(1))
        unit_first = re.search(
            rf"(\d+(?:[.,]\d+)?)[^\n\r]{{0,30}}(?:{unit_pattern})[^\n\r]{{0,80}}(?:{label_pattern})",
            text,
            re.IGNORECASE,
        )
        if unit_first:
            return normalize_number(unit_first.group(1))
        return "nan"

    def _find_time_hours(self, text: str) -> str:
        match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:h|hr|hrs|hours)\b[^\n\r]{0,50}(?:incubat|exposure)", text, re.IGNORECASE)
        if not match:
            match = re.search(r"(?:incubat|exposure)[^\n\r]{0,50}(\d+(?:[.,]\d+)?)\s*(?:h|hr|hrs|hours)\b", text, re.IGNORECASE)
        return normalize_number(match.group(1)) if match else "nan"
