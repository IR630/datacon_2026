"""Minimal Streamlit UI for the SelTox MVP."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pandas as pd
import streamlit as st

from src.cli import cmd_extract
from src.parse.ensemble import parse_pdf
from src.retrieve.evidence_finder import find_evidence
from src.utils.io import ensure_dir


st.set_page_config(page_title="SelTox-MAX", layout="wide")
st.title("SelTox-MAX")

uploaded = st.file_uploader("PDF", type=["pdf"])
if uploaded:
    upload_dir = ensure_dir("data/uploads")
    pdf_path = upload_dir / uploaded.name
    pdf_path.write_bytes(uploaded.getbuffer())
    st.write(f"Saved: `{pdf_path}`")

    if st.button("Parse"):
        outputs = parse_pdf(pdf_path)
        st.json({name: str(path) for name, path in outputs.items()})

    if st.button("Show Evidence"):
        parsed_dir = Path("data/parsed") / pdf_path.stem
        if not (parsed_dir / "chunks.json").exists():
            parse_pdf(pdf_path)
        evidence = find_evidence(parsed_dir, top_k=5)
        for group, items in evidence.items():
            st.subheader(group)
            for item in items:
                st.caption(f"page {item.get('page')} | {item.get('source_type')} | score {item.get('score')}")
                st.write(item.get("text", "")[:1000])

    if st.button("Extract Skeleton CSV"):
        out = Path("data/predictions") / f"{pdf_path.stem}_selt.csv"
        args = Namespace(pdf=str(pdf_path), parsed_dir="data/parsed", top_k=8, out=str(out), domain="SelTox")
        cmd_extract(args)
        df = pd.read_csv(out)
        st.dataframe(df, use_container_width=True)
        st.download_button("Download CSV", df.to_csv(index=False), file_name=out.name)
