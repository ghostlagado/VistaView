"""Regras de negócio e cálculo dos indicadores (baseline da Fase 1)."""

import pytest

from utils.config import CHECKLISTS_VISITAS, opts


def test_visitas_mes_devolve_um_escalar(client, capture_sql):
    capture_sql["scalar"] = 42
    resp = client.get("/visitas/mes/GR/Parana Interior")
    assert resp.status_code == 200
    assert resp.get_json() == 42


def test_top3_unidades_devolve_listas_paralelas(client, capture_sql):
    capture_sql["rows"] = [
        {"UNIDADE": "U1", "TOTAL": 10},
        {"UNIDADE": "U2", "TOTAL": 5},
    ]
    body = client.get("/top3_uni/GR/gr").get_json()
    assert body == {"uni": ["U1", "U2"], "total": [10, 5]}


def test_performance_zera_categorias_sem_linhas(client, capture_sql):
    capture_sql["rows"] = []
    body = client.get("/get_performance/GR/gr").get_json()
    assert body["st"] == ["FORA DO PRAZO", "NO PRAZO"]
    assert body["total"] == [0, 0]


def test_performance_soma_por_categoria(client, capture_sql):
    capture_sql["rows"] = [
        {"ST": "NO PRAZO", "TOTAL": 7},
        {"ST": "FORA DO PRAZO", "TOTAL": 3},
    ]
    body = client.get("/get_performance/GR/gr").get_json()
    assert dict(zip(body["st"], body["total"])) == {
        "NO PRAZO": 7,
        "FORA DO PRAZO": 3,
    }


def test_escalonadas_devolve_objeto_total(client, capture_sql):
    capture_sql["scalar"] = 4
    body = client.get("/tarefas/escalonadas/GR/gr").get_json()
    assert body == {"total": 4}


@pytest.mark.parametrize(
    "opt,campo",
    [("GER", "cr.Gerente"), ("GR", "cr.GerenteRegional"), ("DIR", "cr.DiretorRegional")],
)
def test_opt_sempre_resolve_para_coluna_da_whitelist(capture_sql, client, opt, campo):
    client.get(f"/tarefas/total/{opt}/gr")
    assert f"WHERE {campo} = :gr" in capture_sql["sql"]


def test_injecao_via_opt_nao_chega_ao_banco(capture_sql, client):
    resp = client.get("/tarefas/total/GR' OR 1=1--/gr")
    assert resp.status_code == 400
    assert capture_sql["sql"] is None


def test_parametros_de_checklist_sao_os_configurados(capture_sql, client):
    client.get("/visitas/mes/GR/gr")
    usados = sorted(
        v for k, v in capture_sql["params"].items() if k.startswith("checklist")
    )
    assert usados == sorted(CHECKLISTS_VISITAS)
    assert len(CHECKLISTS_VISITAS) == 5


def test_whitelist_de_opts_nao_muda_sem_necessidade():
    assert set(opts) == {"GER", "GR", "DIR"}
