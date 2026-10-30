import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# تنظیمات باید پیش از import شدن app تعیین شوند تا تست‌ها به داده‌ی واقعی دست نزنند.
_TMP = Path(tempfile.mkdtemp(prefix="smart_reporting_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["PROCESSED_DIR"] = str(_TMP / "processed")
os.environ["CHROMA_DIR"] = str(_TMP / "chroma")
os.environ["PAGEINDEX_DIR"] = str(_TMP / "pageindex")
os.environ["LLM_API_KEY"] = "test-key"

import pytest  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


@pytest.fixture(scope="session")
def sales_pdf() -> Path:
    return FIXTURES / "sales_sample.pdf"


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
