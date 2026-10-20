"""Fonte sintética do modo demonstração.

Nada aqui toca o warehouse nem a API de cotações — é o que permite abrir o painel numa
TV sem VPN e sem chave de provedor. As assinaturas são as mesmas de `services.metricas`
para que as duas fontes sejam intercambiáveis, e `tests/test_demo.py` garante que o
payload tem as mesmas chaves e que nada aqui alcança o banco.

Os números são coerentes entre si e evoluem durante o dia: o total do mês é uma rampa
sobre o mês anterior, o total do dia acompanha a fração da jornada já passada, e os
rankings vêm de uma semente fixa por (recorte, dia) — a tela se mexe, mas um supervisor
não troca de posição de um ciclo para o outro sem motivo.
"""

import hashlib
import random
from calendar import monthrange
from datetime import datetime as dt

# A whitelist de recorte é regra de negócio, não dado: o demo usa exatamente a mesma.
from services.metricas import coluna_de_filtro  # noqa: F401  (reexportada de propósito)

UNIDADES = (
    "Londrina", "Maringá", "Curitiba", "Cascavel", "Ponta Porã", "Campo Mourão",
    "Apucarana", "Cornélio Procópio", "Umuarama", "Foz do Iguaçu", "Guarapuava",
    "Toledo",
)
SUPERVISORES = (
    "Tiago Moreira", "Aline Bassani", "Gustavo Ribeiro", "Denise Okada",
    "Anderson Prado", "Carla Meneghetti", "Rodrigo Alencar", "Juliana Ferraz",
)
GERENTES = (
    "Ana Paula Souza", "Carlos Eduardo Lima", "Marcos Vinicius Rocha",
    "Juliana Ferreira", "Rafael Antonio Nunes", "Beatriz Camargo",
    "Fernanda Prado", "Otávio Meneghetti", "Paulo Sergio Duarte",
)

# Símbolos de demonstração. A fase 7 define a lista real configurável (até cinco).
COTACOES_DEMO = (
    ("GGPS3", 42.0),
    ("PETR4", 38.0),
    ("VALE3", 61.0),
)

_INICIO_JORNADA = 7 * 60
_FIM_JORNADA = 19 * 60


def _rng(*chaves):
    identificador = "|".join(str(c) for c in chaves)
    semente = int(hashlib.sha256(identificador.encode()).hexdigest()[:16], 16)
    return random.Random(semente)


def _progresso_do_dia(agora):
    """Fração da jornada já passada, entre 0 e 1. É o que faz o painel andar."""
    minutos = agora.hour * 60 + agora.minute
    return min(1.0, max(0.0, (minutos - _INICIO_JORNADA) / (_FIM_JORNADA - _INICIO_JORNADA)))


def _mes_anterior_de(agora):
    mes, ano = agora.month - 1, agora.year
    if mes == 0:
        mes, ano = 12, ano - 1
    return mes, ano


# ======================================================================
# CIFRAS
# ======================================================================
def _base_mensal(gr, agora):
    """Total de referência do mês anterior: fixo durante todo o mês."""
    mes, ano = _mes_anterior_de(agora)
    return _rng(gr, "base", ano, mes).randint(900, 1800)


def tarefas_mes_anterior(campo, gr, agora=None):
    return _base_mensal(gr, agora or dt.now())


def tarefas_total(campo, gr, agora=None):
    agora = agora or dt.now()
    base = _base_mensal(gr, agora)
    dias_no_mes = monthrange(agora.year, agora.month)[1]
    esperado_ate_hoje = base * (agora.day - 1 + _progresso_do_dia(agora)) / dias_no_mes
    return int(round(esperado_ate_hoje * _rng(gr, "fator", agora.date()).uniform(0.92, 1.08)))


def tarefas_dia(campo, gr, agora=None):
    agora = agora or dt.now()
    alvo = _rng(gr, "dia", agora.date()).randint(35, 90)
    return int(round(alvo * _progresso_do_dia(agora)))


def visitas_mes(campo, gr, agora=None):
    agora = agora or dt.now()
    return int(round(tarefas_total(campo, gr, agora) * _rng(gr, "visita", agora.month).uniform(.14, .26)))


def visitas_dia(campo, gr, agora=None):
    agora = agora or dt.now()
    return int(round(_rng(gr, "visita_dia", agora.date()).randint(6, 26) * _progresso_do_dia(agora)))


def escalonadas(campo, gr):
    agora = dt.now()
    return _rng(gr, "escalonadas", agora.date()).randint(4, 34)


def performance(campo, gr, agora=None):
    agora = agora or dt.now()
    concluidas = tarefas_total(campo, gr, agora)
    fora = int(round(concluidas * _rng(gr, "fora", agora.month).uniform(.03, .09)))
    return {"st": ["FORA DO PRAZO", "NO PRAZO"], "total": [fora, max(concluidas - fora, 0)]}


# ======================================================================
# RANKINGS
# ======================================================================
def _ranking(gr, chave, nomes, agora, top=None):
    rnd = _rng(gr, chave, agora.strftime("%Y-%m"))
    valores = sorted(
        ((nome, rnd.randint(40, 400)) for nome in nomes),
        key=lambda par: par[1],
        reverse=True,
    )[:top]
    return {"uni": [n for n, _ in valores], "total": [v for _, v in valores]}


def unidades(campo, gr, agora=None):
    return _ranking(gr, "unidades", UNIDADES, agora or dt.now())


def top3_unidades(campo, gr, agora=None):
    return _ranking(gr, "unidades", UNIDADES, agora or dt.now(), top=3)


def top3_sups(campo, gr, agora=None):
    ranking = _ranking(gr, "sups", SUPERVISORES, agora or dt.now(), top=3)
    return {"sup": ranking["uni"], "total": ranking["total"]}


def gerentes(campo, gr, agora=None):
    agora = agora or dt.now()
    rnd = _rng(gr, "gerentes", agora.strftime("%Y-%m"))
    valores = sorted(
        ((nome, int(round(rnd.randint(60, 340) * (0.4 + 0.6 * _progresso_do_dia(agora)))))
         for nome in GERENTES),
        key=lambda par: par[1],
        reverse=True,
    )
    return {"grs": [n for n, _ in valores], "total": [v for _, v in valores]}


# ======================================================================
# SÉRIE DIÁRIA
# ======================================================================
def _serie(gr, campo, chave, agora, ate_dia, media, hoje=None):
    dias = list(range(1, ate_dia + 1))
    rnd = _rng(gr, chave, agora.strftime("%Y-%m"))
    totais = [max(int(round(rnd.gauss(media, media * 0.28))), 1) for _ in dias]
    if hoje is not None:
        totais[-1] = hoje
    return {"dia": dias, "total": totais}


def graph_days(campo, gr, agora=None):
    agora = agora or dt.now()
    media = _base_mensal(gr, agora) / 30
    return _serie(gr, campo, "dias", agora, agora.day, media,
                  hoje=tarefas_dia(campo, gr, agora))


def graph_days_ant(campo, gr, agora=None):
    agora = agora or dt.now()
    mes, ano = _mes_anterior_de(agora)
    ate = min(agora.day, monthrange(ano, mes)[1])
    return _serie(gr, campo, "dias_ant", agora, ate, _base_mensal(gr, agora) / 30)


# ======================================================================
# COTAÇÕES
# ======================================================================
def cotacoes(agora=None):
    """Série sintética com a mesma forma que a fase 7 vai receber do provedor."""
    agora = agora or dt.now()
    lista = []
    for simbolo, base in COTACOES_DEMO:
        rnd = _rng(simbolo, agora.strftime("%Y-%m-%d"), agora.hour)
        lista.append({
            "simbolo": simbolo,
            "preco": round(base * rnd.uniform(0.97, 1.03), 2),
            "variacao": round(rnd.uniform(-1.8, 2.4), 2),
            "atual": True,
            "indisponivel": False,
            "cotizadoEm": agora.strftime("%H:%M"),
            "provedor": "demo",
        })
    return lista


# ======================================================================
# AGREGADO
# ======================================================================
def painel(opt, gr, agora=None, meta_percentual=None):
    """Mesmo objeto devolvido por `services.metricas.painel`, com cotações sintéticas."""
    import sys

    from services.metricas import montar_painel

    dados = montar_painel(sys.modules[__name__], opt, gr, agora, meta_percentual)
    dados["cotacoes"] = cotacoes(agora or dt.now())
    return dados
