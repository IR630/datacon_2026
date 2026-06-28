"""Resolve open-access PDF links from DOI metadata.

Chain: Crossref -> Unpaywall -> OpenAlex -> Europe PMC (PMC full text). Each source
contributes candidate URLs; we download the first that is a real PDF.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from src.utils.io import ensure_dir


CROSSREF_WORKS = "https://api.crossref.org/works/{doi}"
UNPAYWALL = "https://api.unpaywall.org/v2/{doi}"
OPENALEX = "https://api.openalex.org/works/https://doi.org/{doi}"
EUROPEPMC_PDF = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextPDF"
EUROPEPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{doi}&format=json&resultType=core"
UNPAYWALL_EMAIL = "datacon2026@example.com"
HEADERS = {
    "User-Agent": "datacon_2026_selt_mvp/0.1 (mailto:datacon2026@example.com)",
    "Accept": "application/pdf,application/json,text/html;q=0.8,*/*;q=0.5",
}


def safe_pdf_name(name: str) -> str:
    cleaned = str(name).strip().lower().replace("\\", "_").replace("/", "_")
    return cleaned if cleaned.endswith(".pdf") else f"{cleaned}.pdf"


def _get_json(url: str, timeout: int = 25) -> dict[str, Any]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code >= 400:
            return {}
        return resp.json()
    except Exception:
        return {}


def crossref_work(doi: str, timeout: int = 20) -> dict[str, Any]:
    return _get_json(CROSSREF_WORKS.format(doi=quote(str(doi).strip(), safe="")), timeout).get("message", {})


def crossref_candidates(doi: str) -> list[str]:
    urls: list[str] = []
    for link in crossref_work(doi).get("link", []) or []:
        url = str(link.get("URL", "")).strip()
        content_type = str(link.get("content-type", "")).lower()
        lower = url.lower()
        if url and ("pdf" in content_type or lower.endswith(".pdf") or "/pdf" in lower or "download=1" in lower):
            urls.append(url)
    return urls


def unpaywall_candidates(doi: str) -> list[str]:
    url = UNPAYWALL.format(doi=quote(str(doi).strip(), safe="")) + f"?email={UNPAYWALL_EMAIL}"
    data = _get_json(url)
    urls: list[str] = []
    best = data.get("best_oa_location") or {}
    if best.get("url_for_pdf"):
        urls.append(best["url_for_pdf"])
    for loc in data.get("oa_locations") or []:
        if loc.get("url_for_pdf"):
            urls.append(loc["url_for_pdf"])
    return urls


def openalex_candidates(doi: str) -> list[str]:
    data = _get_json(OPENALEX.format(doi=quote(str(doi).strip(), safe="")))
    urls: list[str] = []
    for key in ("best_oa_location", "primary_location"):
        loc = data.get(key) or {}
        if loc.get("pdf_url"):
            urls.append(loc["pdf_url"])
    for loc in data.get("locations") or []:
        if loc.get("pdf_url"):
            urls.append(loc["pdf_url"])
    pmcid = (data.get("ids") or {}).get("pmcid")
    if pmcid:
        urls.append(EUROPEPMC_PDF.format(pmcid=str(pmcid).rstrip("/").rsplit("/", 1)[-1]))
    return urls


def europepmc_candidates(doi: str) -> list[str]:
    data = _get_json(EUROPEPMC_SEARCH.format(doi=quote(str(doi).strip(), safe="")))
    urls: list[str] = []
    for res in ((data.get("resultList") or {}).get("result") or []):
        pmcid = res.get("pmcid")
        if pmcid and (res.get("isOpenAccess") == "Y" or res.get("inEPMC") == "Y"):
            urls.append(EUROPEPMC_PDF.format(pmcid=pmcid))
    return urls


def _europepmc_from_pmc_ids(urls: list[str]) -> list[str]:
    out: list[str] = []
    for url in urls:
        match = re.search(r"PMC\d+", url)
        if match:
            out.append(EUROPEPMC_PDF.format(pmcid=match.group(0)))
    return out


def gather_candidates(doi: str) -> list[str]:
    urls: list[str] = []
    for source in (europepmc_candidates, unpaywall_candidates, openalex_candidates, crossref_candidates):
        try:
            urls.extend(source(doi))
        except Exception:
            continue
    # Europe PMC's fullTextPDF route is bot-friendly; try it first for any PMC id we saw.
    ordered = _europepmc_from_pmc_ids(urls) + urls
    return list(dict.fromkeys(u for u in ordered if u))


def looks_like_pdf(content: bytes, content_type: str = "") -> bool:
    if content.startswith(b"%PDF"):
        return True
    return "pdf" in content_type.lower() and len(content) > 1000


def download_pdf(url: str, out_path: str | Path, timeout: int = 45) -> bool:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    except Exception:
        return False
    if resp.status_code >= 400:
        return False
    if not looks_like_pdf(resp.content, resp.headers.get("content-type", "")):
        return False
    out = Path(out_path)
    ensure_dir(out.parent)
    out.write_bytes(resp.content)
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
    if not doi or str(doi).strip().lower() in {"nan", "not_detected", ""}:
        report["status"] = "no_doi"
        return report
    try:
        candidates = gather_candidates(str(doi))
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
