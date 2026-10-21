import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# app.py exige as variáveis de ambiente no momento do import; definir antes de importar.
os.environ.setdefault("DB_URI", "sqlite:///:memory:")
os.environ.setdefault("SECRET", "test-secret")
# O `.env` de quem está rodando não pode escolher o modo da suíte: o `app` compartilhado
# precisa nascer no caminho real, e o demo entra só onde o teste pede um app dele.
os.environ["MODO_DEMO"] = "false"

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


# `[Tarefa].[Status] = 85` e `"Tarefa"."Status" = 85` são a mesma asserção com sintaxe de
# dialeto diferente. Normalizar deixa os testes falarem do filtro, não das aspas.
RE_ASPAS = re.compile(r'[\[\]"`]')


def sem_sintaxe(texto):
    return re.sub(r"\s+", " ", RE_ASPAS.sub("", texto)).upper()


@pytest.fixture()
def app():
    _real_app.config["TESTING"] = True
    yield _real_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def capture_sql(app, monkeypatch):
    """Captura as consultas ORM executadas, compiladas para os dois bancos.

    Antes disto o fixture devolvia o texto do SQL montado pelas rotas. No ORM não existe
    texto montado: existe uma estrutura de consulta, e ela só vira SQL nas mãos de um
    dialeto. Por isso cada consulta capturada guarda quatro leituras da mesma coisa:

    - `sql` / `sqlite`: o SQL de cada banco com os **placeholders** de bind — é o que prova
      que valor nenhum entra por texto;
    - `com_valores` / `com_valores_sqlite`: o mesmo SQL com os valores ligados, para
      asserções legíveis de filtro (`Status = 85`);
    - `params`: os bind values, com as listas do `IN` achatadas;
    - `sem_sintaxe`: o SQL com valores e sem as aspas de dialeto, normalizado em maiúsculas.

    Os campos acima espelham a última consulta, que é o caso de uso da maioria dos testes;
    `consultas` tem a lista completa, na ordem de execução.
    """
    from sqlalchemy.dialects import mssql, sqlite

    def compilar(statement, dialect, literais):
        kwargs = {"compile_kwargs": {"literal_binds": True}} if literais else {}
        return str(statement.compile(dialect=dialect, **kwargs))

    def achatar(params):
        """`{'ChecklistId_1': ['a', 'b']}` → `{'ChecklistId_1': 'a', ...}` para assinar item a item."""
        achatado = {}
        for chave, valor in (params or {}).items():
            if isinstance(valor, (list, tuple, set)):
                achatado.update({f"{chave}[{i}]": item for i, item in enumerate(valor)})
            else:
                achatado[chave] = valor
        return achatado

    capturado = {
        "consultas": [], "rows": [], "scalar": 0,
        "sql": None, "sqlite": None, "params": None,
        "com_valores": None, "com_valores_sqlite": None, "sem_sintaxe": None,
    }

    def fake_execute(statement, *args, **kwargs):
        consulta = {
            "sql": compilar(statement, mssql.dialect(), False),
            "sqlite": compilar(statement, sqlite.dialect(), False),
            "com_valores": compilar(statement, mssql.dialect(), True),
            "com_valores_sqlite": compilar(statement, sqlite.dialect(), True),
            "params": achatar(statement.compile().params),
        }
        consulta["sem_sintaxe"] = sem_sintaxe(consulta["com_valores"])
        capturado["consultas"].append(consulta)
        for chave, valor in consulta.items():
            capturado[chave] = valor
        return FakeResult(rows=capturado["rows"], scalar=capturado["scalar"])

    monkeypatch.setattr(db.session, "execute", fake_execute)
    return capturado
