"""Resolve open-access PDF links from DOI metadata."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from src.utils.io import ensure_dir


CROSSREF_WORKS = "https://api.crossref.org/works/{doi}"
HEADERS = {
    "User-Agent": "datacon_2026_selt_mvp/0.1 (mailto:example@example.com)",
    "Accept": "application/pdf,application/json,text/html;q=0.8,*/*;q=0.5",
}


def safe_pdf_name(name: str) -> str:
    cleaned = str(name).strip().lower().replace("\\", "_").replace("/", "_")
    return cleaned if cleaned.endswith(".pdf") else f"{cleaned}.pdf"


def crossref_work(doi: str, timeout: int = 20) -> dict[str, Any]:
    url = CROSSREF_WORKS.format(doi=quote(str(doi).strip(), safe=""))
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.json().get("message", {})


def pdf_candidates(work: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for link in work.get("link", []) or []:
        url = str(link.get("URL", "")).strip()
        content_type = str(link.get("content-type", "")).lower()
        if not url:
            continue
        lower = url.lower()
        if "pdf" in content_type or lower.endswith(".pdf") or "/pdf" in lower or "download=1" in lower:
            urls.append(url)
    return list(dict.fromkeys(urls))


def looks_like_pdf(content: bytes, content_type: str = "") -> bool:
    if content.startswith(b"%PDF"):
        return True
    return "pdf" in content_type.lower() and len(content) > 1000


def download_pdf(url: str, out_path: str | Path, timeout: int = 45) -> bool:
    resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    if resp.status_code >= 400:
        return False
    content = resp.content
    if not looks_like_pdf(content, resp.headers.get("content-type", "")):
        return False
    out = Path(out_path)
    ensure_dir(out.parent)
    out.write_bytes(content)
    return True


def resolve_one_pdf(doi: str, pdf_name: str, out_dir: str | Path) -> dict[str, Any]:
    out_path = Path(out_dir) / safe_pdf_name(pdf_name)
    report: dict[str, Any] = {
        "pdf": safe_pdf_name(pdf_name),
        "doi": doi,
        "out_path": str(out_path),
        "status": "pending",
        "candidates": [],
        "selected_url": "",
        "error": "",
    }
    if out_path.exists() and out_path.stat().st_size > 1000:
        report["status"] = "exists"
        return report
    if not doi or str(doi).strip().lower() in {"nan", "not_detected"}:
        report["status"] = "no_doi"
        return report
    try:
        work = crossref_work(str(doi))
        candidates = pdf_candidates(work)
        report["candidates"] = candidates
        for url in candidates:
            if download_pdf(url, out_path):
                report["status"] = "downloaded"
                report["selected_url"] = url
                return report
        report["status"] = "no_pdf_downloaded" if candidates else "no_pdf_candidate"
    except Exception as exc:
        report["status"] = "error"
        report["error"] = re.sub(r"\s+", " ", str(exc))[:500]
    return report
