"""Single schema-driven LLM extractor for SelTox (Phase 3).

Full-document context (no BM25 top-k), one record per (bacteria x nanoparticle),
abstention-first: unknown fields are left null and become nan downstream. The
strict JSON schema is deliberately NOT used (it forces non-null numerics and would
break abstention); instead the prompt fixes the key set and asks for null on misses.
Normalization happens later in build-submission --extracted.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.agents.base import LLMClient
from src.baseline_bridge import extracted_columns
from src.utils.io import ensure_dir

_COLS = extracted_columns("seltox")

_SYSTEM = (
    "You extract structured experimental data about the antimicrobial activity and "
    "toxicity of (mostly silver) nanoparticles from a scientific paper, following the "
    'ChemX SelTox schema. Return ONLY a JSON object of the form {"samples": [ ... ]}. '
    "Emit one sample object per tested (bacteria x nanoparticle) pair. "
    "Use exactly these keys in every sample: " + ", ".join(_COLS) + ". "
    "If a value is not explicitly reported in the paper, set it to null - never guess. "
    "Numeric fields must be JSON numbers (not strings); textual fields short strings."
)

_USER_TEMPLATE = (
    "Paper text (full document, page-tagged):\n\n{document}\n\n"
    "Extract all (bacteria x nanoparticle) activity rows as JSON now."
)


def _load_document(parsed_dir: Path, max_chars: int = 120_000) -> str:
    parts: list[str] = []
    pages = json.loads((parsed_dir / "pages.json").read_text(encoding="utf-8"))
    for page in pages:
        parts.append(f"[page {page.get('page')}]\n{page.get('text', '')}")
    tables_path = parsed_dir / "tables.json"
    if tables_path.exists():
        for table in json.loads(tables_path.read_text(encoding="utf-8")):
            markdown = table.get("markdown") or table.get("text") or ""
            if markdown:
                parts.append(f"[table p.{table.get('page')}]\n{markdown}")
    return "\n\n".join(parts)[:max_chars]


def _parse_samples(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return []
        try:
            obj = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    samples = obj.get("samples", []) if isinstance(obj, dict) else []
    return [{col: sample.get(col) for col in _COLS} for sample in samples if isinstance(sample, dict)]


class SeltoxExtractor:
    def __init__(self, client: LLMClient | None = None) -> None:
        self.client = client or LLMClient()

    def extract_pdf(self, parsed_dir: str | Path, cache_dir: str | Path = "data/cache") -> list[dict[str, Any]]:
        parsed_dir = Path(parsed_dir)
        messages = [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _USER_TEMPLATE.format(document=_load_document(parsed_dir))},
        ]
        raw = self.client.complete_text(messages)
        ensure_dir(Path(cache_dir))
        (Path(cache_dir) / f"{parsed_dir.name}.response.txt").write_text(raw, encoding="utf-8")
        return _parse_samples(raw)
