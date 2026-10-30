import re
from pathlib import Path

import pymupdf

from app.services.text_utils import parse_number


def clean_text(value) -> str:
    """فاصله‌ها و خطوط اضافی را یکسان می‌کند (فاصلهٔ بین کلمه‌ها حفظ می‌شود)."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_value(value):
    """
    پاک‌سازی مقدار سلول جدول و تبدیل اعداد (انگلیسی/فارسی) به int یا float.

    - مقدارهایی مثل «80%» یا «۱۲٪» به‌صورت متن می‌مانند تا معنای درصد از بین نرود.
    - کدها/شماره‌های بلند یا با صفر ابتدایی (تلفن، کد ملی، ...) عدد نمی‌شوند.
    """
    text = clean_text(value)
    if not text:
        return None

    text = re.sub(r"[\s,]+$", "", text)
    number = parse_number(text, allow_percent=False)

    if number is None:
        return text

    digits_only = re.sub(r"\D", "", text)
    if len(digits_only) > 15:
        return text
    if re.match(r"^[+-]?0\d", re.sub(r"[,\s]", "", text)) and "." not in text:
        return text

    return number


def _unique_headers(raw_headers: list) -> list[str]:
    """نام ستون‌ها را رشته، غیرخالی و یکتا می‌کند."""
    headers: list[str] = []
    seen: dict[str, int] = {}

    for index, raw in enumerate(raw_headers, start=1):
        name = clean_text(raw) or f"col_{index}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        headers.append(name)

    return headers


def _rows_by_clip(page, table) -> list[list[str | None]] | None:
    """
    متن هر سلول را با برش (clip) همان ناحیه از صفحه می‌خواند.

    table.extract() در بعضی PDFها فاصلهٔ بین کلمه‌ها را حذف می‌کند و جداکنندهٔ
    هزارگان یا ممیز اعشار را جابه‌جا می‌کند (مثلاً «33.7%» را «337% .» می‌دهد)؛
    خواندن با clip این مشکل را ندارد.
    """
    try:
        table_rows = table.rows
    except Exception:
        return None

    result: list[list[str | None]] = []

    for row in table_rows:
        cells = []
        for cell in row.cells:
            if cell is None:
                cells.append(None)
                continue
            text = page.get_text("text", clip=pymupdf.Rect(cell))
            cells.append(text.strip() or None)
        result.append(cells)

    if not result or not any(cell for row in result for cell in row):
        return None

    return result


def _extract_tables(page, page_number: int) -> list[dict]:
    tables = []

    try:
        finder = page.find_tables()
    except Exception:
        # یک صفحهٔ مشکل‌دار نباید کل استخراج را متوقف کند.
        return tables

    for table_index, table in enumerate(finder.tables, start=1):
        try:
            extracted_rows = _rows_by_clip(page, table) or table.extract()
        except Exception:
            continue

        if not extracted_rows or len(extracted_rows) < 2:
            continue

        try:
            header_external = bool(table.header.external)
        except Exception:
            header_external = False

        if header_external:
            headers = _unique_headers(list(table.header.names))
            data_rows = extracted_rows
        else:
            headers = _unique_headers(extracted_rows[0])
            data_rows = extracted_rows[1:]

        if len(headers) < 2:
            continue

        rows = []
        for row in data_rows:
            cleaned = [normalize_value(cell) for cell in row]
            # هم‌طول‌کردن ردیف با سرستون‌ها
            cleaned = (cleaned + [None] * len(headers))[: len(headers)]
            if any(cell is not None for cell in cleaned):
                rows.append(cleaned)

        if not rows:
            continue

        tables.append(
            {
                "page_number": page_number,
                "table_index": table_index,
                "header_external": header_external,
                "headers": headers,
                "rows": rows,
            }
        )

    return tables


def extract_pdf_text(pdf_path: str | Path) -> dict:
    """
    استخراج متن و جدول‌های PDF صفحه‌به‌صفحه.

    خروجی: page_count, pages, tables, table_count, warnings
    """
    path = Path(pdf_path)

    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    pages = []
    all_tables = []
    warnings: list[str] = []

    with pymupdf.open(path) as document:
        if document.is_encrypted:
            raise ValueError("PDF is encrypted and cannot be read.")

        for page_number, page in enumerate(document, start=1):
            pages.append(
                {
                    "page_number": page_number,
                    "text": page.get_text("text").strip(),
                }
            )
            all_tables.extend(_extract_tables(page, page_number))

    total_chars = sum(len(p["text"]) for p in pages)

    if total_chars == 0 and not all_tables:
        raise ValueError(
            "هیچ متنی در این PDF پیدا نشد؛ احتمالاً اسکن/تصویری است و "
            "OCR در این نسخه پشتیبانی نمی‌شود."
        )

    if pages and total_chars / len(pages) < 30:
        warnings.append(
            "حجم متن استخراج‌شده بسیار کم است؛ ممکن است بخشی از PDF تصویری باشد."
        )

    return {
        "page_count": len(pages),
        "pages": pages,
        "tables": all_tables,
        "table_count": len(all_tables),
        "warnings": warnings,
    }
