from pathlib import Path
import pymupdf


def clean_cell(value) -> str:
    """
    پاک‌سازی اولیه محتوای سلول جدول.
    فاصله‌های اضافی و خطوط جدید را حذف می‌کند.
    """
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


import re


def normalize_value(value):
    """
    پاک‌سازی و تبدیل مقادیر عددی استخراج‌شده از PDF.
    """

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    # حذف خطوط جدید و فاصله‌های اضافی
    value = value.replace("\n", " ")
    value = value.strip()

    # حذف ویرگول‌های انتهایی و جداکننده‌های اضافی
    value = re.sub(r"[\s,]+$", "", value)

    # حذف ویرگول‌های جداکننده هزارگان
    numeric_value = value.replace(",", "").replace(" ", "")

    # تبدیل اعداد صحیح
    if re.fullmatch(r"-?\d+", numeric_value):
        return int(numeric_value)

    # تبدیل اعداد اعشاری
    if re.fullmatch(r"-?\d+\.\d+", numeric_value):
        return float(numeric_value)

    # اگر عدد نبود، متن را نگه دار
    return value


import re
import pymupdf
from pathlib import Path


def normalize_value(value):
    """
    پاک‌سازی مقدار استخراج‌شده از سلول PDF
    و تبدیل مقادیر عددی به int یا float.
    """

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    # یکسان‌سازی فاصله‌ها و خطوط جدید
    value = re.sub(r"\s+", " ", value)

    # حذف ویرگول‌ها و جداکننده‌های انتهایی
    value = re.sub(r"[\s,]+$", "", value)

    # حذف جداکننده‌های هزارگان
    numeric_value = value.replace(",", "").replace(" ", "")

    # عدد صحیح
    if re.fullmatch(r"-?\d+", numeric_value):
        return int(numeric_value)

    # عدد اعشاری
    if re.fullmatch(r"-?\d+\.\d+", numeric_value):
        return float(numeric_value)

    # در صورت متنی بودن، مقدار پاک‌سازی‌شده برگردد
    return value


def extract_pdf_text(pdf_path: str | Path) -> dict:
    """
    استخراج متن و جدول‌های PDF به‌صورت صفحه‌به‌صفحه.

    خروجی شامل:
        page_count: تعداد صفحات
        pages: متن صفحات
        tables: جدول‌های استخراج‌شده
        table_count: تعداد جدول‌ها
    """

    path = Path(pdf_path)

    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    pages = []
    all_tables = []

    with pymupdf.open(path) as document:

        if document.is_encrypted:
            raise ValueError("PDF is encrypted and cannot be read.")

        for page_number, page in enumerate(document, start=1):

            # --------------------------------
            # 1. استخراج متن صفحه
            # --------------------------------

            page_text = page.get_text("text").strip()

            pages.append(
                {
                    "page_number": page_number,
                    "text": page_text,
                }
            )

            # --------------------------------
            # 2. شناسایی جدول‌های صفحه
            # --------------------------------

            table_finder = page.find_tables()

            for table_index, table in enumerate(table_finder.tables, start=1):

                extracted_rows = table.extract()

                if not extracted_rows:
                    continue

                # --------------------------------
                # 3. تشخیص Header جدول
                # --------------------------------

                if table.header.external:

                    headers = [normalize_value(cell) for cell in table.header.names]

                    data_rows = extracted_rows

                else:

                    headers = [normalize_value(cell) for cell in extracted_rows[0]]

                    data_rows = extracted_rows[1:]

                # --------------------------------
                # 4. پاک‌سازی ردیف‌ها
                # --------------------------------

                rows = []

                for row in data_rows:

                    cleaned_row = [normalize_value(cell) for cell in row]

                    # حذف ردیف‌های کاملاً خالی
                    if any(cell is not None for cell in cleaned_row):
                        rows.append(cleaned_row)

                # --------------------------------
                # 5. ذخیره جدول
                # --------------------------------

                all_tables.append(
                    {
                        "page_number": page_number,
                        "table_index": table_index,
                        "header_external": table.header.external,
                        "headers": headers,
                        "rows": rows,
                    }
                )

    # --------------------------------
    # 6. خروجی نهایی
    # --------------------------------

    return {
        "page_count": len(pages),
        "pages": pages,
        "tables": all_tables,
        "table_count": len(all_tables),
    }


def split_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[str]:
    """
    تقسیم متن به قطعه‌های هم‌پوشان.
    """

    text = text.strip()

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    chunks = []
    start = 0

    while start < len(text):

        end = min(start + chunk_size, len(text))

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks
