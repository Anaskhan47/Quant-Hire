import fitz
import logging
import io
from fastapi import HTTPException

log = logging.getLogger("backend.utils")

class TextExtractor:
    @staticmethod
    async def extract_from_pdf(content: bytes) -> str:
        """Parses PDF content into raw text using PyMuPDF."""
        try:
            pdf_doc = fitz.open(stream=content, filetype="pdf")
            text = ""
            for page in pdf_doc:
                text += page.get_text() + "\n"
            return text.strip()
        except Exception as e:
            log.error(f"Failed to parse PDF stream: {e}")
            raise HTTPException(status_code=422, detail="Invalid or corrupted PDF file.")

text_extractor = TextExtractor()
