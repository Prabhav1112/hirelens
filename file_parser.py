"""
Extracts plain text from uploaded resume / transcript / job description files.
Supports .pdf, .docx, .txt/.md, and falls back to best-effort decode for anything else.
"""

import io
from typing import Optional

from fastapi import UploadFile


def _parse_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _parse_docx(data: bytes) -> str:
    import docx

    document = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs)


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    lower = filename.lower()
    try:
        if lower.endswith(".pdf"):
            return _parse_pdf(data)
        if lower.endswith(".docx"):
            return _parse_docx(data)
        # txt, md, csv, or unknown -> best-effort decode
        return data.decode("utf-8", errors="ignore")
    except Exception as e:
        raise ValueError(f"Could not parse file '{filename}': {e}")


async def extract_text(file: Optional[UploadFile]) -> str:
    if file is None:
        return ""
    data = await file.read()
    if not data:
        return ""
    return extract_text_from_bytes(file.filename or "upload.txt", data)
