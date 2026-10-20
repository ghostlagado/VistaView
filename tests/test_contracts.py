"""Contratos de rota entre o front-end (static/js) e o back-end (routes/).

Estes testes existem porque, na auditoria inicial, 7 de 12 chamadas `fetch` do
front-end apontavam para URLs que não existiam no back-end.
"""

import re
from pathlib import Path

import pytest

JS_FILES = ["static/js/base.js", "static/js/chart.js"]
FETCH_RE = re.compile(r"fetch\(\s*[`'\"]([^`'\"]+)[`'\"]")


def frontend_paths(app_root):
    paths = set()
    for rel in JS_FILES:
        source = (app_root / rel).read_text(encoding="utf-8")
        for raw in FETCH_RE.findall(source):
            paths.add(re.sub(r"\$\{[^}]+\}", "PLACEHOLDER", raw))
    return paths


@pytest.fixture()
def app_root():
    return Path(__file__).resolve().parents[1]


def test_toda_chamada_fetch_existe_no_back_end(app, app_root):
    resolver = app.url_map.bind("localhost")
    missing = []
    for path in sorted(frontend_paths(app_root)):
        try:
            resolver.match(path)
        except Exception:
            missing.append(path)
    assert not missing, f"fetch() do front-end sem rota no back-end: {missing}"


def test_pagina_principal_renderiza_com_regional(app, client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "sessionStorage.setItem('GR'" in html
    assert "sessionStorage.setItem('OPT'" in html


def test_pagina_de_demonstracao_renderiza(app, client):
    assert client.get("/showcase").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/top3_sups/XX/gr",
        "/top3_uni/XX/gr",
        "/get_unidades/XX/gr",
        "/graph_days/XX/gr",
        "/graph_days_ant/XX/gr",
        "/get_performance/XX/gr",
        "/get_gerentes/XX/gr",
        "/visitas/mes/XX/gr",
        "/visitas/dia/XX/gr",
        "/tarefas/escalonadas/XX/gr",
        "/tarefas/total/XX/gr",
        "/tarefas/mes/anterior/XX/gr",
        "/tarefas/dia/XX/gr",
    ],
)
def test_opt_invalido_e_recusado(client, path):
    resp = client.get(path)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Opção inválida"
