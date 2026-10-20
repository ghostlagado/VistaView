"""Regras e cálculos dos indicadores do GPS Vista.

As consultas e as regras de negócio moravam dentro de `routes/`. Aqui elas ficam sem
qualquer dependência de Flask, para que a camada HTTP (rotas) e a camada de atualização
em tempo real consumam exatamente o mesmo cálculo.

O SQL é o original da auditoria, preservado literalmente — inclusive os hints `NOLOCK`,
que variavam de rota para rota.
"""

from calendar import monthrange
from datetime import datetime as dt

from sqlalchemy import text

from utils.config import CHECKLISTS_VISITAS, SETTINGS, opts
from utils.db import db

_STATUS_CONCLUIDA = 85
_STATUS_ABERTAS = (25, 10, 70)


def coluna_de_filtro(opt):
    """Whitelist do recorte. Retorna None para um `opt` fora da whitelist."""
    return opts.get(opt)


def _checklist_params():
    return {f"checklist{i+1}": c for i, c in enumerate(CHECKLISTS_VISITAS)}


def _janela_mes_agora(agora=None):
    agora = agora or dt.now()
    return {"month": agora.month, "year": agora.year}


def _janela_mes_anterior(agora=None):
    """Mês anterior com a virada de ano: janeiro referencia dezembro do ano passado."""
    agora = agora or dt.now()
    mes = agora.month - 1
    ano = agora.year
    if mes == 0:
        mes, ano = 12, ano - 1
    return {"month": mes, "year": ano}


# ======================================================================
# VISITAS
# ======================================================================
def visitas_mes(campo, gr, agora=None):
    sql = text(f"""
        SELECT COUNT(T.NOME) AS TOTAL
        FROM Tarefa T WITH(NOLOCK)
        INNER JOIN dw_vista.dbo.DM_ESTRUTURA Es WITH(NOLOCK)
            ON Es.Id_estrutura = T.EstruturaId
        INNER JOIN dw_vista.dbo.DM_CR cr WITH(NOLOCK)
            ON cr.Id_cr = Es.Id_cr
        WHERE {campo} = :gr
          AND T.ChecklistId IN (
              :checklist1,
              :checklist2,
              :checklist3,
              :checklist4,
              :checklist5
          )
          AND MONTH(T.TerminoReal) = :month
          AND YEAR(T.TerminoReal) = :year
          AND T.Expirada = 0
          AND T.Status = {_STATUS_CONCLUIDA}
    """)
    params = {"gr": gr, **_checklist_params(), **_janela_mes_agora(agora)}
    return db.session.execute(sql, params).scalar()


def visitas_dia(campo, gr, agora=None):
    sql = text(f"""
        SELECT TOP 1 COUNT(T.NOME) AS TOTAL
        FROM Tarefa T WITH(NOLOCK)
        INNER JOIN dw_vista.dbo.DM_ESTRUTURA Es WITH(NOLOCK)
            ON Es.Id_estrutura = T.EstruturaId
        INNER JOIN dw_vista.dbo.DM_CR cr WITH(NOLOCK)
            ON cr.Id_cr = Es.Id_cr
        WHERE {campo} = :gr
          AND T.ChecklistId IN (
              :checklist1,
              :checklist2,
              :checklist3,
              :checklist4,
              :checklist5
          )
          AND DAY(T.TerminoReal) = :day
          AND MONTH(T.TerminoReal) = :month
          AND YEAR(T.TerminoReal) = :year
          AND T.Expirada = 0
          AND T.Status = {_STATUS_CONCLUIDA}
    """)
    agora = agora or dt.now()
    params = {"gr": gr, "day": agora.day, **_checklist_params(), **_janela_mes_agora(agora)}
    return db.session.execute(sql, params).scalar()


# ======================================================================
# TAREFAS
# ======================================================================
def tarefas_total(campo, gr, agora=None):
    sql = text(f"""
        SELECT COUNT(T.NOME) AS TOTAL
        FROM Tarefa T WITH(NOLOCK)
        INNER JOIN dw_vista.dbo.DM_ESTRUTURA Es WITH(NOLOCK)
            ON Es.Id_estrutura = T.EstruturaId
        INNER JOIN dw_vista.dbo.DM_CR cr WITH(NOLOCK)
            ON cr.Id_cr = Es.Id_cr
        WHERE {campo} = :gr
          AND MONTH(T.TerminoReal) = :month
          AND YEAR(T.TerminoReal) = :year
          AND T.Expirada = 0
          AND T.Status = {_STATUS_CONCLUIDA}
    """)
    params = {"gr": gr, **_janela_mes_agora(agora)}
    return db.session.execute(sql, params).scalar()


def tarefas_mes_anterior(campo, gr, agora=None):
    sql = text(f"""
        SELECT TOP 1 COUNT(T.NOME) AS TOTAL
        FROM Tarefa T WITH(NOLOCK)
        INNER JOIN dw_vista.dbo.DM_ESTRUTURA Es WITH(NOLOCK)
            ON Es.Id_estrutura = T.EstruturaId
        INNER JOIN dw_vista.dbo.DM_CR cr WITH(NOLOCK)
            ON cr.Id_cr = Es.Id_cr
        WHERE {campo} = :gr
          AND MONTH(T.TerminoReal) = :month
          AND YEAR(T.TerminoReal) = :year
          AND T.Expirada = 0
          AND T.Status = {_STATUS_CONCLUIDA}
    """)
    params = {"gr": gr, **_janela_mes_anterior(agora)}
    return db.session.execute(sql, params).scalar()


def tarefas_dia(campo, gr, agora=None):
    sql = text(f"""
        SELECT TOP 1 COUNT(T.NOME) AS TOTAL
        FROM Tarefa T WITH(NOLOCK)
        INNER JOIN dw_vista.dbo.DM_ESTRUTURA Es WITH(NOLOCK)
            ON Es.Id_estrutura = T.EstruturaId
        INNER JOIN dw_vista.dbo.DM_CR cr WITH(NOLOCK)
            ON cr.Id_cr = Es.Id_cr
        WHERE {campo} = :gr
          AND DAY(T.TerminoReal) = :day
          AND MONTH(T.TerminoReal) = :month
          AND YEAR(T.TerminoReal) = :year
          AND T.Expirada = 0
          AND T.Status = {_STATUS_CONCLUIDA}
    """)
    agora = agora or dt.now()
    params = {"gr": gr, "day": agora.day, **_janela_mes_agora(agora)}
    return db.session.execute(sql, params).scalar()


def escalonadas(campo, gr):
    sql = text(f"""
        SELECT COUNT(cr.GERENTE) AS TOTAL
        FROM Tarefa T WITH(NOLOCK)
        INNER JOIN dw_vista.dbo.DM_ESTRUTURA Es WITH(NOLOCK)
            ON Es.Id_estrutura = T.EstruturaId
        INNER JOIN dw_vista.dbo.DM_CR cr WITH(NOLOCK)
            ON cr.Id_cr = Es.Id_cr
        WHERE {campo} = :gr
          AND T.Escalonado > 0
          AND T.Expirada = 0
          AND T.Status IN ({", ".join(str(s) for s in _STATUS_ABERTAS)})
    """)
    return db.session.execute(sql, {"gr": gr}).scalar()


def performance(campo, gr, agora=None):
    sql = text(f"""
        SELECT DISTINCT
            CASE
                WHEN T.Escalonado = 0 THEN 'NO PRAZO'
                WHEN T.Escalonado > 0 THEN 'FORA DO PRAZO'
            END AS ST,
            COUNT(T.ID) AS TOTAL
        FROM TAREFA T
        INNER JOIN DW_VISTA.DBO.DM_ESTRUTURA DE
            ON DE.ID_ESTRUTURA = T.ESTRUTURAID
        INNER JOIN DW_VISTA.DBO.DM_CR DC
            ON DC.ID_CR = DE.ID_CR
        WHERE {campo} = :gr
          AND MONTH(T.TERMINOREAL) = :month
          AND YEAR(T.TERMINOREAL) = :year
          AND T.Expirada = 0
        GROUP BY T.Escalonado
        ORDER BY ST
    """)
    linhas = db.session.execute(
        sql, {"gr": gr, **_janela_mes_agora(agora)}
    ).mappings().all()

    st = {"FORA DO PRAZO": 0, "NO PRAZO": 0}
    for linha in linhas:
        if linha["ST"] in st:
            st[linha["ST"]] += int(linha["TOTAL"])

    return {"st": list(st.keys()), "total": list(st.values())}


# ======================================================================
# RANKINGS
# ======================================================================
def top3_sups(campo, gr, agora=None):
    sql = text(f"""
        SELECT TOP 3
            R.Nome,
            COUNT(R.Nome) AS TOTAL
        FROM Tarefa T WITH(NOLOCK)
        INNER JOIN RECURSO R WITH(NOLOCK)
            ON R.CODIGOHASH = T.FINALIZADOPORHASH
        INNER JOIN dw_vista.dbo.DM_ESTRUTURA Es WITH(NOLOCK)
            ON Es.Id_estrutura = T.EstruturaId
        INNER JOIN dw_vista.dbo.DM_CR cr WITH(NOLOCK)
            ON cr.Id_cr = Es.Id_cr
        WHERE {campo} = :gr
          AND T.ChecklistId IN (
              :checklist1,
              :checklist2,
              :checklist3,
              :checklist4,
              :checklist5
          )
          AND MONTH(T.TerminoReal) = :month
          AND YEAR(T.TerminoReal) = :year
          AND T.Expirada = 0
          AND T.Status = {_STATUS_CONCLUIDA}
        GROUP BY R.Nome
        ORDER BY TOTAL DESC
    """)
    params = {"gr": gr, **_checklist_params(), **_janela_mes_agora(agora)}
    linhas = db.session.execute(sql, params).mappings().all()
    return {"sup": [l["Nome"] for l in linhas], "total": [l["TOTAL"] for l in linhas]}


def _por_unidade(campo, gr, top, agora=None):
    limite = "TOP 3" if top else ""
    sql = text(f"""
        SELECT {limite}
            Nivel_03 AS UNIDADE,
            COUNT(T.Id) AS TOTAL
        FROM Tarefa T WITH(NOLOCK)
        INNER JOIN dw_vista.dbo.DM_ESTRUTURA Es WITH(NOLOCK)
            ON Es.Id_estrutura = T.EstruturaId
        INNER JOIN dw_vista.dbo.DM_CR cr WITH(NOLOCK)
            ON cr.Id_cr = Es.Id_cr
        WHERE {campo} = :gr
          AND MONTH(T.TerminoReal) = :month
          AND YEAR(T.TerminoReal) = :year
          AND T.Expirada = 0
          AND T.Status = {_STATUS_CONCLUIDA}
        GROUP BY Nivel_03
        ORDER BY TOTAL DESC
    """)
    linhas = db.session.execute(
        sql, {"gr": gr, **_janela_mes_agora(agora)}
    ).mappings().all()
    return {"uni": [l["UNIDADE"] for l in linhas], "total": [l["TOTAL"] for l in linhas]}


def top3_unidades(campo, gr, agora=None):
    return _por_unidade(campo, gr, top=True, agora=agora)


def unidades(campo, gr, agora=None):
    return _por_unidade(campo, gr, top=False, agora=agora)


def gerentes(campo, gr, agora=None):
    sql = text(f"""
        SELECT
            DC.GERENTE AS GERENTE,
            COUNT(T.ID) AS TOTAL
        FROM TAREFA T
        INNER JOIN DW_VISTA.DBO.DM_ESTRUTURA DE
            ON DE.ID_ESTRUTURA = T.ESTRUTURAID
        INNER JOIN DW_VISTA.DBO.DM_CR DC
            ON DC.ID_CR = DE.ID_CR
        WHERE {campo} = :gr
          AND T.Expirada = 0
          AND MONTH(T.TERMINOREAL) = :month
          AND YEAR(T.TERMINOREAL) = :year
        GROUP BY DC.GERENTE
        ORDER BY TOTAL DESC
    """)
    linhas = db.session.execute(
        sql, {"gr": gr, **_janela_mes_agora(agora)}
    ).mappings().all()
    return {"grs": [l["GERENTE"] for l in linhas], "total": [l["TOTAL"] for l in linhas]}


# ======================================================================
# SÉRIE DIÁRIA
# ======================================================================
def _por_dia(campo, gr, janela, ate_dia=None):
    filtro_dia = "AND DAY(T.TERMINOREAL) <= :day" if ate_dia else ""
    sql = text(f"""
        SELECT
            DAY(T.TERMINOREAL) AS DIA,
            COUNT(T.ID) AS TOTAL
        FROM TAREFA T
        INNER JOIN DW_VISTA.DBO.DM_ESTRUTURA DE
            ON DE.ID_ESTRUTURA = T.ESTRUTURAID
        INNER JOIN DW_VISTA.DBO.DM_CR DC
            ON DC.ID_CR = DE.ID_CR
        WHERE {campo} = :gr
          AND T.Expirada = 0
          {filtro_dia}
          AND MONTH(T.TERMINOREAL) = :month
          AND YEAR(T.TERMINOREAL) = :year
        GROUP BY DAY(T.TERMINOREAL)
        ORDER BY DIA
    """)
    params = {"gr": gr, **janela}
    if ate_dia:
        params["day"] = ate_dia
    linhas = db.session.execute(sql, params).mappings().all()
    return {"dia": [l["DIA"] for l in linhas], "total": [l["TOTAL"] for l in linhas]}


def graph_days(campo, gr, agora=None):
    return _por_dia(campo, gr, _janela_mes_agora(agora))


def graph_days_ant(campo, gr, agora=None):
    agora = agora or dt.now()
    return _por_dia(campo, gr, _janela_mes_anterior(agora), ate_dia=agora.day)


# ======================================================================
# AGREGADO DO PAINEL
# ======================================================================
def painel(opt, gr, agora=None, meta_percentual=None):
    """Todas as cifras do dashboard em uma única agregação.

    A regra de meta (mês anterior + percentual) e o gap viviam apenas em
    `static/js/base.js`. Estão aqui para que HTTP, Socket.IO e o modo demo calculem igual.
    """
    campo = coluna_de_filtro(opt)
    if not campo:
        raise ValueError(f"recorte inválido: {opt!r}")

    agora = agora or dt.now()
    if meta_percentual is None:
        meta_percentual = SETTINGS.meta_percentual

    def inteiro(valor):
        return int(valor or 0)

    total_mes = inteiro(tarefas_total(campo, gr, agora))
    total_dia = inteiro(tarefas_dia(campo, gr, agora))
    mes_anterior = inteiro(tarefas_mes_anterior(campo, gr, agora))

    meta_mes = round(mes_anterior * (1 + meta_percentual / 100))
    dias_no_mes = monthrange(agora.year, agora.month)[1]
    meta_dia = round(meta_mes / max(dias_no_mes - agora.day, 1))

    return {
        "atualizadoEm": agora.isoformat(timespec="seconds"),
        "recorte": {"opt": opt, "gr": gr},
        "totalMes": total_mes,
        "totalDia": total_dia,
        "visitasMes": inteiro(visitas_mes(campo, gr, agora)),
        "visitasDia": inteiro(visitas_dia(campo, gr, agora)),
        "escalonadas": inteiro(escalonadas(campo, gr)),
        "mesAnterior": mes_anterior,
        "metaMes": meta_mes,
        "metaDia": meta_dia,
        "gapMes": total_mes - meta_mes,
        "gapDia": total_dia - meta_dia,
        "performance": performance(campo, gr, agora),
        "top3Uni": top3_unidades(campo, gr, agora),
        "top3Sup": top3_sups(campo, gr, agora),
        "gerentes": gerentes(campo, gr, agora),
        "unidades": unidades(campo, gr, agora),
        "dias": graph_days(campo, gr, agora),
        "diasAnt": graph_days_ant(campo, gr, agora),
    }
