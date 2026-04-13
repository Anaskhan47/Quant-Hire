import io
from typing import Optional

from pypdf import PdfReader


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract raw text from an uploaded PDF.
    This is best-effort: scanned PDFs may return little/no text.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt.strip():
            parts.append(txt)
    return "\n".join(parts).strip()

