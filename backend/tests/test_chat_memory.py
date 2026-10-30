"""«بله» باید به پیشنهاد قبلیِ دستیار وصل شود."""

import pytest

from app.services import chat_service, llm_client


@pytest.fixture()
def fake_llm(monkeypatch):
    calls = {"embedded": [], "answer_messages": []}

    def fake_chat_completion(messages, **kwargs):
        system = messages[0]["content"]
        if system.strip().startswith("وظیفهٔ تو بازنویسی"):
            last = messages[-1]["content"]
            # شبیه‌سازی بازنویسی: «بله» → پیشنهاد دستیار
            if "آخرین پیام کاربر:\nبله" in last:
                return "نمودار روند فروش ماهانه را بساز", "stop"
            return "سؤال مستقل", "stop"
        calls["answer_messages"].append(messages)
        if len(calls["answer_messages"]) == 1:
            return "فروش رشد کرده است. آیا نمودار روند فروش ماهانه را هم بسازم؟", "stop"
        return "این هم نمودار روند فروش ماهانه.", "stop"

    def fake_embed(texts):
        calls["embedded"].extend(texts)
        return [[0.1, 0.2] for _ in texts]

    def fake_search(**kwargs):
        return [
            {
                "chunk_id": "c1",
                "text": "Month: January | Revenue: 100",
                "metadata": {"source_id": 1, "page_number": 1, "chunk_index": 1, "kind": "table"},
                "distance": 0.1,
            }
        ]

    monkeypatch.setattr(llm_client, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(chat_service, "embed_texts", fake_embed)
    monkeypatch.setattr(chat_service, "search_chunks", fake_search)
    return calls


def test_confirmation_uses_previous_offer(client, fake_llm):
    first = client.post("/api/v1/chat", json={"query": "وضعیت فروش چطور است؟"}).json()
    session_id = first["session_id"]
    assert "آیا نمودار" in first["answer"]

    second = client.post(
        "/api/v1/chat", json={"query": "بله", "session_id": session_id}
    ).json()

    # جست‌وجو با «بله» انجام نشده، با سؤال بازنویسی‌شده انجام شده است
    assert fake_llm["embedded"][-1] == "نمودار روند فروش ماهانه را بساز"
    assert second["standalone_query"] == "نمودار روند فروش ماهانه را بساز"

    # مدل تاریخچه را دیده است (سؤال اول و پاسخ دستیار با پیشنهادش)
    messages = fake_llm["answer_messages"][-1]
    roles = [m["role"] for m in messages]
    assert roles[:3] == ["system", "user", "assistant"]
    assert "آیا نمودار روند فروش ماهانه" in messages[2]["content"]

    history = client.get(f"/api/v1/chat/{session_id}").json()
    assert [m["role"] for m in history] == ["user", "assistant", "user", "assistant"]


def test_unknown_session_is_404(client, fake_llm):
    response = client.post("/api/v1/chat", json={"query": "سلام", "session_id": "nope"})
    assert response.status_code == 404
