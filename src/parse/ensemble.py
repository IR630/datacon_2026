"""Graceful PDF parsing ensemble.

The MVP relies on pypdf for text because it is lightweight. If PyMuPDF or
pdfplumber are installed, the parser automatically adds rendered pages and
tables/word-coordinate outputs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.utils.io import ensure_dir, write_json
from src.utils.logging import warn


CAPTION_RE = re.compile(
    r"(?P<caption>(?:Fig\.|Figure|Table)\s*\d+[\w\W]{0,700}?)(?=(?:Fig\.|Figure|Table)\s*\d+|$)",
    re.IGNORECASE,
)


def _clean_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\x00", "")).strip()


def _paragraph_chunks(text: str, page: int, pdf_name: str) -> list[dict[str, Any]]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not parts and text.strip():
        parts = [text.strip()]
    chunks: list[dict[str, Any]] = []
    for idx, part in enumerate(parts):
        chunks.append(
            {
                "id": f"{Path(pdf_name).stem}:p{page}:c{idx + 1}",
                "pdf": pdf_name,
                "page": page,
                "source_type": "text",
                "text": _clean_text(part),
                "bbox": None,
                "parser": "pypdf",
                "confidence": "medium",
            }
        )
    return chunks


def _extract_text_pypdf(pdf_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import pypdf

    reader = pypdf.PdfReader(str(pdf_path))
    pages = []
    chunks = []
    for i, page in enumerate(reader.pages, start=1):
        text = _clean_text(page.extract_text() or "")
        pages.append(
            {
                "pdf": pdf_path.name,
                "page": i,
                "text": text,
                "parser": "pypdf",
                "confidence": "medium" if text else "low",
            }
        )
        chunks.extend(_paragraph_chunks(text, i, pdf_path.name))
    return pages, chunks


def _extract_tables_pdfplumber(pdf_path: Path) -> list[dict[str, Any]]:
    try:
        import pdfplumber
    except Exception:
        warn("pdfplumber is not installed; table extraction skipped.")
        return []

    tables: list[dict[str, Any]] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                for table_index, table in enumerate(page.extract_tables() or [], start=1):
                    rows = [["" if cell is None else str(cell).strip() for cell in row] for row in table]
                    markdown = _table_to_markdown(rows)
                    if not markdown.strip():
                        continue
                    tables.append(
                        {
                            "id": f"{pdf_path.stem}:p{page_index}:t{table_index}",
                            "pdf": pdf_path.name,
                            "page": page_index,
                            "source_type": "table",
                            "text": markdown,
                            "rows": rows,
                            "bbox": None,
                            "parser": "pdfplumber",
                            "confidence": "medium",
                        }
                    )
    except Exception as exc:
        warn(f"pdfplumber failed: {exc}")
    return tables


def _table_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    header = padded[0]
    body = padded[1:]
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * width) + " |"]
    out.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(out)


def _render_pages_pymupdf(pdf_path: Path, page_images_dir: Path) -> list[dict[str, Any]]:
    try:
        import fitz
    except Exception:
        warn("PyMuPDF is not installed; page rendering skipped.")
        return []

    rendered: list[dict[str, Any]] = []
    try:
        doc = fitz.open(str(pdf_path))
        for index, page in enumerate(doc, start=1):
            out = page_images_dir / f"page_{index:03d}.png"
            pix = page.get_pixmap(dpi=160)
            pix.save(str(out))
            rendered.append(
                {
                    "pdf": pdf_path.name,
                    "page": index,
                    "source_type": "page_image",
                    "path": str(out),
                    "parser": "pymupdf",
                    "confidence": "high",
                }
            )
        doc.close()
    except Exception as exc:
        warn(f"PyMuPDF rendering failed: {exc}")
    return rendered


def _caption_candidates(pages: list[dict[str, Any]], pdf_name: str) -> list[dict[str, Any]]:
    figures: list[dict[str, Any]] = []
    for page in pages:
        for idx, match in enumerate(CAPTION_RE.finditer(page.get("text", "")), start=1):
            caption = _clean_text(match.group("caption"))
            figures.append(
                {
                    "id": f"{Path(pdf_name).stem}:p{page['page']}:caption{idx}",
                    "pdf": pdf_name,
                    "page": page["page"],
                    "source_type": "caption",
                    "text": caption,
                    "bbox": None,
                    "parser": "regex",
                    "confidence": "low",
                }
            )
    return figures


def parse_pdf(pdf_path: str | Path, parsed_root: str | Path = "data/parsed") -> dict[str, Path]:
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(pdf)

    out_dir = ensure_dir(Path(parsed_root) / pdf.stem)
    page_images_dir = ensure_dir(out_dir / "page_images")

    pages, chunks = _extract_text_pypdf(pdf)
    tables = _extract_tables_pdfplumber(pdf)
    figures = _caption_candidates(pages, pdf.name)
    rendered = _render_pages_pymupdf(pdf, page_images_dir)

    # Tables and captions should also be searchable evidence.
    chunks.extend(tables)
    chunks.extend(figures)

    outputs = {
        "pages": write_json(out_dir / "pages.json", pages),
        "tables": write_json(out_dir / "tables.json", tables),
        "chunks": write_json(out_dir / "chunks.json", chunks),
        "figures": write_json(out_dir / "figures.json", figures + rendered),
    }
    return outputs

