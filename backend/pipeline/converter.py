import logging
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | {".pdf", ".docx"}


def is_supported_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def get_file_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return "image"
    elif ext == ".pdf":
        return "pdf"
    elif ext == ".docx":
        return "docx"
    return "unknown"


def pdf_to_images(
    pdf_path: str | Path,
    pages: list[int] | None = None,
    dpi: int = 300,
    temp_dir: str | None = None,
) -> list[Path]:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_dir = Path(temp_dir) if temp_dir else Path(tempfile.mkdtemp(prefix="ocr_pdf_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    image_paths = []

    page_indices = pages if pages is not None else list(range(total_pages))

    for page_idx in page_indices:
        if page_idx < 0 or page_idx >= total_pages:
            logger.warning(f"Page {page_idx + 1} out of range (1-{total_pages}), skipping")
            continue

        page = doc[page_idx]
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        image_path = output_dir / f"{pdf_path.stem}_page_{page_idx + 1:04d}.png"
        pix.save(str(image_path))
        image_paths.append(image_path)
        logger.debug(f"Rendered page {page_idx + 1}/{total_pages} -> {image_path}")

    doc.close()
    return image_paths


def get_pdf_page_count(pdf_path: str | Path) -> int:
    doc = fitz.open(str(pdf_path))
    count = len(doc)
    doc.close()
    return count


def _find_libreoffice() -> str | None:
    if platform.system() == "Windows":
        common_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for p in common_paths:
            if os.path.exists(p):
                return p
    return shutil.which("soffice") or shutil.which("libreoffice")


def _docx_to_pdf_comtypes(docx_path: Path, output_dir: Path) -> Path:
    import comtypes.client

    word = comtypes.client.CreateObject("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(docx_path.resolve()))
        pdf_path = output_dir / f"{docx_path.stem}.pdf"
        doc.SaveAs(str(pdf_path), FileFormat=17)  # 17 = wdFormatPDF
        doc.Close()
        return pdf_path
    finally:
        word.Quit()


def _docx_to_pdf_libreoffice(docx_path: Path, output_dir: Path, lo_path: str | None = None) -> Path:
    lo_bin = lo_path or _find_libreoffice()
    if lo_bin is None:
        raise RuntimeError(
            "LibreOffice not found. Install LibreOffice or set converter.libreoffice_path in config. "
            "On Windows, you can also install Microsoft Word for DOCX conversion."
        )

    result = subprocess.run(
        [lo_bin, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(docx_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")

    pdf_path = output_dir / f"{docx_path.stem}.pdf"
    if not pdf_path.exists():
        raise RuntimeError(f"Expected PDF output not found at {pdf_path}")
    return pdf_path


def docx_to_images(
    docx_path: str | Path,
    dpi: int = 300,
    method: str = "auto",
    libreoffice_path: str | None = None,
    temp_dir: str | None = None,
) -> list[Path]:
    docx_path = Path(docx_path)
    if not docx_path.exists():
        raise FileNotFoundError(f"DOCX not found: {docx_path}")

    work_dir = Path(temp_dir) if temp_dir else Path(tempfile.mkdtemp(prefix="ocr_docx_"))
    work_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = None

    if method == "auto":
        if platform.system() == "Windows":
            try:
                pdf_path = _docx_to_pdf_comtypes(docx_path, work_dir)
                logger.info("DOCX converted via Microsoft Word COM")
            except Exception as e:
                logger.info(f"COM conversion failed ({e}), trying LibreOffice")
                pdf_path = _docx_to_pdf_libreoffice(docx_path, work_dir, libreoffice_path)
        else:
            pdf_path = _docx_to_pdf_libreoffice(docx_path, work_dir, libreoffice_path)
    elif method == "comtypes":
        pdf_path = _docx_to_pdf_comtypes(docx_path, work_dir)
    elif method == "libreoffice":
        pdf_path = _docx_to_pdf_libreoffice(docx_path, work_dir, libreoffice_path)
    else:
        raise ValueError(f"Unknown DOCX conversion method: {method}")

    return pdf_to_images(pdf_path, dpi=dpi, temp_dir=str(work_dir))


def image_passthrough(image_path: str | Path, temp_dir: str | None = None) -> list[Path]:
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Validate the image is readable
    img = Image.open(str(image_path))
    img.verify()

    return [image_path]


def convert_to_images(
    file_path: str | Path,
    pages: list[int] | None = None,
    dpi: int = 300,
    docx_method: str = "auto",
    libreoffice_path: str | None = None,
    temp_dir: str | None = None,
) -> list[Path]:
    file_path = Path(file_path)
    file_type = get_file_type(file_path)

    if file_type == "image":
        return image_passthrough(file_path, temp_dir)
    elif file_type == "pdf":
        return pdf_to_images(file_path, pages=pages, dpi=dpi, temp_dir=temp_dir)
    elif file_type == "docx":
        return docx_to_images(
            file_path, dpi=dpi, method=docx_method,
            libreoffice_path=libreoffice_path, temp_dir=temp_dir,
        )
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")
