import fitz  # PyMuPDF
from pathlib import Path


def extract_pdf_text(pdf_path: str | Path) -> dict:
    """
    استخراج متن PDF به‌صورت صفحه‌به‌صفحه.
    خروجی شامل تعداد صفحات و متن هر صفحه است.
    """
    path = Path(pdf_path)

    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    pages = []

    with fitz.open(path) as document:
        if document.is_encrypted:
            raise ValueError("PDF is encrypted and cannot be read.")

        for page_number, page in enumerate(document, start=1):
            pages.append({
                "page_number": page_number,
                "text": page.get_text("text").strip(),
            })

    return {
        "page_count": len(pages),
        "pages": pages,
    }