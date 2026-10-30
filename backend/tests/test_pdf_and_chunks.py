from app.services.pdf_processor import extract_pdf_text
from app.services.text_chunker import build_chunks, split_text


def test_table_cells_keep_spaces_and_percent(sales_pdf):
    data = extract_pdf_text(sales_pdf)
    assert data["table_count"] == 4

    regions = next(t for t in data["tables"] if t["headers"][0] == "Region")
    assert regions["rows"][0][0] == "North"
    assert regions["rows"][0][3] == "33.7%"  # قبلاً «337% .» استخراج می‌شد

    monthly = next(t for t in data["tables"] if t["headers"][0] == "Month")
    assert monthly["rows"][0][0] == "January 2026"  # فاصله حفظ می‌شود
    assert monthly["rows"][0][1] == 3750000000


def test_tables_are_searchable_chunks(sales_pdf):
    data = extract_pdf_text(sales_pdf)
    chunks = build_chunks(data, source_id=7)

    assert any(c["kind"] == "table" for c in chunks)
    assert any("Region: North" in c["text"] for c in chunks)

    keys = {(c["page_number"], c["chunk_index"]) for c in chunks}
    assert len(keys) == len(chunks)  # شناسه‌ها یکتا هستند


def test_split_text_prefers_sentence_boundaries():
    text = ("این یک جمله است. " * 120).strip()
    pieces = split_text(text, chunk_size=300, overlap=40)
    assert len(pieces) > 1
    assert all(len(p) <= 300 for p in pieces)
    assert all(p.rstrip().endswith("است.") for p in pieces[:-1])
