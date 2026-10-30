"""تقسیم محتوای استخراج‌شدهٔ PDF (متن + جدول) به قطعه‌های قابل جست‌وجو."""

import re

# اولویت نقطه‌های شکستن متن: پاراگراف، خط، پایان جمله، ویرگول، فاصله
_BREAKS = ("\n\n", "\n", "؟ ", "! ", ". ", "؛ ", "؛", "، ", " ")


def split_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[str]:
    """تقسیم متن به قطعه‌های هم‌پوشان؛ تا حد امکان در مرز جمله/پاراگراف می‌شکند."""
    text = text.strip()

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    chunks: list[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)

        if end < length:
            window_start = start + chunk_size // 2
            best = -1
            for marker in _BREAKS:
                position = text.rfind(marker, window_start, end)
                if position != -1:
                    best = position + len(marker)
                    break
            if best != -1:
                end = best

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= length:
            break

        next_start = max(end - overlap, start + 1)
        # اگر وسط یک کلمه افتادیم، تا اولین فاصله جلو برو
        if next_start < end and not text[next_start - 1].isspace():
            space = text.find(" ", next_start, end)
            if space != -1:
                next_start = space + 1
        start = next_start

    return chunks


def _cell_text(value) -> str:
    return "" if value is None else str(value)


def table_to_chunks(table: dict, max_chars: int = 1500) -> list[str]:
    """
    جدول را به متن «سرستون: مقدار» تبدیل می‌کند تا در پرسش‌وپاسخ قابل بازیابی باشد.
    جدول‌های بلند به چند قطعه تقسیم می‌شوند و در هر قطعه عنوان تکرار می‌شود.
    """
    headers = [str(h) for h in table.get("headers", [])]
    rows = table.get("rows", [])

    if not headers or not rows:
        return []

    title = f"جدول (صفحه {table.get('page_number')}) با ستون‌های: " + " | ".join(headers)

    chunks: list[str] = []
    current: list[str] = []
    size = len(title)

    for row in rows:
        parts = [
            f"{header}: {_cell_text(value)}"
            for header, value in zip(headers, row)
            if value is not None
        ]
        line = " | ".join(parts)
        if not line:
            continue

        if current and size + len(line) > max_chars:
            chunks.append(title + "\n" + "\n".join(current))
            current, size = [], len(title)

        current.append(line)
        size += len(line) + 1

    if current:
        chunks.append(title + "\n" + "\n".join(current))

    return chunks


def build_chunks(extracted: dict, source_id: int) -> list[dict]:
    """
    ساخت همهٔ قطعه‌های یک سند. chunk_index در هر صفحه یکتاست
    (قطعه‌های متنی اول، سپس قطعه‌های جدول همان صفحه).
    """
    chunks: list[dict] = []
    counters: dict[int, int] = {}

    def add(page_number: int, kind: str, text: str):
        counters[page_number] = counters.get(page_number, 0) + 1
        chunks.append(
            {
                "source_id": source_id,
                "page_number": page_number,
                "chunk_index": counters[page_number],
                "kind": kind,
                "text": text,
            }
        )

    for page in extracted.get("pages", []):
        for piece in split_text(page.get("text", "")):
            add(page["page_number"], "text", piece)

    for table in extracted.get("tables", []):
        for piece in table_to_chunks(table):
            add(table.get("page_number") or 1, "table", piece)

    return chunks
