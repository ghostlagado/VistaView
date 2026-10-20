import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# app.py exige DB_URI no momento do import; definir antes de importar.
os.environ.setdefault("DB_URI", "sqlite:///:memory:")
os.environ.setdefault("SECRET", "test-secret")

import pytest  # noqa: E402

from app import app as _real_app  # noqa: E402
from utils.db import db  # noqa: E402


class FakeResult:
    """Resultado mínimo de SQLAlchemy para os contratos usados pelas rotas."""

    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self):
        outer = self

        class _Mappings:
            def all(self):
                return outer._rows

        return _Mappings()

    def scalar(self):
        return self._scalar


@pytest.fixture()
def app():
    _real_app.config["TESTING"] = True
    yield _real_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def capture_sql(app, monkeypatch):
    """Captura o SQL e os parâmetros executados, devolvendo um resultado configurável."""
    captured = {"sql": None, "params": None, "rows": [], "scalar": 0}

    def fake_execute(statement, params=None, *args, **kwargs):
        captured["sql"] = str(statement)
        captured["params"] = params
        return FakeResult(rows=captured["rows"], scalar=captured["scalar"])

    monkeypatch.setattr(db.session, "execute", fake_execute)
    return captured
