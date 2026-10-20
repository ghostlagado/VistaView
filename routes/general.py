from utils.config import opts, CHECKLISTS_VISITAS
from flask import Blueprint, jsonify
from datetime import datetime as dt
from sqlalchemy import text
from utils.db import db

general_bp = Blueprint("Rotas Gerais", __name__)

# ============================================================
# TOP 3 SUPERVISORES
# ============================================================
@general_bp.route('/top3_sups/<opt>/<gr>')
def visitasSup(opt, gr):

    campo = opts.get(opt)

    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400

    agora = dt.now()

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
          AND T.Status = 85
        GROUP BY R.Nome
        ORDER BY TOTAL DESC
    """)

    params = {
        'gr': gr,
        'checklist1': CHECKLISTS_VISITAS[0],
        'checklist2': CHECKLISTS_VISITAS[1],
        'checklist3': CHECKLISTS_VISITAS[2],
        'checklist4': CHECKLISTS_VISITAS[3],
        'checklist5': CHECKLISTS_VISITAS[4],
        'month': agora.month,
        'year': agora.year,
    }

    result = db.session.execute(sql, params)

    dados = result.mappings().all()

    return jsonify({
        'sup': [item['Nome'] for item in dados],
        'total': [item['TOTAL'] for item in dados],
    }), 200

# ============================================================
# TOP 3 UNIDADES
# ============================================================
@general_bp.route('/top3_uni/<opt>/<gr>')
def countuni(opt, gr):

    campo = opts.get(opt)

    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400

    agora = dt.now()

    sql = text(f"""
        SELECT TOP 3
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
          AND T.Status = 85
        GROUP BY Nivel_03
        ORDER BY TOTAL DESC
    """)

    result = db.session.execute(
        sql,
        {
            'gr': gr,
            'month': agora.month,
            'year': agora.year,
        }
    )

    dados = result.mappings().all()

    return jsonify({
        'uni': [item['UNIDADE'] for item in dados],
        'total': [item['TOTAL'] for item in dados],
    }), 200

# ============================================================
# TODAS AS UNIDADES
# ============================================================
@general_bp.route('/get_unidades/<opt>/<gr>')
def getunidades(opt, gr):

    campo = opts.get(opt)

    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400

    agora = dt.now()

    sql = text(f"""
        SELECT
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
          AND T.Status = 85
        GROUP BY Nivel_03
        ORDER BY TOTAL DESC
    """)

    result = db.session.execute(
        sql,
        {
            'gr': gr,
            'month': agora.month,
            'year': agora.year,
        }
    )

    dados = result.mappings().all()

    return jsonify({
        'uni': [item['UNIDADE'] for item in dados],
        'total': [item['TOTAL'] for item in dados],
    }), 200

# ============================================================
# GRÁFICO - DIAS DO MÊS
# ============================================================
@general_bp.route('/graph_days/<opt>/<gr>')
def graphdias(opt, gr):

    campo = opts.get(opt)

    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400

    agora = dt.now()

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
          AND MONTH(T.TERMINOREAL) = :month
          AND YEAR(T.TERMINOREAL) = :year
        GROUP BY DAY(T.TERMINOREAL)
        ORDER BY DIA
    """)

    result = db.session.execute(
        sql,
        {
            'gr': gr,
            'month': agora.month,
            'year': agora.year,
        }
    )

    dados = result.mappings().all()

    return jsonify({
        'dia': [item['DIA'] for item in dados],
        'total': [item['TOTAL'] for item in dados],
    }), 200

# ============================================================
# GRÁFICO - DIAS DO MÊS ANTERIOR
# ============================================================
@general_bp.route('/graph_days_ant/<opt>/<gr>')
def graphdiasant(opt, gr):

    campo = opts.get(opt)

    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400

    agora = dt.now()

    # Mês anterior com correção de ano: em janeiro a referência é dezembro do ano anterior.
    mes_anterior = agora.month - 1
    ano_referencia = agora.year
    if mes_anterior == 0:
        mes_anterior = 12
        ano_referencia = agora.year - 1
    dia_atual = agora.day

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
          AND DAY(T.TERMINOREAL) <= :day
          AND MONTH(T.TERMINOREAL) = :month
          AND YEAR(T.TERMINOREAL) = :year
        GROUP BY DAY(T.TERMINOREAL)
        ORDER BY DIA
    """)

    result = db.session.execute(
        sql,
        {
            'gr': gr,
            'day': dia_atual,
            'month': mes_anterior,
            'year': ano_referencia,
        }
    )

    dados = result.mappings().all()

    return jsonify({
        'dia': [item['DIA'] for item in dados],
        'total': [item['TOTAL'] for item in dados],
    }), 200

# ============================================================
# PERFORMANCE
# ============================================================
@general_bp.route('/get_performance/<opt>/<gr>')
def getperfomance(opt, gr):

    campo = opts.get(opt)

    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400

    agora = dt.now()

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

    result = db.session.execute(
        sql,
        {
            'gr': gr,
            'month': agora.month,
            'year': agora.year,
        }
    )

    dados = result.mappings().all()

    st = {
        'FORA DO PRAZO': 0,
        'NO PRAZO': 0,
    }

    for item in dados:
        if item['ST'] in st:
            st[item['ST']] += int(item['TOTAL'])

    return jsonify({
        'st': list(st.keys()),
        'total': list(st.values()),
    }), 200

# ============================================================
# GERENTES
# ============================================================
@general_bp.route('/get_gerentes/<opt>/<gr>')
def getGerentes(opt, gr):
    campo = opts.get(opt)
    if not campo: return jsonify({'error': 'Opção inválida'}), 400
    agora = dt.now()

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

    result = db.session.execute(
        sql,
        {
            'gr': gr,
            'month': agora.month,
            'year': agora.year,
        }
    )

    dados = result.mappings().all()

    return jsonify({
        'grs': [item['GERENTE'] for item in dados],
        'total': [item['TOTAL'] for item in dados],
    }), 200