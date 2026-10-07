"""
document_extractor.py — text extraction for uploaded legal documents.

PDFs: PyMuPDF (pymupdf — note: the `fitz` import name is deprecated as of
this version and triggers a warning; using `import pymupdf` instead).
Images / scanned PDF pages: Tesseract OCR via pytesseract, used ONLY as a
fallback when a page has no extractable text layer — never forced on every
page (native text extraction is faster and more accurate when available).

If OCR isn't available in the environment, this does NOT silently produce
empty text and pretend it succeeded — it returns an explicit warning field
the caller must surface to the user (per Phase 5D spec: "return a clear
message that the document requires OCR rather than silently producing
empty text").
"""

import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pymupdf

logger = logging.getLogger("legal_ai.document_extractor")

try:
    import pytesseract
    from PIL import Image
    OCR_IMPORTS_AVAILABLE = True
except ImportError:
    OCR_IMPORTS_AVAILABLE = False


def _ocr_is_actually_usable() -> bool:
    """The Python packages importing successfully doesn't guarantee the
    underlying `tesseract` binary is installed — check for real rather than
    assuming, so a failure surfaces as a clear warning instead of an
    unhandled exception deep in extraction."""
    if not OCR_IMPORTS_AVAILABLE:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception as e:
        logger.warning("pytesseract/PIL import OK but tesseract binary check failed: %s", e)
        return False


OCR_USABLE = _ocr_is_actually_usable()

OCR_UNAVAILABLE_MESSAGE = (
    "One or more pages appear to be scanned/image-based with no extractable text "
    "layer, and OCR (Tesseract) is not available in this environment. These pages "
    "were left as empty text rather than silently producing an incomplete analysis — "
    "install Tesseract OCR and the pytesseract package to enable text extraction from "
    "scanned documents."
)


@dataclass
class PageText:
    page_number: int
    text: str
    used_ocr: bool = False


@dataclass
class ExtractionResult:
    pages: List[PageText]
    full_text: str
    any_page_used_ocr: bool
    ocr_warning: Optional[str] = None


def _ocr_image(pil_image) -> str:
    return pytesseract.image_to_string(pil_image).strip()


def extract_text_from_pdf(file_path: str) -> ExtractionResult:
    doc = pymupdf.open(file_path)
    pages: List[PageText] = []
    any_ocr = False
    saw_unocrable_page = False

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1
        text = page.get_text().strip()
        page_used_ocr = False  # tracks THIS page only — bugfix: previously
        # computed from OCR_USABLE + non-empty text, which wrongly marked
        # pages that had a native text layer (never touched OCR) as
        # used_ocr=True just because OCR happened to be available.

        if not text:
            # No text layer — likely a scanned image page.
            if OCR_USABLE:
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                pil_img = Image.open(io.BytesIO(img_bytes))
                text = _ocr_image(pil_img)
                page_used_ocr = True
                any_ocr = True
            else:
                saw_unocrable_page = True
                text = ""

        pages.append(PageText(page_number=page_number, text=text, used_ocr=page_used_ocr))

    doc.close()

    full_text = "\n\n".join(p.text for p in pages if p.text)
    warning = OCR_UNAVAILABLE_MESSAGE if saw_unocrable_page else None

    return ExtractionResult(pages=pages, full_text=full_text, any_page_used_ocr=any_ocr, ocr_warning=warning)


def extract_text_from_image(file_path: str) -> ExtractionResult:
    if not OCR_USABLE:
        return ExtractionResult(
            pages=[PageText(page_number=1, text="", used_ocr=False)],
            full_text="",
            any_page_used_ocr=False,
            ocr_warning=OCR_UNAVAILABLE_MESSAGE,
        )

    pil_img = Image.open(file_path)
    text = _ocr_image(pil_img)
    return ExtractionResult(
        pages=[PageText(page_number=1, text=text, used_ocr=True)],
        full_text=text,
        any_page_used_ocr=True,
    )


def extract_text(file_path: str, file_extension: str) -> ExtractionResult:
    ext = file_extension.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in (".png", ".jpg", ".jpeg"):
        return extract_text_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file extension for extraction: {ext}")
