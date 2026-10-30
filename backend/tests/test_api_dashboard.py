def test_upload_and_generate_dashboard_via_api(client, sales_pdf):
    with sales_pdf.open("rb") as f:
        resp = client.post("/api/v1/sources", files={"file": ("sales.pdf", f, "application/pdf")})
    assert resp.status_code == 201
    source_id = resp.json()["id"]

    # بدون اجرای دستی مرحلهٔ استخراج هم کار می‌کند
    resp = client.post(f"/api/v1/reports/{source_id}/dashboard", json={"use_llm": False})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert {c["type"] for c in body["components"]} >= {"kpi", "chart", "table"}

    saved = client.get(f"/api/v1/reports/{source_id}/dashboard")
    assert saved.status_code == 200
    assert saved.json()["title"] == body["title"]

    assert client.get("/api/v1/reports/9999/dashboard").status_code == 404

    assert client.delete(f"/api/v1/sources/{source_id}").status_code == 204
    assert client.get(f"/api/v1/reports/{source_id}/dashboard").status_code == 404
