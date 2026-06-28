"""Streamlit UI for the SelTox-MAX deadline demo."""

from __future__ import annotations

from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Callable

import pandas as pd
import streamlit as st

from src.agents.base import LLMSettings
from src.baseline_bridge import article_subset
from src.cli import cmd_build_submission, cmd_extract
from src.eval.chemx_metric_adapter import evaluate_prediction_file
from src.parse.ensemble import parse_pdf
from src.retrieve.evidence_finder import find_evidence
from src.utils.io import ensure_dir


DATA_DIR = Path("data")
PRED_DIR = DATA_DIR / "predictions"
PDF_DIR = DATA_DIR / "pdfs"
GOLD_PATH = DATA_DIR / "gold" / "seltox.parquet"
DEFAULT_EXTRACTED = PRED_DIR / "selt_batch_resolved.csv"
DEFAULT_SUBMISSION = PRED_DIR / "seltox_submission_resolved.csv"
DEFAULT_METRICS = PRED_DIR / "seltox_submission_resolved_metrics.csv"


def run_cli(func: Callable[[Namespace], None], args: Namespace) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(args)
    return buffer.getvalue().strip()


def count_files(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    return len(list(path.glob(pattern)))


def read_metrics(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path, index_col=0)


def metric_summary(metrics: pd.DataFrame | None) -> str:
    if metrics is None or "f1" not in metrics:
        return "not ready"
    return f"{metrics['f1'].mean():.6f}"


def build_submission(extracted_path: str, out_path: str) -> str:
    extracted = extracted_path.strip() or None
    if extracted and not Path(extracted).exists():
        raise FileNotFoundError(extracted)
    return run_cli(
        cmd_build_submission,
        Namespace(domain="seltox", extracted=extracted, out=out_path),
    )


def evaluate_submission(pred_path: str, metrics_path: str) -> pd.DataFrame:
    pred = Path(pred_path)
    if not pred.exists():
        raise FileNotFoundError(pred)
    metrics = evaluate_prediction_file("seltox", pred)
    out = Path(metrics_path)
    ensure_dir(out.parent)
    metrics.to_csv(out)
    return metrics


def download_csv(path: Path, label: str) -> None:
    if path.exists():
        st.download_button(label, path.read_bytes(), file_name=path.name)


st.set_page_config(page_title="SelTox-MAX", layout="wide")

target_count = len(article_subset("seltox") or [])
pdf_count = count_files(PDF_DIR, "*.pdf")
parsed_count = count_files(DATA_DIR / "parsed", "*/chunks.json")
metrics = read_metrics(DEFAULT_METRICS)
llm_summary = LLMSettings.from_env().sanitized_summary()

st.title("SelTox-MAX")

status_cols = st.columns(5)
status_cols[0].metric("Gold", "ready" if GOLD_PATH.exists() else "missing")
status_cols[1].metric("Target PDFs", target_count)
status_cols[2].metric("Local PDFs", pdf_count)
status_cols[3].metric("Parsed PDFs", parsed_count)
status_cols[4].metric("Macro-F1", metric_summary(metrics))

dataset_tab, pdf_tab, config_tab = st.tabs(["Dataset run", "Single PDF", "Config"])

with dataset_tab:
    left, right = st.columns([1, 1])

    with left:
        st.subheader("Submission")
        extracted_path = st.text_input("Extracted CSV", str(DEFAULT_EXTRACTED if DEFAULT_EXTRACTED.exists() else ""))
        submission_path = st.text_input("Submission CSV", str(DEFAULT_SUBMISSION))
        metrics_path = st.text_input("Metrics CSV", str(DEFAULT_METRICS))

        action_cols = st.columns(2)
        if action_cols[0].button("Build", width="stretch"):
            with st.spinner("Building submission"):
                try:
                    log = build_submission(extracted_path, submission_path)
                    st.success("Submission built")
                    if log:
                        st.code(log, language="text")
                except Exception as exc:
                    st.error(str(exc))

        if action_cols[1].button("Evaluate", width="stretch"):
            with st.spinner("Evaluating submission"):
                try:
                    metrics = evaluate_submission(submission_path, metrics_path)
                    st.success(f"Macro-F1: {metrics['f1'].mean():.6f}")
                except Exception as exc:
                    st.error(str(exc))

        download_csv(Path(submission_path), "Download submission")
        download_csv(Path(metrics_path), "Download metrics")

    with right:
        st.subheader("Metrics")
        current_metrics = read_metrics(Path(metrics_path))
        if current_metrics is None:
            current_metrics = metrics
        if current_metrics is not None:
            st.dataframe(
                current_metrics.sort_values("f1", ascending=False),
                width="stretch",
            )
        else:
            st.info("No metrics yet")

with pdf_tab:
    uploaded = st.file_uploader("PDF", type=["pdf"])
    if uploaded:
        upload_dir = ensure_dir(DATA_DIR / "uploads")
        pdf_path = upload_dir / uploaded.name
        pdf_path.write_bytes(uploaded.getbuffer())
        st.caption(str(pdf_path))

        run_cols = st.columns(3)
        if run_cols[0].button("Parse", width="stretch"):
            with st.spinner("Parsing PDF"):
                outputs = parse_pdf(pdf_path)
                st.json({name: str(path) for name, path in outputs.items()})

        if run_cols[1].button("Evidence", width="stretch"):
            with st.spinner("Finding evidence"):
                parsed_dir = Path("data/parsed") / pdf_path.stem
                if not (parsed_dir / "chunks.json").exists():
                    parse_pdf(pdf_path)
                evidence = find_evidence(parsed_dir, top_k=5)
                for group, items in evidence.items():
                    st.subheader(group)
                    for item in items:
                        st.caption(
                            f"page {item.get('page')} | {item.get('source_type')} | "
                            f"score {item.get('score')}"
                        )
                        st.write(item.get("text", "")[:1000])

        if run_cols[2].button("Extract", width="stretch"):
            with st.spinner("Extracting CSV"):
                out = PRED_DIR / f"{pdf_path.stem}_selt.csv"
                args = Namespace(pdf=str(pdf_path), parsed_dir="data/parsed", top_k=8, out=str(out), domain="SelTox")
                log = run_cli(cmd_extract, args)
                df = pd.read_csv(out)
                st.dataframe(df, width="stretch")
                download_csv(out, "Download PDF CSV")
                if log:
                    st.code(log, language="text")

with config_tab:
    cfg_left, cfg_right = st.columns([1, 1])
    with cfg_left:
        st.subheader("LLM")
        st.json(llm_summary)
    with cfg_right:
        st.subheader("Local artifacts")
        st.write(
            pd.DataFrame(
                [
                    {"name": "gold", "path": str(GOLD_PATH), "exists": GOLD_PATH.exists()},
                    {"name": "extracted", "path": str(DEFAULT_EXTRACTED), "exists": DEFAULT_EXTRACTED.exists()},
                    {"name": "submission", "path": str(DEFAULT_SUBMISSION), "exists": DEFAULT_SUBMISSION.exists()},
                    {"name": "metrics", "path": str(DEFAULT_METRICS), "exists": DEFAULT_METRICS.exists()},
                ]
            )
        )
