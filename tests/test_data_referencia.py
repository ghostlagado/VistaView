"""Janela de referência das consultas (mês anterior / mês atual).

A regra é de calendário, não de banco: janeiro referencia dezembro do ano anterior, e o
gráfico do mês anterior corta no mesmo dia de hoje. Aqui isso é assinado nos valores
ligados à consulta, que é onde a janela existe antes de virar SQL.
"""

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


def valores_ligados(captura):
    """Os bind values da última consulta, em conjunto — nomes de coluna são gerados."""
    return set(captura["params"].values())


@pytest.mark.parametrize(
    "freeze",
    [real_dt.datetime(2026, 1, 15, 12, 0)],
    indirect=True,
)
def test_em_janeiro_a_referencia_vira_dezembro_do_ano_anterior(client, freeze, capture_sql):
    client.get("/tarefas/mes/anterior/GR/gr")
    assert {12, 2025} <= valores_ligados(capture_sql)

    client.get("/graph_days_ant/GR/gr")
    assert {12, 2025, 15} <= valores_ligados(capture_sql)
    # O corte no mesmo dia de hoje é o que torna as duas séries comparáveis.
    assert "<= 15" in capture_sql["sem_sintaxe"]


@pytest.mark.parametrize(
    "freeze",
    [real_dt.datetime(2026, 10, 20, 12, 0)],
    indirect=True,
)
def test_fora_de_janeiro_a_referencia_e_o_mes_anterior(client, freeze, capture_sql):
    client.get("/tarefas/mes/anterior/GR/gr")
    assert {9, 2026, "gr"} <= valores_ligados(capture_sql)


@pytest.mark.parametrize(
    "freeze",
    [real_dt.datetime(2026, 10, 20, 12, 0)],
    indirect=True,
)
def test_indicadores_do_mes_usam_mes_e_ano_correntes(client, freeze, capture_sql):
    client.get("/tarefas/total/GR/gr")
    assert {10, 2026} <= valores_ligados(capture_sql)
