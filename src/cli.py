"""Command line interface for the SelTox MVP."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import pandas as pd

from src.agents.activity_extractor import ActivityExtractorAgent
from src.agents.base import LLMClient, LLMNotConfigured, LLMSettings
from src.agents.nanoparticle_extractor import NanoparticleExtractorAgent
from src.agents.synthesis_extractor import SynthesisExtractorAgent
from src.agents.validator import ValidatorAgent
from src.baseline_bridge import article_subset, dataset_id, extracted_columns, numeric_columns, schema_path
from src.data.pdf_resolver import resolve_one_pdf
from src.eval.chemx_metric_adapter import evaluate_frames, evaluate_prediction_file, load_gold, load_local_gold, prepare_gold
from src.parse.ensemble import parse_pdf
from src.postprocess.deduplicate import deduplicate_records
from src.postprocess.link_records import merge_article_level_records
from src.retrieve.evidence_finder import find_evidence
from src.schemas.selt import SELTOX_COLUMNS
from src.utils.io import ensure_dir, write_json


def cmd_inspect_selt(args: argparse.Namespace) -> None:
    domain = "seltox"
    print(f"Domain: {domain}")
    print(f"Dataset: {dataset_id(domain)}")
    print(f"Schema: {schema_path(domain)}")
    print(f"Target columns ({len(extracted_columns(domain))}):")
    for col in extracted_columns(domain):
        mark = " [numeric]" if col in numeric_columns(domain) else ""
        print(f"  - {col}{mark}")
    subset = article_subset(domain) or []
    print(f"Evaluation article subset: {len(subset)} files")
    if subset:
        print("First subset files:")
        for name in subset[:10]:
            print(f"  - {name}")

    gold = load_local_gold(domain, args.gold_dir)
    if gold is None:
        print(f"No local gold found in {args.gold_dir}; put seltox.csv or seltox.parquet there for metrics.")
        return
    print(f"Local gold rows: {len(gold)}")
    print("Columns:")
    for col in gold.columns:
        print(f"  - {col}")
    print("Sample rows:")
    print(gold.head(args.samples).to_string(index=False))


def cmd_parse(args: argparse.Namespace) -> None:
    outputs = parse_pdf(args.pdf, args.parsed_dir)
    print("Parsed artifacts:")
    for name, path in outputs.items():
        print(f"  {name}: {path}")


def _parsed_dir_for_pdf(pdf: str | Path, parsed_root: str | Path) -> Path:
    return Path(parsed_root) / Path(pdf).stem


def cmd_evidence(args: argparse.Namespace) -> None:
    parsed_dir = _parsed_dir_for_pdf(args.pdf, args.parsed_dir)
    if not (parsed_dir / "chunks.json").exists():
        parse_pdf(args.pdf, args.parsed_dir)
    grouped = find_evidence(parsed_dir, top_k=args.top_k)
    for group, items in grouped.items():
        print(f"\n== {group.upper()} ==")
        for item in items:
            text = " ".join(item.get("text", "").split())
            print(f"[score={item['score']}] p.{item.get('page')} {item.get('source_type')} {item.get('id', '')}")
            print(f"  hits={','.join(item.get('regex_hits', [])) or '-'}")
            print(f"  {text[:500]}")


def cmd_extract(args: argparse.Namespace) -> None:
    parsed_dir = _parsed_dir_for_pdf(args.pdf, args.parsed_dir)
    if not (parsed_dir / "chunks.json").exists():
        parse_pdf(args.pdf, args.parsed_dir)
    grouped = find_evidence(parsed_dir, top_k=args.top_k)
    activity_records = ActivityExtractorAgent().extract(grouped.get("activity", []))
    np_record = NanoparticleExtractorAgent().extract(grouped.get("nanoparticle", []))
    synthesis_record = SynthesisExtractorAgent().extract(grouped.get("synthesis", []))
    article_record = merge_article_level_records(np_record, synthesis_record)
    if activity_records:
        records = [merge_article_level_records(article_record, activity_record) for activity_record in activity_records]
    else:
        records = [article_record]
    for record in records:
        record["pdf"] = Path(args.pdf).name.lower()
    records = deduplicate_records(records)
    validated, reports = ValidatorAgent().validate(records)

    out = Path(args.out)
    ensure_dir(out.parent)
    pd.DataFrame(validated).reindex(columns=SELTOX_COLUMNS + ["pdf"]).to_csv(out, index=False)
    write_json(out.with_suffix(".validation.json"), reports)
    write_json(out.with_suffix(".evidence.json"), grouped)
    print(f"Saved prediction CSV: {out}")
    print(f"Saved validation report: {out.with_suffix('.validation.json')}")
    print("Note: this is a deterministic skeleton; configure LLM agents before serious scoring.")


def cmd_batch_extract(args: argparse.Namespace) -> None:
    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.exists():
        raise FileNotFoundError(pdf_dir)
    rows = []
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        out_one = Path(args.work_dir) / f"{pdf.stem}_selt.csv"
        extract_args = argparse.Namespace(
            pdf=str(pdf),
            domain=args.domain,
            out=str(out_one),
            parsed_dir=args.parsed_dir,
            top_k=args.top_k,
        )
        cmd_extract(extract_args)
        rows.append(pd.read_csv(out_one))
    out = Path(args.out)
    ensure_dir(out.parent)
    if rows:
        pd.concat(rows, ignore_index=True).reindex(columns=SELTOX_COLUMNS + ["pdf"]).to_csv(out, index=False)
    else:
        pd.DataFrame(columns=SELTOX_COLUMNS + ["pdf"]).to_csv(out, index=False)
    print(f"Saved batch prediction CSV: {out}")


def cmd_evaluate(args: argparse.Namespace) -> None:
    metrics = evaluate_prediction_file(args.domain, args.pred, args.gold_dir)
    print(metrics)
    print(f"Macro-F1: {metrics['f1'].mean():.6f}")
    if args.out:
        out = Path(args.out)
        ensure_dir(out.parent)
        metrics.to_csv(out)
        print(f"Saved metrics: {out}")


def cmd_cache_gold(args: argparse.Namespace) -> None:
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except Exception as exc:
        raise SystemExit("huggingface_hub is not installed") from exc

    domain = args.domain.lower()
    repo_id = dataset_id(domain)
    files = HfApi().list_repo_files(repo_id, repo_type="dataset")
    candidates = [name for name in files if name.endswith((".parquet", ".csv"))]
    if not candidates:
        raise SystemExit(f"No parquet/csv files found in {repo_id}")
    candidate = sorted(candidates)[0]
    src = hf_hub_download(repo_id, candidate, repo_type="dataset")
    suffix = Path(candidate).suffix
    out = Path(args.gold_dir) / f"{domain}{suffix}"
    ensure_dir(out.parent)
    shutil.copyfile(src, out)
    print(f"Cached {repo_id}:{candidate} -> {out}")


def cmd_inspect_gold(args: argparse.Namespace) -> None:
    domain = args.domain.lower()
    raw = load_local_gold(domain, args.gold_dir)
    if raw is None:
        raise SystemExit(f"No local gold found in {args.gold_dir}; run cache-gold first.")
    prepared = prepare_gold(domain, raw)
    cols = extracted_columns(domain)
    print(f"Raw shape: {raw.shape}")
    print(f"Prepared shape: {prepared.shape}")
    if "pdf" in raw.columns:
        print(f"Raw PDF count: {raw['pdf'].nunique()}")
    if "pdf" in prepared.columns:
        print(f"Prepared PDF count: {prepared['pdf'].nunique()}")
    print("Target null counts before fillna:")
    print(raw[cols].isna().sum().to_string())
    print("Prepared target columns sample:")
    print(prepared[cols + ["pdf"]].head(args.samples).to_string(index=False))


def cmd_gold_sanity(args: argparse.Namespace) -> None:
    domain = args.domain.lower()
    gold = load_gold(domain, args.gold_dir)
    cols = extracted_columns(domain)
    pred = gold[cols + ["pdf"]].copy()
    metrics = evaluate_frames(domain, gold, pred)
    print(metrics)
    print(f"Macro-F1: {metrics['f1'].mean():.6f}")


def _blank_record_for_domain(domain: str) -> dict[str, str]:
    numeric = set(numeric_columns(domain))
    return {col: "nan" if col in numeric else "NOT_DETECTED" for col in extracted_columns(domain)}


def cmd_prior_pred(args: argparse.Namespace) -> None:
    domain = args.domain.lower()
    subset = article_subset(domain)
    if subset:
        pdfs = [item.lower() for item in subset]
    else:
        gold = load_gold(domain, args.gold_dir)
        pdfs = sorted(gold["pdf"].astype(str).str.lower().unique())
    rows = []
    for pdf in pdfs:
        for _ in range(args.rows_per_pdf):
            row = _blank_record_for_domain(domain)
            row["pdf"] = pdf
            rows.append(row)
    out = Path(args.out)
    ensure_dir(out.parent)
    pd.DataFrame(rows).reindex(columns=extracted_columns(domain) + ["pdf"]).to_csv(out, index=False)
    print(f"Saved prior prediction CSV: {out}")
    print(f"Rows: {len(rows)}; PDFs: {len(pdfs)}; rows_per_pdf: {args.rows_per_pdf}")


def cmd_resolve_pdfs(args: argparse.Namespace) -> None:
    domain = args.domain.lower()
    gold = load_gold(domain, args.gold_dir)
    pairs = (
        gold[["pdf", "doi"]]
        .drop_duplicates()
        .sort_values("pdf")
        .iloc[args.start : args.start + args.limit if args.limit else None]
    )
    reports = []
    for idx, row in enumerate(pairs.itertuples(index=False), start=1):
        report = resolve_one_pdf(str(row.doi), str(row.pdf), args.out_dir)
        reports.append(report)
        print(f"[{idx}/{len(pairs)}] {report['status']}: {report['pdf']}")
        if args.sleep and idx < len(pairs):
            time.sleep(args.sleep)
    report_path = Path(args.report)
    ensure_dir(report_path.parent)
    write_json(report_path, reports)
    counts = pd.Series([item["status"] for item in reports]).value_counts()
    print("Status counts:")
    print(counts.to_string())
    print(f"Saved report: {report_path}")


def cmd_llm_smoke(args: argparse.Namespace) -> None:
    settings = LLMSettings.from_env()
    if args.provider:
        settings.provider = args.provider
    if args.model:
        settings.model = args.model
    if args.base_url:
        settings.base_url = args.base_url
    if args.folder_id:
        settings.yandex_folder_id = args.folder_id
    settings.max_output_tokens = args.max_output_tokens

    print("LLM config:")
    print(json.dumps(settings.sanitized_summary(), ensure_ascii=False, indent=2))
    if args.dry_run:
        return

    messages = [{"role": "user", "content": args.prompt}]
    try:
        llm = LLMClient(settings)
        text = llm.complete_text(messages, max_output_tokens=args.max_output_tokens)
    except LLMNotConfigured as exc:
        raise SystemExit(f"LLM is not configured: {exc}") from exc
    print("LLM response:")
    print(text)
    if llm.last_usage:
        print("LLM usage:")
        print(json.dumps(llm.last_usage, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SelTox-MAX CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inspect-selt")
    p.add_argument("--gold-dir", default="data/gold")
    p.add_argument("--samples", type=int, default=5)
    p.set_defaults(func=cmd_inspect_selt)

    p = sub.add_parser("parse")
    p.add_argument("--pdf", required=True)
    p.add_argument("--parsed-dir", default="data/parsed")
    p.set_defaults(func=cmd_parse)

    p = sub.add_parser("evidence")
    p.add_argument("--pdf", required=True)
    p.add_argument("--domain", default="SelTox")
    p.add_argument("--parsed-dir", default="data/parsed")
    p.add_argument("--top-k", type=int, default=6)
    p.set_defaults(func=cmd_evidence)

    p = sub.add_parser("extract")
    p.add_argument("--pdf", required=True)
    p.add_argument("--domain", default="SelTox")
    p.add_argument("--out", required=True)
    p.add_argument("--parsed-dir", default="data/parsed")
    p.add_argument("--top-k", type=int, default=8)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("batch-extract")
    p.add_argument("--pdf-dir", required=True)
    p.add_argument("--domain", default="SelTox")
    p.add_argument("--out", required=True)
    p.add_argument("--parsed-dir", default="data/parsed")
    p.add_argument("--work-dir", default="data/predictions/per_pdf")
    p.add_argument("--top-k", type=int, default=8)
    p.set_defaults(func=cmd_batch_extract)

    p = sub.add_parser("evaluate")
    p.add_argument("--pred", required=True)
    p.add_argument("--domain", default="seltox")
    p.add_argument("--gold-dir", default="data/gold")
    p.add_argument("--out")
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser("cache-gold")
    p.add_argument("--domain", default="seltox")
    p.add_argument("--gold-dir", default="data/gold")
    p.set_defaults(func=cmd_cache_gold)

    p = sub.add_parser("inspect-gold")
    p.add_argument("--domain", default="seltox")
    p.add_argument("--gold-dir", default="data/gold")
    p.add_argument("--samples", type=int, default=5)
    p.set_defaults(func=cmd_inspect_gold)

    p = sub.add_parser("gold-sanity")
    p.add_argument("--domain", default="seltox")
    p.add_argument("--gold-dir", default="data/gold")
    p.set_defaults(func=cmd_gold_sanity)

    p = sub.add_parser("prior-pred")
    p.add_argument("--domain", default="seltox")
    p.add_argument("--gold-dir", default="data/gold")
    p.add_argument("--rows-per-pdf", type=int, default=1)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_prior_pred)

    p = sub.add_parser("resolve-pdfs")
    p.add_argument("--domain", default="seltox")
    p.add_argument("--gold-dir", default="data/gold")
    p.add_argument("--out-dir", default="data/pdfs")
    p.add_argument("--report", default="data/cache/pdf_resolver_report.json")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--sleep", type=float, default=0.2)
    p.set_defaults(func=cmd_resolve_pdfs)

    p = sub.add_parser("llm-smoke")
    p.add_argument("--provider", default="")
    p.add_argument("--model", default="")
    p.add_argument("--base-url", default="")
    p.add_argument("--folder-id", default="")
    p.add_argument("--max-output-tokens", type=int, default=128)
    p.add_argument(
        "--prompt",
        default="Say OK",
    )
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_llm_smoke)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
