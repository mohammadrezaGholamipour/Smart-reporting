from app.services import vector_store as vs
from app.services.pdf_processor import extract_pdf_text
from app.services.text_chunker import build_chunks


def test_store_search_delete_roundtrip(sales_pdf):
    chunks = build_chunks(extract_pdf_text(sales_pdf), source_id=11)

    # embedding ساختگی: هر قطعه یک بردار متفاوت
    embeddings = [[1.0, float(i + 1), 0.5] for i in range(len(chunks))]
    assert vs.store_chunks(11, chunks, embeddings) == len(chunks)

    results = vs.search_chunks([1.0, 1.0, 0.5], source_id=11, top_k=3)
    assert len(results) == 3
    assert {"kind", "page_number", "chunk_index"} <= set(results[0]["metadata"])

    # سندی که وجود ندارد → خطا نمی‌دهد، لیست خالی برمی‌گرداند
    assert vs.search_chunks([1.0, 1.0, 0.5], source_id=999, top_k=3) == []

    # ذخیرهٔ دوباره، داده‌ی کهنه را جایگزین می‌کند (تکرار نمی‌شود)
    vs.store_chunks(11, chunks, embeddings)
    assert len(vs.search_chunks([1.0, 1.0, 0.5], source_id=11, top_k=10)) == min(10, len(chunks))

    vs.delete_source_chunks(11)
    assert vs.search_chunks([1.0, 1.0, 0.5], source_id=11, top_k=3) == []
