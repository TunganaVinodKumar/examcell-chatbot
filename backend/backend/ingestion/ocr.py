import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

# Detect whether the installed `ocrmypdf` package can be imported.
# On some Windows setups a mismatched `pikepdf` causes `ocrmypdf`
# to raise an ImportError. If import fails we avoid invoking it.
try:
    import ocrmypdf as _ocrmypdf  # noqa: F401
    OCRMYPDF_IMPORT_OK = True
    _ocrmypdf_import_error = None
except Exception as _e:
    OCRMYPDF_IMPORT_OK = False
    _ocrmypdf_import_error = _e


def copy_without_ocr(input_pdf: Path, output_pdf: Path, reason: str) -> bool:
    """
    Fallback copy when OCR cannot run.
    Returns False because OCR did not actually execute.
    """
    try:
        if input_pdf.resolve() != output_pdf.resolve():
            output_pdf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(input_pdf), str(output_pdf))
            print(f"Warning: {reason}; copied original to processed (OCR skipped).")
        else:
            print(f"Warning: {reason} and input == output; skipping copy.")
    except Exception as copy_error:
        print(f"Warning: fallback copy also failed: {copy_error}")
    return False


def apply_ocr(input_pdf: Path, output_pdf: Path, dpi: int = 300) -> bool:
    """
    Apply OCR using ocrmypdf.

    Returns True if OCR completed successfully and produced/updated output_pdf.
    Returns False if OCR could not be performed and a fallback copy was made
    or copying was skipped because input == output.
    """
    cmd = [
        "ocrmypdf",
        "--force-ocr",
        "--optimize", "1",
        "--deskew",
        "--rotate-pages",
        "--rotate-pages-threshold", "10",
        "--jobs", str(os.cpu_count() or 1),
        "--oversample", str(dpi),
        "--output-type", "pdf",
        str(input_pdf),
        str(output_pdf),
    ]

    if not OCRMYPDF_IMPORT_OK:
        return copy_without_ocr(
            input_pdf,
            output_pdf,
            f"ocrmypdf package import failed: {_ocrmypdf_import_error}",
        )

    try:
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(cmd, check=True)
        return True

    except FileNotFoundError:
        return copy_without_ocr(input_pdf, output_pdf, "ocrmypdf not found on PATH")

    except subprocess.CalledProcessError as e:
        return copy_without_ocr(input_pdf, output_pdf, f"ocrmypdf failed ({e})")

    except Exception as e:
        return copy_without_ocr(input_pdf, output_pdf, f"unexpected OCR error ({e})")


def ocr_pdf_to_text_tesseract(pdf_path: Path, dpi: int = 300) -> Optional[str]:
    try:
        import fitz  # PyMuPDF
        import pytesseract
        import cv2
        import numpy as np
        from PIL import Image

        doc = fitz.open(str(pdf_path))
        full_text = []

        for page_index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=dpi)
            mode = "RGB" if pix.n < 4 else "RGBA"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)

            img_np = np.array(img)

            if mode == "RGBA":
                img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
            else:
                img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

            h, w = img_cv.shape[:2]

            header_crop = img_cv[0:int(0.35 * h), 0:w]
            header_gray = cv2.cvtColor(header_crop, cv2.COLOR_BGR2GRAY)
            header_gray = cv2.GaussianBlur(header_gray, (5, 5), 0)
            header_gray = cv2.adaptiveThreshold(
                header_gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                2,
            )

            header_text = pytesseract.image_to_string(
                header_gray,
                config="--oem 3 --psm 6 -l eng",
            )

            body_crop = img_cv[int(0.30 * h):h, 0:w]
            body_gray = cv2.cvtColor(body_crop, cv2.COLOR_BGR2GRAY)
            body_gray = cv2.GaussianBlur(body_gray, (3, 3), 0)
            body_gray = cv2.adaptiveThreshold(
                body_gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                2,
            )

            body_text = pytesseract.image_to_string(
                body_gray,
                config="--oem 3 --psm 6 -l eng",
            )

            page_text = f"[PAGE {page_index}]\n{header_text}\n{body_text}".strip()
            full_text.append(page_text)

        doc.close()
        return "\n\n".join(full_text).strip()

    except Exception as e:
        print(f"Warning: OCR via Tesseract failed: {e}")
        return None
