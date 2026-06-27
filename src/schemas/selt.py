"""Official SelTox record schema helpers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model

from src.baseline_bridge import extracted_columns, numeric_columns


DOMAIN = "seltox"
SELTOX_COLUMNS = extracted_columns(DOMAIN)
SELTOX_NUMERIC_COLUMNS = set(numeric_columns(DOMAIN))


def _field_type(column: str) -> tuple[Any, Any]:
    if column in SELTOX_NUMERIC_COLUMNS:
        return float | int | str, Field(default="NOT_DETECTED")
    return str, Field(default="NOT_DETECTED")


SeltRecord = create_model(
    "SeltRecord",
    __config__=ConfigDict(extra="forbid"),
    **{column: _field_type(column) for column in SELTOX_COLUMNS},
)


class SeltPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pdf: str
    records: list[SeltRecord]


def blank_record() -> dict[str, str]:
    return {column: "NOT_DETECTED" for column in SELTOX_COLUMNS}


def csv_columns() -> list[str]:
    return SELTOX_COLUMNS + ["pdf"]

