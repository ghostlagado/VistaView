"""Modo demonstração: fonte sintética, isolamento do warehouse e identificação na tela.

Estes testes existem para cumprir três regras do brief: o demo não pode contaminar
consultas reais, tem de funcionar sem a API externa de cotações e tem de ser
visualmente identificável.
"""

import re
from datetime import datetime
from pathlib import Path

import pytest

from app import create_app
from services import metricas, showcase
from utils.config import Settings
from utils.db import db


def _settings(**over):
    base = dict(
        host="127.0.0.1", port=8092, debug=False, secret="s",
        db_uri="sqlite:///:memory:", default_opt="GR", default_gr="Parana Interior",
    )
    base.update(over)
    return Settings(**base)


@pytest.fixture()
def sem_banco(monkeypatch):
    """Qualquer consulta ao warehouse vira falha de teste."""
    def proibido(*args, **kwargs):
        raise AssertionError("o modo demo não pode consultar o banco real")

    monkeypatch.setattr(db.session, "execute", proibido)


@pytest.fixture()
def demo(monkeypatch):
    monkeypatch.delenv("ACTION_API", raising=False)
    return create_app(_settings(demo=True))


# ------------------------------------------------------------------ configuração
def test_demo_dispensa_a_uri_do_banco():
    assert _settings(db_uri="", demo=True).validar() is None


def test_sem_demo_a_uri_continua_obrigatoria():
    with pytest.raises(RuntimeError, match="DB_URI"):
        _settings(db_uri="").validar()


def test_modo_demo_vem_do_ambiente(monkeypatch):
    monkeypatch.setenv("MODO_DEMO", "true")
    assert Settings.from_env().demo is True
    monkeypatch.setenv("MODO_DEMO", "false")
    assert Settings.from_env().demo is False


# ------------------------------------------------------------------ isolamento
def test_as_rotas_de_demo_nao_tocam_o_banco(demo, sem_banco):
    with demo.test_client() as cliente:
        assert cliente.get("/tarefas/total/GR/Parana Interior").status_code == 200
        assert cliente.get("/get_performance/GR/Parana Interior").status_code == 200
        assert cliente.get("/graph_days/GR/Parana Interior").status_code == 200


def test_sem_demo_as_mesmas_rotas_consultam_o_banco(app, capture_sql):
    """O espelho do teste acima: sem demo, a fonte real continua sendo o warehouse."""
    capture_sql["rows"] = [{"GERENTE": "x", "TOTAL": 1}]
    app.config["VISTA_FONTE"] = metricas
    with app.test_client() as cliente:
        cliente.get("/tarefas/total/GR/Parana Interior")
    assert "TAREFA" in capture_sql["sql"].upper()


def test_rota_invalida_continua_recusada_em_demo(demo):
    with demo.test_client() as cliente:
        resp = cliente.get("/tarefas/total/XX/gr")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Opção inválida"


def test_showcase_nao_importa_nada_de_dados_reais():
    fonte = Path("services/showcase.py").read_text(encoding="utf-8")
    for vedacao in ("utils.db", "db.session", "requests", "utils.actions", "brapi"):
        assert vedacao not in fonte, f"modo demo não pode depender de {vedacao}"


# ------------------------------------------------------------------ contrato
def test_payload_do_demo_tem_as_mesmas_chaves_do_real(app, capture_sql):
    agora = datetime(2026, 10, 20, 15, 30)
    with app.app_context():
        reais = set(metricas.painel("GR", "Parana Interior", agora))
    sinteticos = set(showcase.painel("GR", "Parana Interior", agora))
    assert sinteticos == reais


@pytest.mark.parametrize("rota,chave", [
    ("/top3_uni/", "uni"), ("/top3_sups/", "sup"), ("/get_gerentes/", "grs"),
    ("/get_unidades/", "uni"), ("/graph_days/", "dia"), ("/graph_days_ant/", "dia"),
])
def test_forma_de_cada_rota_preservada_em_demo(demo, rota, chave):
    with demo.test_client() as cliente:
        corpo = cliente.get(rota + "GR/Parana Interior").get_json()
    assert chave in corpo and "total" in corpo


def test_a_regra_de_meta_e_a_mesma_em_demo():
    agora = datetime(2026, 10, 20, 15, 30)
    p = showcase.painel("GR", "Parana Interior", agora, meta_percentual=15)
    assert p["metaMes"] == round(p["mesAnterior"] * 1.15)
    assert p["gapMes"] == p["totalMes"] - p["metaMes"]


def test_janeiro_referencia_dezembro_do_ano_anterior_em_demo():
    p = showcase.painel("GR", "Parana Interior", datetime(2027, 1, 5, 12, 0))
    assert p["metaMes"] >= 0
    assert p["diasAnt"]["dia"] == list(range(1, 6))


# ------------------------------------------------------------------ coerência
def test_os_mesmos_numeros_se_repetem_no_mesmo_instante():
    agora = datetime(2026, 10, 20, 15, 30)
    assert showcase.painel("GR", "Parana Interior", agora) == \
        showcase.painel("GR", "Parana Interior", agora)


def test_o_painel_anda_durante_o_dia():
    manha = showcase.painel("GR", "Parana Interior", datetime(2026, 10, 20, 8, 0))
    tarde = showcase.painel("GR", "Parana Interior", datetime(2026, 10, 20, 18, 0))
    assert tarde["totalDia"] > manha["totalDia"]
    assert tarde["totalMes"] >= manha["totalMes"]


def test_rankings_vem_ordenados_e_sem_duplicidade():
    p = showcase.painel("GR", "Parana Interior", datetime(2026, 10, 20, 15, 30))
    for bloco in (p["top3Uni"], p["top3Sup"], p["gerentes"], p["unidades"]):
        totais = bloco["total"]
        assert totais == sorted(totais, reverse=True)
    assert len(p["top3Uni"]["uni"]) == 3
    assert len(set(p["gerentes"]["grs"])) == len(p["gerentes"]["grs"])


def test_a_serie_do_dia_bate_com_a_consulta():
    agora = datetime(2026, 10, 20, 15, 30)
    p = showcase.painel("GR", "Parana Interior", agora)
    assert p["dias"]["dia"] == list(range(1, agora.day + 1))
    assert p["dias"]["total"][-1] == p["totalDia"]
    assert len(p["diasAnt"]["dia"]) == agora.day


# ------------------------------------------------------------------ cotações
def test_cotacoes_de_demo_vem_sem_qualquer_api():
    lista = showcase.cotacoes(datetime(2026, 10, 20, 15, 30))
    assert 1 <= len(lista) <= 5
    for c in lista:
        assert {"simbolo", "preco", "variacao", "atual", "cotizadoEm", "provedor"} <= set(c)
        assert c["provedor"] == "demo"
        assert isinstance(c["preco"], (int, float))


# ------------------------------------------------------------------ identificação
def test_o_painel_marca_demo_no_cabecalho(demo):
    html = demo.test_client().get("/").get_data(as_text=True)
    assert "selo--demo" in html
    assert re.search(r">\s*DEMO\s*<", html)


def test_o_painel_real_nao_marca_demo(app):
    html = app.test_client().get("/").get_data(as_text=True)
    assert "selo--demo" not in html


def test_o_ciclo_de_atualizacao_usa_a_fonte_do_demo(demo):
    atualizador = demo.extensions["vista_atualizador"]
    assert atualizador.nome_ciclo == "demo"
    assert demo.config["VISTA_FONTE"] is showcase
    assert demo.config["VISTA_COTACOES"] is showcase.cotacoes

    dados = atualizador.calcular(demo)
    assert {c["provedor"] for c in dados["cotacoes"]} == {"demo"}


def test_o_ciclo_real_nao_se_confunde_com_demo(app):
    assert app.extensions["vista_atualizador"].nome_ciclo == "painel"
