"""ChemX-compatible metric adapter.

This mirrors the baseline metric shape while allowing local gold caches.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from src.baseline_bridge import (
    appends_pdf_suffix,
    article_subset,
    dataset_id,
    extracted_columns,
    numeric_columns,
    reference_metrics_path,
)


def read_parquet(path: str | Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(path)
    except ImportError:
        try:
            import polars as pl
        except Exception as exc:
            raise ImportError("Reading parquet requires pyarrow/fastparquet or polars") from exc
        return pd.DataFrame(pl.read_parquet(path).to_dicts())


def convert_comma(value: object) -> str:
    try:
        return str(value).replace(",", ".")
    except Exception:
        return str(value)


def load_local_gold(domain: str, gold_dir: str | Path = "data/gold") -> pd.DataFrame | None:
    base = Path(gold_dir)
    for ext in (".parquet", ".csv"):
        path = base / f"{domain}{ext}"
        if path.exists():
            if ext == ".parquet":
                return read_parquet(path)
            return pd.read_csv(path)
    return None


def load_gold(domain: str, gold_dir: str | Path = "data/gold", apply_subset: bool = True) -> pd.DataFrame:
    local = load_local_gold(domain, gold_dir)
    if local is not None:
        return prepare_gold(domain, local, apply_subset=apply_subset)
    try:
        from datasets import load_dataset
    except Exception as exc:
        raise FileNotFoundError(
            f"No local gold found in {gold_dir}. Put {domain}.csv/parquet there or install datasets."
        ) from exc
    ds = load_dataset(dataset_id(domain))
    return prepare_gold(domain, ds["train"].to_pandas(), apply_subset=apply_subset)


def prepare_gold(domain: str, df: pd.DataFrame, apply_subset: bool = True) -> pd.DataFrame:
    out = df.copy()
    for col in numeric_columns(domain):
        if col in out.columns:
            out[col] = out[col].apply(convert_comma)
    out = out.fillna("NOT_DETECTED")
    if "access" in out.columns:
        out = out.loc[out["access"] == 1].copy()
    if "pdf" in out.columns:
        out["pdf"] = out["pdf"].astype(str).str.lower()
    if apply_subset:
        subset = article_subset(domain)
        if subset:
            subset_lower = {item.lower() for item in subset}
            out = out.loc[out["pdf"].isin(subset_lower)].copy()
    return out


def prepare_single_agent_pred(domain: str, df: pd.DataFrame) -> pd.DataFrame:
    """Mirror baseline ``prepare_result(source='single_agent')`` exactly.

    Appends ``.pdf`` for the suffix domains, lower-cases ``pdf``, drops duplicates.
    Deliberately does NOT convert commas or fill NaNs (the baseline does not either).
    """
    out = df.copy()
    if appends_pdf_suffix(domain):
        out["pdf"] = out["pdf"].astype(str) + ".pdf"
    out["pdf"] = out["pdf"].astype(str).str.lower()
    return out.drop_duplicates()


def prepare_pred(domain: str, pred_path: str | Path) -> pd.DataFrame:
    cols = extracted_columns(domain)
    df = pd.read_csv(pred_path)
    missing = [col for col in cols + ["pdf"] if col not in df.columns]
    if missing:
        raise ValueError(f"Prediction is missing columns: {missing}")
    df = df[cols + ["pdf"]].copy()
    df["pdf"] = df["pdf"].astype(str).str.lower()
    numeric = set(numeric_columns(domain))
    for col in cols:
        fill_value = "nan" if col in numeric else "NOT_DETECTED"
        df[col] = df[col].where(df[col].notna(), fill_value)
    for col in numeric_columns(domain):
        df[col] = df[col].apply(convert_comma)
    return df.drop_duplicates()


def calc_column_metrics(true_values: list[str], pred_values: list[str]) -> dict[str, float]:
    true_counter = Counter(map(str, true_values))
    pred_counter = Counter(map(str, pred_values))
    tp = sum((true_counter & pred_counter).values())
    fp = sum((pred_counter - true_counter).values())
    fn = sum((true_counter - pred_counter).values())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def evaluate_frames(
    domain: str,
    gold: pd.DataFrame,
    pred: pd.DataFrame,
    articles: list[str] | None = None,
) -> pd.DataFrame:
    cols = extracted_columns(domain)
    metrics = {col: {"tp": 0.0, "fp": 0.0, "fn": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0} for col in cols}
    if articles is None:
        articles = sorted(set(gold["pdf"].astype(str).str.lower()))
    if not articles:
        raise ValueError("Gold contains no articles after filtering.")
    for article in articles:
        gold_rows = gold.loc[gold["pdf"] == article, cols]
        pred_rows = pred.loc[pred["pdf"] == article, cols]
        for col in cols:
            item = calc_column_metrics(list(gold_rows[col].astype(str)), list(pred_rows[col].astype(str)))
            for key, value in item.items():
                metrics[col][key] += value
    df = pd.DataFrame(metrics).T / len(articles)
    return df


def evaluate_prediction_file(domain: str, pred_path: str | Path, gold_dir: str | Path = "data/gold") -> pd.DataFrame:
    gold = load_gold(domain, gold_dir)
    pred = prepare_pred(domain, pred_path)
    return evaluate_frames(domain, gold, pred)


METRIC_COLUMNS = ["tp", "fp", "fn", "precision", "recall", "f1"]


def load_reference_metrics(domain: str, source: str = "single_agent") -> pd.DataFrame:
    return pd.read_csv(reference_metrics_path(domain, source), index_col=0)


def reproduce_single_agent_metrics(
    domain: str,
    gold_dir: str | Path = "data/gold",
    pred: pd.DataFrame | None = None,
    lowercase_articles: bool = False,
) -> pd.DataFrame:
    """Recompute the published single-agent metrics with our evaluator (1:1 with baseline).

    ``lowercase_articles=False`` mirrors the baseline literally (it iterates the article
    subset as-is from ``np.load`` while gold/pred ``pdf`` are lower-cased). The validate
    command tries both so we learn which one matches the published numbers.
    """
    gold = load_gold(domain, gold_dir, apply_subset=False)
    if pred is None:
        from src.data.single_agent import fetch_single_agent_pred

        pred = fetch_single_agent_pred(domain)
    pred = prepare_single_agent_pred(domain, pred)
    subset = article_subset(domain)
    if subset:
        articles = [item.lower() for item in subset] if lowercase_articles else list(subset)
    else:
        articles = sorted(set(gold["pdf"].astype(str).str.lower()))
    return evaluate_frames(domain, gold, pred, articles=articles)


def diff_to_reference(ours: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    common = [idx for idx in ours.index if idx in reference.index]
    return (ours.loc[common, METRIC_COLUMNS] - reference.loc[common, METRIC_COLUMNS]).abs()
