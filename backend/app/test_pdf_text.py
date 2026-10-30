import pymupdf

pdf_path = "../data/uploads/6eb44abb0f804006b0b9520c3f8b7757.pdf"

doc = pymupdf.open(pdf_path)

for page_number, page in enumerate(doc, start=1):
    print(f"\n{'=' * 30}")
    print(f"PAGE {page_number}")
    print("=" * 30)

    text = page.get_text("text")
    print(repr(text[:2000]))