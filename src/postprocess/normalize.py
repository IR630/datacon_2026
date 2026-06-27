"""Deterministic normalization helpers for SelTox."""

from __future__ import annotations

import re
from typing import Any


MISSING_VALUES = {"", "-", "na", "n/a", "nd", "n.d.", "nr", "not reported", "not detected", "none", "null"}

BACTERIA_SYNONYMS = {
    "e. coli": "Escherichia coli",
    "escherichia coli": "Escherichia coli",
    "s. aureus": "Staphylococcus aureus",
    "staphylococcus aureus": "Staphylococcus aureus",
    "p. aeruginosa": "Pseudomonas aeruginosa",
    "pseudomonas aeruginosa": "Pseudomonas aeruginosa",
    "k. pneumoniae": "Klebsiella pneumoniae",
    "klebsiella pneumoniae": "Klebsiella pneumoniae",
    "b. subtilis": "Bacillus subtilis",
    "bacillus subtilis": "Bacillus subtilis",
    "e. faecalis": "Enterococcus faecalis",
    "enterococcus faecalis": "Enterococcus faecalis",
}

NP_SYNONYMS = {
    "agnp": "Ag",
    "agnps": "Ag",
    "ag np": "Ag",
    "ag nps": "Ag",
    "silver nanoparticle": "Ag",
    "silver nanoparticles": "Ag",
    "zno nanoparticles": "ZnO",
    "zno nanoparticle": "ZnO",
    "aunp": "Au",
    "aunps": "Au",
}


def normalize_missing(value: Any) -> Any:
    if value is None:
        return "NOT_DETECTED"
    text = str(value).strip()
    if text.lower() in MISSING_VALUES:
        return "NOT_DETECTED"
    return value


def normalize_bacteria(value: Any) -> str:
    value = normalize_missing(value)
    if value == "NOT_DETECTED":
        return value
    key = re.sub(r"\s+", " ", str(value).strip().lower())
    return BACTERIA_SYNONYMS.get(key, str(value).strip())


def normalize_np(value: Any) -> str:
    value = normalize_missing(value)
    if value == "NOT_DETECTED":
        return value
    key = re.sub(r"[\s-]+", " ", str(value).strip().lower())
    key = key.replace(".", "")
    return NP_SYNONYMS.get(key, str(value).strip())


def normalize_number(value: Any) -> str:
    value = normalize_missing(value)
    if value == "NOT_DETECTED":
        return value
    text = str(value).strip().replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return text
    number = float(match.group(0))
    if number.is_integer():
        return str(int(number))
    return str(number)


def parse_nm_range(value: str) -> tuple[str, str, str]:
    text = str(value).replace(",", ".")
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*nm", text, re.IGNORECASE)
    if range_match:
        low = normalize_number(range_match.group(1))
        high = normalize_number(range_match.group(2))
        try:
            avg = str((float(low) + float(high)) / 2)
            if avg.endswith(".0"):
                avg = avg[:-2]
        except Exception:
            avg = "NOT_DETECTED"
        return low, high, avg
    single = re.search(r"(\d+(?:\.\d+)?)\s*nm", text, re.IGNORECASE)
    if single:
        number = normalize_number(single.group(1))
        return number, number, number
    return "NOT_DETECTED", "NOT_DETECTED", "NOT_DETECTED"


def validate_ranges(record: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    checks = {
        "ph_during_synthesis": (0, 14),
        "np_size_min_nm": (0, None),
        "np_size_max_nm": (0, None),
        "np_size_avg_nm": (0, None),
        "mic_np_µg_ml": (0, None),
        "zoi_np_mm": (0, None),
    }
    for field, (low, high) in checks.items():
        value = record.get(field)
        if value in (None, "NOT_DETECTED") or str(value).strip().lower() == "nan":
            continue
        try:
            number = float(str(value).replace(",", "."))
        except ValueError:
            warnings.append(f"{field}: not numeric")
            continue
        if low is not None and number < low:
            warnings.append(f"{field}: below {low}")
        if high is not None and number > high:
            warnings.append(f"{field}: above {high}")
    return warnings
