from __future__ import annotations

import io


def extract_text(filename: str, data: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf(data)
    if lower.endswith((".txt", ".md", ".csv")):
        return data.decode("utf-8", errors="ignore")
    # xlsx/images: OCR + vision extraction is a Phase 1 hardening item, not
    # built in this pass (see docs/PROJECT_PLAN.md §5). Degrade honestly
    # rather than pretending to parse something we don't.
    return f"[unparsed binary document: {filename}, {len(data)} bytes]"


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text or "[pdf parsed but contained no extractable text]"
    except Exception as exc:  # pragma: no cover - defensive, exercised by test_parsing.py
        return f"[failed to parse PDF: {exc}]"
