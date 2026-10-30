from services.pageindex_service import (
    create_pageindex_client,
    get_source_doc_id,
)

doc_id = get_source_doc_id(1)

client = create_pageindex_client()

pages = client.get_page_content(doc_id, "2")

for page in pages:
    print(f"\n--- PAGE {page['page_index']} ---")
    print(page["markdown"])