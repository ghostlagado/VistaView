from utils.config import opts
from flask import Blueprint, jsonify
from datetime import datetime as dt
from sqlalchemy import text
from utils.db import db

tarefas_bp = Blueprint("Tarefas", __name__)

# ============================================================
# TOTAL DE ESCALONADAS
# ============================================================
@tarefas_bp.route('/escalonadas/<opt>/<gr>')
def escalonadas(opt, gr):
    selected_opt = opts.get(opt)
    if not selected_opt: return jsonify({'error': 'Opção inválida'}), 400

    sql = text(f"""
        SELECT COUNT(cr.GERENTE) AS TOTAL
        FROM Tarefa T WITH(NOLOCK)
        INNER JOIN dw_vista.dbo.DM_ESTRUTURA Es WITH(NOLOCK)
            ON Es.Id_estrutura = T.EstruturaId
        INNER JOIN dw_vista.dbo.DM_CR cr WITH(NOLOCK)
            ON cr.Id_cr = Es.Id_cr
        WHERE {selected_opt} = :gr
          AND T.Escalonado > 0
          AND T.Expirada = 0
          AND T.Status IN (25, 10, 70)
    """)
    result = db.session.execute(sql, {'gr': gr}).scalar()

    return {'total': result}, 200

# ============================================================
# TOTAL DE TAREFAS
# ============================================================
@tarefas_bp.route('/total/<opt>/<gr>')
def totalTarefas(opt, gr):
    campo = opts.get(opt)
    if not campo: return jsonify({'error': 'Opção inválida'}), 400

    agora = dt.now()

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
          AND T.Status = 85
    """)

    total = db.session.execute(
        sql,
        {
            'gr': gr,
            'month': agora.month,
            'year': agora.year
        }
    ).scalar()

    return jsonify(total), 200

# ============================================================
# TAREFAS DO MÊS ANTERIOR
# ============================================================
@tarefas_bp.route('/mes/anterior/<opt>/<gr>')
def tarefasMesAnt(opt, gr):

    campo = opts.get(opt)

    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400

    agora = dt.now()

    # Mantendo a mesma regra do código original:
    # mês atual - 1
    mes_anterior = agora.month - 1

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
          AND T.Status = 85
    """)

    total = db.session.execute(
        sql,
        {
            'gr': gr,
            'month': mes_anterior,
            'year': agora.year,
        }
    ).scalar()

    return jsonify(total), 200

# ============================================================
# TAREFAS DO DIA
# ============================================================
@tarefas_bp.route('/dia/<opt>/<gr>')
def tarefasDia(opt, gr):

    campo = opts.get(opt)

    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400

    agora = dt.now()

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
          AND T.Status = 85
    """)

    total = db.session.execute(
        sql,
        {
            'gr': gr,
            'day': agora.day,
            'month': agora.month,
            'year': agora.year,
        }
    ).scalar()

    return jsonify(total), 200
