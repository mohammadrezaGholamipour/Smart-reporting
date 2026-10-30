
from services.pdf_processor import extract_pdf_text
from pprint import pprint

pdf_path = "../data/sample_sales_report_for_rag.pdf"

result = extract_pdf_text(pdf_path)

print("Page count:", result["page_count"])
print("Table count:", result["table_count"])

for table in result["tables"]:
    print("\nPage:", table["page_number"])
    print("Headers:", table["headers"])
    pprint(table["rows"])
