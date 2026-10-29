# Smart Reporting — Starter

Starter foundation for a PDF-based intelligent reporting app.

## Included

- FastAPI app and health endpoint
- Settings loaded from environment variables
- SQLite + SQLAlchemy models for data sources and report history
- Edrac chat-completion client
- Configurable embedding HTTP client
- Local persistent directories for uploads, processed files, and Chroma

## Setup

Use Python 3.11+.

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

Copy the root `.env.example` to `backend/.env`, then set `llm_api_key`.
Keep real keys out of Git.

Run from the `backend` directory:

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/api/v1/health`.

## Test the providers

The LLM client is in `app/services/llm_client.py`.
The embedding client is in `app/services/embedding_client.py`.

The embedding example supplied for this project only showed an `input` field. Confirm whether the endpoint requires an API key and/or `model` field before relying on it. If its response shape differs from OpenAI-compatible `data[0].embedding`, update the parser.

## Important

- Do not expose the embedding endpoint over plain HTTP to the public internet if sensitive data or credentials are sent.
- `create_all()` is fine for this starter; use Alembic migrations once the schema starts changing.
- PDF extraction, RAG, upload endpoints, source deletion, and report execution are not implemented yet.
