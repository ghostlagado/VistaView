"""Janela de referência das consultas (mês anterior / mês atual)."""

import datetime as real_dt

import pytest

import services.metricas as metricas


class FrozenDT:
    def __init__(self, moment):
        self._moment = moment

    def now(self):
        return self._moment


@pytest.fixture()
def freeze(monkeypatch, request):
    moment = request.param
    monkeypatch.setattr(metricas, "dt", FrozenDT(moment))
    return moment


@pytest.mark.parametrize(
    "freeze",
    [real_dt.datetime(2026, 1, 15, 12, 0)],
    indirect=True,
)
def test_em_janeiro_a_referencia_vira_dezembro_do_ano_anterior(client, freeze, capture_sql):
    client.get("/tarefas/mes/anterior/GR/gr")
    assert capture_sql["params"]["month"] == 12
    assert capture_sql["params"]["year"] == 2025

    client.get("/graph_days_ant/GR/gr")
    assert capture_sql["params"]["month"] == 12
    assert capture_sql["params"]["year"] == 2025
    assert capture_sql["params"]["day"] == 15


@pytest.mark.parametrize(
    "freeze",
    [real_dt.datetime(2026, 10, 20, 12, 0)],
    indirect=True,
)
def test_fora_de_janeiro_a_referencia_e_o_mes_anterior(client, freeze, capture_sql):
    client.get("/tarefas/mes/anterior/GR/gr")
    assert capture_sql["params"] == {"gr": "gr", "month": 9, "year": 2026}


@pytest.mark.parametrize(
    "freeze",
    [real_dt.datetime(2026, 10, 20, 12, 0)],
    indirect=True,
)
def test_indicadores_do_mes_usam_mes_e_ano_correntes(client, freeze, capture_sql):
    client.get("/tarefas/total/GR/gr")
    assert capture_sql["params"]["month"] == 10
    assert capture_sql["params"]["year"] == 2026
