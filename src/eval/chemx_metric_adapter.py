"""ChemX-compatible metric adapter.

This mirrors the baseline metric shape while allowing local gold caches.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from src.baseline_bridge import article_subset, dataset_id, extracted_columns, numeric_columns


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
                return pd.read_parquet(path)
            return pd.read_csv(path)
    return None


def load_gold(domain: str, gold_dir: str | Path = "data/gold") -> pd.DataFrame:
    local = load_local_gold(domain, gold_dir)
    if local is not None:
        return prepare_gold(domain, local)
    try:
        from datasets import load_dataset
    except Exception as exc:
        raise FileNotFoundError(
            f"No local gold found in {gold_dir}. Put {domain}.csv/parquet there or install datasets."
        ) from exc
    ds = load_dataset(dataset_id(domain))
    return prepare_gold(domain, ds["train"].to_pandas())


def prepare_gold(domain: str, df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in numeric_columns(domain):
        if col in out.columns:
            out[col] = out[col].apply(convert_comma)
    out = out.fillna("NOT_DETECTED")
    if "access" in out.columns:
        out = out.loc[out["access"] == 1].copy()
    if "pdf" in out.columns:
        out["pdf"] = out["pdf"].astype(str).str.lower()
    subset = article_subset(domain)
    if subset:
        subset_lower = {item.lower() for item in subset}
        out = out.loc[out["pdf"].isin(subset_lower)].copy()
    return out


def prepare_pred(domain: str, pred_path: str | Path) -> pd.DataFrame:
    cols = extracted_columns(domain)
    df = pd.read_csv(pred_path).fillna("NOT_DETECTED")
    missing = [col for col in cols + ["pdf"] if col not in df.columns]
    if missing:
        raise ValueError(f"Prediction is missing columns: {missing}")
    df = df[cols + ["pdf"]].drop_duplicates()
    df["pdf"] = df["pdf"].astype(str).str.lower()
    for col in numeric_columns(domain):
        df[col] = df[col].apply(convert_comma)
    return df


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


def evaluate_frames(domain: str, gold: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    cols = extracted_columns(domain)
    metrics = {col: {"tp": 0.0, "fp": 0.0, "fn": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0} for col in cols}
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

