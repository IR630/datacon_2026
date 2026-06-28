"""Small bridge to the vendored ChemX baseline constants."""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONSTANTS_PATH = ROOT / "baseline" / "src" / "constants.py"
SCHEMAS_DIR = ROOT / "baseline" / "data" / "schemas"
REFERENCE_METRICS_DIR = ROOT / "baseline" / "reference_metrics"

# Where the published single-agent predictions live (reachable when GitHub is open).
SINGLE_AGENT_BASE = "https://raw.githubusercontent.com/ai-chem/ChemX/main/LLM/result/from_single_agent"
# Domains where the baseline appends ".pdf" to the prediction's pdf column (prepare_result).
PDF_SUFFIX_DOMAINS = frozenset({"cytotoxicity", "seltox", "synergy", "magnetic"})


@lru_cache(maxsize=1)
def constants() -> ModuleType:
    spec = importlib.util.spec_from_file_location("chemx_baseline_constants", CONSTANTS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import baseline constants from {CONSTANTS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_constant(name: str) -> Any:
    return getattr(constants(), name)


def extracted_columns(domain: str) -> list[str]:
    return list(get_constant("EXTRACTED_COLUMNS")[domain])


def numeric_columns(domain: str) -> list[str]:
    return list(get_constant("NUMERIC_COLUMNS")[domain])


def smiles_columns(domain: str) -> list[str]:
    return list(get_constant("SMILES_COLS")[domain])


def dataset_id(domain: str) -> str:
    return str(get_constant("DATASETS_IDS")[domain])


def article_subset(domain: str) -> list[str] | None:
    if domain == "seltox":
        return list(get_constant("SELTOX_ARTICLES"))
    if domain == "magnetic":
        return list(get_constant("MAGNETIC_ARTICLES"))
    return None


def schema_path(domain: str) -> Path:
    return SCHEMAS_DIR / f"{domain}.json"


def single_agent_pred_url(domain: str) -> str:
    return f"{SINGLE_AGENT_BASE}/{domain}/pred.csv"


def appends_pdf_suffix(domain: str) -> bool:
    return domain in PDF_SUFFIX_DOMAINS


def reference_metrics_path(domain: str, source: str = "single_agent") -> Path:
    return REFERENCE_METRICS_DIR / f"metrics_{domain}_from_{source}.csv"

