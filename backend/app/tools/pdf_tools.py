"""
PDF ingestion tool.

Two libraries, used for what each is actually good at:
  - PyMuPDF (`fitz`): very fast text and layout extraction, used for the bulk
    of the document body.
  - pdfplumber: slower but table-aware so used specifically to pull out
    tables (data-heavy papers/reports usually live or die on their tables,
    and PyMuPDF's plain text extraction mangles tabular layout).

`source` can be either an http(s) URL or a local filesystem path; URLs are
downloaded to a temp file that's cleaned up afterward.
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from dataclasses import dataclass, field

import fitz  # PyMuPDF
import httpx
import pdfplumber

logger = logging.getLogger("oracle.tools.pdf")


@dataclass
class PDFReadResult:
    source: str
    page_count: int
    full_text: str
    tables_markdown: list[str] = field(default_factory=list)
    truncated: bool = False
    error: str | None = None


@contextlib.contextmanager
def _local_pdf_path(source: str):
    if source.startswith("http://") or source.startswith("https://"):
        resp = httpx.get(source, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            tmp.write(resp.content)
            tmp.close()
            yield tmp.name
        finally:
            os.unlink(tmp.name)
    else:
        if not os.path.exists(source):
            raise FileNotFoundError(f"No such PDF file: {source}")
        yield source


def _table_to_markdown(table: list[list[str | None]]) -> str:
    if not table:
        return ""
    rows = [[cell if cell is not None else "" for cell in row] for row in table]
    header, *body = rows
    md = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]
    for row in body:
        md.append("| " + " | ".join(row) + " |")
    return "\n".join(md)


def read_pdf(
    source: str, max_pages: int = 30, max_chars: int = 20_000
) -> PDFReadResult:
    try:
        with _local_pdf_path(source) as path:
            text_chunks: list[str] = []
            page_count = 0
            with fitz.open(path) as doc:
                page_count = doc.page_count
                for i, page in enumerate(doc):
                    if i >= max_pages:
                        break
                    text_chunks.append(page.get_text())

            tables_markdown: list[str] = []
            with pdfplumber.open(path) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i >= max_pages:
                        break
                    for table in page.extract_tables() or []:
                        rendered = _table_to_markdown(table)
                        if rendered:
                            tables_markdown.append(rendered)

            full_text = "\n\n".join(text_chunks)
            truncated = len(full_text) > max_chars or page_count > max_pages
            if len(full_text) > max_chars:
                full_text = full_text[:max_chars]

            return PDFReadResult(
                source=source,
                page_count=page_count,
                full_text=full_text,
                tables_markdown=tables_markdown[:10],  # cap prompt size
                truncated=truncated,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read PDF %r: %s", source, exc)
        return PDFReadResult(source=source, page_count=0, full_text="", error=str(exc))


def format_for_prompt(result: PDFReadResult) -> str:
    if result.error:
        return f"(failed to read PDF: {result.error})"
    parts = [result.full_text]
    if result.tables_markdown:
        parts.append("\n\nExtracted tables:\n" + "\n\n".join(result.tables_markdown))
    if result.truncated:
        parts.append("\n\n[document truncated for length]")
    return "".join(parts)
