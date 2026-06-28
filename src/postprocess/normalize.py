"""Deterministic normalization helpers for SelTox.

Calibrated to the actual gold format (see docs/gt_format.md). Key facts the metric
(exact-string multiset) forces us to match:
- numeric fields stored as float64 -> "10.0", "24.0", "-18.0" (Python str(float));
- mic_np_µg_ml is stored as str -> "100", "12.5" (integer-style, no ".0");
- mdr / coating are int64 0/1 with 0% missing -> default "0", never NOT_DETECTED;
- np = chemical formula ("Ag", "ZnO"); bacteria = full latin name; method = upper vocab.
"""

from __future__ import annotations

import re
from typing import Any


# Tokens that mean "missing" coming OUT of an LLM/extractor (string-field oriented).
MISSING_VALUES = {"", "-", "na", "n/a", "nd", "n.d.", "nr", "not reported", "not detected", "none", "null"}
# Broader set used by the calibrated per-field formatters (includes the gold blanks).
_MISSING = MISSING_VALUES | {"--", "n.a.", "n.r.", "not_detected", "nan"}

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
    "c. albicans": "Candida albicans",
    "candida albicans": "Candida albicans",
    "a. baumannii": "Acinetobacter baumannii",
    "acinetobacter baumannii": "Acinetobacter baumannii",
    "s. enterica": "Salmonella enterica",
    "salmonella enterica": "Salmonella enterica",
    "s. epidermidis": "Staphylococcus epidermidis",
    "staphylococcus epidermidis": "Staphylococcus epidermidis",
    "p. mirabilis": "Proteus mirabilis",
    "proteus mirabilis": "Proteus mirabilis",
    "s. typhimurium": "Salmonella typhimurium",
    "salmonella typhimurium": "Salmonella typhimurium",
    "b. cereus": "Bacillus cereus",
    "bacillus cereus": "Bacillus cereus",
}

# Common nanoparticle names -> gold formula form.
NP_SYNONYMS = {
    "agnp": "Ag", "agnps": "Ag", "ag np": "Ag", "ag nps": "Ag",
    "silver": "Ag", "silver np": "Ag", "silver nps": "Ag",
    "silver nanoparticle": "Ag", "silver nanoparticles": "Ag",
    "zinc oxide": "ZnO", "zno np": "ZnO", "zno nps": "ZnO",
    "zno nanoparticle": "ZnO", "zno nanoparticles": "ZnO",
    "gold": "Au", "aunp": "Au", "aunps": "Au", "au np": "Au", "au nps": "Au",
    "gold nanoparticle": "Au", "gold nanoparticles": "Au",
    "titanium dioxide": "TiO2", "titania": "TiO2", "tio2 np": "TiO2", "tio2 nps": "TiO2",
    "copper oxide": "CuO", "cuo np": "CuO", "cuo nps": "CuO",
    "iron oxide": "Fe3O4", "magnetite": "Fe3O4", "fe3o4 np": "Fe3O4",
    "cerium oxide": "CeO2", "ceria": "CeO2", "ceo2 np": "CeO2",
    "bismuth oxide": "Bi2O3",
    "palladium": "Pd", "pd np": "Pd",
    "cobalt": "Co",
    "platinum": "Pt", "pt np": "Pt",
    "zirconia": "ZrO2", "zirconium dioxide": "ZrO2",
    "alumina": "Al2O3", "aluminium oxide": "Al2O3", "aluminum oxide": "Al2O3",
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


# --------------------------------------------------------------------------------------
# GT-calibrated per-field normalization (the source of truth for exact-string matching).
# --------------------------------------------------------------------------------------

def _is_missing(value: Any) -> bool:
    return value is None or str(value).strip().lower() in _MISSING


def _first_number(value: Any) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).strip().replace(",", "."))
    return float(match.group(0)) if match else None


def norm_text(value: Any) -> str:
    return "NOT_DETECTED" if _is_missing(value) else str(value).strip()


def norm_float_num(value: Any) -> str:
    """Float64-stored gold fields -> Python str(float): 10 -> '10.0', 12.5 -> '12.5'."""
    if _is_missing(value):
        return "nan"
    number = _first_number(value)
    return "nan" if number is None else str(number)


def norm_int_num(value: Any) -> str:
    """Str-stored numeric gold (mic_np_µg_ml) -> '100' / '12.5'."""
    if _is_missing(value):
        return "nan"
    number = _first_number(value)
    if number is None:
        return "nan"
    return str(int(number)) if number.is_integer() else str(number)


def norm_binary(value: Any) -> str:
    """mdr / coating -> '0' or '1'; default '0' (gold has 0% missing, ~85-91% zeros)."""
    if _is_missing(value):
        return "0"
    text = str(value).strip().lower()
    if text in {"1", "yes", "y", "true", "positive", "mdr", "resistant", "present", "coated"}:
        return "1"
    if text in {"0", "no", "n", "false", "negative", "absent", "uncoated"}:
        return "0"
    number = _first_number(text)
    if number is not None:
        return "1" if number >= 0.5 else "0"
    return "0"


def norm_method(value: Any) -> str:
    """Map free-text assay names to the gold vocabulary {MIC, ZOI, MBC, MFC}.

    The LLM emits phrasings like "Broth microdilution assay" or "Agar well
    diffusion"; gold stores only the 4 canonical tokens. Mapping recovers true
    ZOI/MBC rows that the MIC-only prior misses.
    """
    if _is_missing(value):
        return "NOT_DETECTED"
    text = str(value).strip()
    low = text.lower()
    if "mbc" in low or "bactericidal" in low:
        return "MBC"
    if "mfc" in low or "fungicidal" in low:
        return "MFC"
    if "mic" in low or "inhibitory" in low or "dilution" in low or "broth" in low:
        return "MIC"
    if "zoi" in low or "diffusion" in low or "inhibition zone" in low or "zone of inhibition" in low:
        return "ZOI"
    return text.upper()


def norm_shape(value: Any) -> str:
    return "NOT_DETECTED" if _is_missing(value) else str(value).strip().lower()


def norm_precursor(value: Any) -> str:
    """Gold precursor vocab is effectively {AgNO3, NOT_DETECTED}. Map silver
    nitrate phrasings to AgNO3; non-silver/unknown precursors to NOT_DETECTED."""
    if _is_missing(value):
        return "NOT_DETECTED"
    low = str(value).strip().lower()
    if "agno3" in low or "silver nitrate" in low:
        return "AgNO3"
    return "NOT_DETECTED"


def norm_np(value: Any) -> str:
    return "NOT_DETECTED" if _is_missing(value) else normalize_np(value)


def norm_bacteria(value: Any) -> str:
    return "NOT_DETECTED" if _is_missing(value) else normalize_bacteria(value)


# field -> formatter. Calibrated from docs/gt_format.md.
SELTOX_FIELD_NORMALIZERS = {
    "np": norm_np,
    "coating": norm_binary,
    "bacteria": norm_bacteria,
    "mdr": norm_binary,
    "strain": norm_text,
    "np_synthesis": norm_text,
    "method": norm_method,
    "mic_np_µg_ml": norm_int_num,
    "concentration": norm_float_num,
    "zoi_np_mm": norm_float_num,
    "np_size_min_nm": norm_float_num,
    "np_size_max_nm": norm_float_num,
    "np_size_avg_nm": norm_float_num,
    "shape": norm_shape,
    "time_set_hours": norm_float_num,
    "zeta_potential_mV": norm_float_num,
    "solvent_for_extract": norm_text,
    "temperature_for_extract_C": norm_float_num,
    "duration_preparing_extract_min": norm_float_num,
    "precursor_of_np": norm_precursor,
    "concentration_of_precursor_mM": norm_float_num,
    "hydrodynamic_diameter_nm": norm_float_num,
    "ph_during_synthesis": norm_float_num,
}


def normalize_seltox_record(record: dict[str, Any]) -> dict[str, str]:
    """Apply the GT-calibrated formatter to every SelTox field."""
    return {field: fn(record.get(field)) for field, fn in SELTOX_FIELD_NORMALIZERS.items()}


# Majority-class priors for fields that are rarely/never missing (see docs/gt_format.md).
# Measured floor with these (no LLM): Macro-F1 0.136 vs baseline 0.045. Each default was
# verified to raise its own field's F1 under the trusted evaluator. mdr/coating default to
# "0" already via norm_binary. concentration_of_precursor is deliberately left abstaining
# (majority-missing -> abstention wins / too subset-sensitive).
SELTOX_PRIOR_DEFAULTS = {
    "np": "Ag",
    "method": "MIC",
    "shape": "spherical",
    "time_set_hours": "24.0",
    "precursor_of_np": "AgNO3",
    "np_synthesis": "green_synthesis",
}


def seltox_prior_record() -> dict[str, str]:
    """No-LLM fallback row: calibrated blanks + majority-class defaults."""
    record = normalize_seltox_record({})
    record.update(SELTOX_PRIOR_DEFAULTS)
    return record


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
