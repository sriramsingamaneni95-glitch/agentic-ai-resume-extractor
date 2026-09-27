
from utils.logging_config import logger

MIN_CHARS_PER_PAGE_BEFORE_OCR = 20


def parse_pdf(path: str, allow_ocr: bool = True) -> str:
    try:
        import fitz 
    except ImportError:
        raise ImportError("Run: pip install pymupdf")

    text_parts = []
    ocr_used = False

    with fitz.open(path) as doc:
        for page_num, page in enumerate(doc):
            page_text = page.get_text().strip()

            if len(page_text) < MIN_CHARS_PER_PAGE_BEFORE_OCR:
                if allow_ocr:
                    ocr_text = _ocr_page(page)
                    if ocr_text:
                        page_text = ocr_text
                        ocr_used = True
                else:
                    logger.warning(
                        f"Page {page_num + 1} has almost no extractable text and OCR is disabled."
                    )

            text_parts.append(page_text)

    if ocr_used:
        logger.info(f"OCR fallback was used for '{path}' (scanned/image-based page(s) detected).")

    return "\n".join(text_parts).strip()


def _ocr_page(page) -> str:
    try:
        import pytesseract
        from PIL import Image
        import io
    except ImportError:
        logger.warning(
           
        )
        return ""

    try:
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img).strip()
    except Exception as e:
        logger.warning(f"OCR failed for a page: {e}")
        return ""
