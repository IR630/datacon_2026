"""Offline checks for the ChemX metric logic used by `validate-evaluator`.

No network / no gold needed: builds tiny frames with real domain columns.
"""

from __future__ import annotations

import pandas as pd

from src.baseline_bridge import extracted_columns
from src.eval.chemx_metric_adapter import (
    calc_column_metrics,
    evaluate_frames,
    prepare_single_agent_pred,
)

DOMAIN = "complexes"  # smallest schema (5 columns)


def _row(cols: list[str], pdf: str, value: str = "x") -> dict[str, str]:
    row = {col: value for col in cols}
    row["pdf"] = pdf
    return row


def test_calc_column_metrics_multiset() -> None:
    # gold {a,a,b} vs pred {a,b,c}: tp=2 (a,b), fp=1 (c), fn=1 (extra a)
    m = calc_column_metrics(["a", "a", "b"], ["a", "b", "c"])
    assert (m["tp"], m["fp"], m["fn"]) == (2, 1, 1)
    assert m["precision"] == 2 / 3
    assert m["recall"] == 2 / 3
    assert abs(m["f1"] - 2 / 3) < 1e-12


def test_prepare_single_agent_pred_appends_pdf_and_lowers() -> None:
    df = pd.DataFrame({"pdf": ["Foo_Bar", "Foo_Bar"], "compound_id": ["1", "1"]})
    # seltox is a suffix-domain: ".pdf" appended, lower-cased, de-duplicated
    out = prepare_single_agent_pred("seltox", df)
    assert list(out["pdf"]) == ["foo_bar.pdf"]


def test_evaluate_frames_denominator_counts_missing_articles() -> None:
    cols = extracted_columns(DOMAIN)
    gold = pd.DataFrame([_row(cols, "a.pdf"), _row(cols, "b.pdf")])
    pred = pd.DataFrame([_row(cols, "a.pdf")])  # perfect on a, nothing for b
    # denominator = 2: a -> f1 1.0, b -> f1 0.0  => mean 0.5 per field
    metrics = evaluate_frames(DOMAIN, gold, pred, articles=["a.pdf", "b.pdf"])
    assert abs(metrics["f1"].mean() - 0.5) < 1e-12
    # single article that matches -> perfect
    metrics_one = evaluate_frames(DOMAIN, gold, pred, articles=["a.pdf"])
    assert abs(metrics_one["f1"].mean() - 1.0) < 1e-12


def test_evaluate_frames_is_case_sensitive_on_article_name() -> None:
    # gold/pred pdf are lower-case; an upper-case article name matches nothing.
    cols = extracted_columns(DOMAIN)
    gold = pd.DataFrame([_row(cols, "a.pdf")])
    pred = pd.DataFrame([_row(cols, "a.pdf")])
    metrics = evaluate_frames(DOMAIN, gold, pred, articles=["A.PDF"])
    assert metrics["f1"].mean() == 0.0
