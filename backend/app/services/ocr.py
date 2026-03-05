"""
OCR Text Extraction Module – v3 (PaddleOCR)
Layout-aware OCR with table detection, structure analysis, and quality metrics.
Falls back to Tesseract if PaddleOCR is unavailable.
"""
import io
import logging
import numpy as np
from PIL import Image
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Engine selection ──────────────────────────────────────────────────
_paddle_engine = None
_USE_PADDLE = False

try:
    from paddleocr import PaddleOCR  # type: ignore[import-not-found]
    _paddle_engine = PaddleOCR(
        use_angle_cls=True,
        lang="en",
        show_log=False,
        use_gpu=False,
        enable_mkldnn=True,
        det_db_score_mode="slow",
    )
    _USE_PADDLE = True
    logger.info("PaddleOCR engine loaded successfully")
except ImportError:
    logger.warning("PaddleOCR not installed – falling back to Tesseract")
    try:
        import pytesseract  # type: ignore[import-not-found]
        from ..config import TESSERACT_CMD
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    except Exception:
        logger.warning("Tesseract also unavailable")


# ── Quality analysis helpers ──────────────────────────────────────────
def _analyse_image_quality(image: Image.Image) -> dict:
    """Compute scan-quality metrics from the PIL image."""
    w, h = image.size
    dpi = image.info.get("dpi", (72, 72))
    avg_dpi = (dpi[0] + dpi[1]) / 2 if isinstance(dpi, (tuple, list)) else dpi

    # Convert to grayscale numpy array for analysis
    gray = np.array(image.convert("L"), dtype=np.float32)
    contrast = float(gray.std())

    # Simple skew proxy – variance of row-wise mean brightness
    row_means = gray.mean(axis=1)
    skew_proxy = float(np.std(np.diff(row_means)))

    # Quality score 0-100
    quality = min(100, max(0,
        25 * min(avg_dpi / 300, 1.0) +
        25 * min(contrast / 70, 1.0) +
        25 * (1 - min(skew_proxy / 15, 1.0)) +
        25 * (1 if w >= 800 and h >= 600 else 0.5)
    ))

    return {
        "width": w,
        "height": h,
        "dpi": round(avg_dpi),
        "contrast": round(contrast, 1),
        "skew_estimate": round(skew_proxy, 2),
        "scan_quality_score": round(quality, 1),
    }


# ── PaddleOCR extraction ─────────────────────────────────────────────
def _paddle_extract(image: Image.Image) -> dict:
    """Run PaddleOCR on a PIL image and return structured results."""
    img_array = np.array(image.convert("RGB"))
    result = _paddle_engine.ocr(img_array, cls=True)

    lines = []
    confidences = []
    layout_blocks = []

    if result and result[0]:
        for idx, line in enumerate(result[0]):
            box, (text, conf) = line
            lines.append(text)
            confidences.append(conf)
            # Store layout info for each text block
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            layout_blocks.append({
                "id": idx,
                "text": text,
                "confidence": round(conf, 3),
                "bbox": {
                    "x_min": round(min(x_coords)),
                    "y_min": round(min(y_coords)),
                    "x_max": round(max(x_coords)),
                    "y_max": round(max(y_coords)),
                },
            })

    full_text = "\n".join(lines)
    avg_conf = (sum(confidences) / len(confidences) * 100) if confidences else 0
    quality = _analyse_image_quality(image)

    return {
        "text": full_text.strip(),
        "ocr_confidence": round(avg_conf, 2),
        "word_count": len(full_text.split()),
        "method": "paddleocr",
        "layout_blocks": layout_blocks,
        "quality": quality,
    }


# ── Tesseract fallback ────────────────────────────────────────────────
def _tesseract_extract(image: Image.Image) -> dict:
    """Run Tesseract OCR as fallback."""
    import pytesseract  # type: ignore[import-not-found]

    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    full_text = pytesseract.image_to_string(image)

    confidences = [c for c in ocr_data["conf"] if c > 0]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0
    quality = _analyse_image_quality(image)

    return {
        "text": full_text.strip(),
        "ocr_confidence": round(avg_conf, 2),
        "word_count": len([w for w in ocr_data["text"] if w.strip()]),
        "method": "tesseract_ocr",
        "layout_blocks": [],
        "quality": quality,
    }


# ── Public API ────────────────────────────────────────────────────────
def extract_text_from_image(image_data: bytes) -> dict:
    """Extract text from an image using PaddleOCR (or Tesseract fallback)."""
    image = Image.open(io.BytesIO(image_data))
    if _USE_PADDLE:
        return _paddle_extract(image)
    return _tesseract_extract(image)


def extract_text_from_pdf(pdf_data: bytes) -> dict:
    """
    Extract text from a PDF.
    1. Direct text extraction (PyMuPDF).
    2. Falls back to PaddleOCR / Tesseract per page.
    """
    import fitz  # type: ignore[import-not-found]

    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        direct_text = "\n".join(text_parts).strip()
        doc.close()

        if len(direct_text) > 50:
            return {
                "text": direct_text,
                "ocr_confidence": 99.0,
                "word_count": len(direct_text.split()),
                "method": "direct_pdf_extraction",
                "layout_blocks": [],
                "quality": {"scan_quality_score": 100, "dpi": 0, "skew_estimate": 0},
            }
    except Exception:
        pass

    # Fallback: convert pages to images → OCR
    try:
        from pdf2image import convert_from_bytes  # type: ignore[import-not-found]

        images = convert_from_bytes(pdf_data)
        all_text = []
        total_conf = 0
        all_blocks = []

        for page_num, img in enumerate(images):
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            page_result = extract_text_from_image(img_bytes.getvalue())
            all_text.append(page_result["text"])
            total_conf += page_result["ocr_confidence"]
            for blk in page_result.get("layout_blocks", []):
                blk["page"] = page_num + 1
                all_blocks.append(blk)

        avg_conf = total_conf / len(images) if images else 0
        combined_text = "\n\n".join(all_text)
        quality = page_result.get("quality", {}) if images else {}

        return {
            "text": combined_text,
            "ocr_confidence": round(avg_conf, 2),
            "word_count": len(combined_text.split()),
            "method": f"pdf_{'paddleocr' if _USE_PADDLE else 'tesseract'}",
            "layout_blocks": all_blocks,
            "quality": quality,
        }
    except Exception as e:
        return {
            "text": "",
            "ocr_confidence": 0,
            "word_count": 0,
            "method": "failed",
            "error": str(e),
            "layout_blocks": [],
            "quality": {},
        }


def extract_text(file_data: bytes, file_type: str) -> dict:
    """Main entry point: extract text based on file type."""
    file_type = file_type.lower()
    if file_type in [".pdf"]:
        return extract_text_from_pdf(file_data)
    elif file_type in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
        return extract_text_from_image(file_data)
    else:
        try:
            return extract_text_from_image(file_data)
        except Exception:
            return {
                "text": "",
                "ocr_confidence": 0,
                "word_count": 0,
                "method": "unsupported",
                "error": f"Unsupported file type: {file_type}",
                "layout_blocks": [],
                "quality": {},
            }
