from utils.config import opts, CHECKLISTS_VISITAS
from flask import Blueprint, jsonify
from datetime import datetime as dt
from sqlalchemy import text
from utils.db import db

visitas_bp = Blueprint("Visitas de Supervisores", __name__)

# ============================================================
# VISITAS DO MÊS
# ============================================================
@visitas_bp.route('/mes/<opt>/<gr>')
def visitasMes(opt, gr):
    campo = opts.get(opt)
    if not campo: return jsonify({'error': 'Opção inválida'}), 400
    agora = dt.now()
    
    # Para SQL Server, fazemos o IN explicitamente parametrizado.
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
          AND T.Status = 85
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

    total = db.session.execute(sql, params).scalar()

    return jsonify(total), 200

# ============================================================
# VISITAS DO DIA
# ============================================================
@visitas_bp.route('/dia/<opt>/<gr>')
def visitasDia(opt, gr):
    campo = opts.get(opt)
    if not campo: return jsonify({'error': 'Opção inválida'}), 400
    agora = dt.now()

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
          AND T.Status = 85
    """)

    params = {
        'gr': gr,
        'checklist1': CHECKLISTS_VISITAS[0],
        'checklist2': CHECKLISTS_VISITAS[1],
        'checklist3': CHECKLISTS_VISITAS[2],
        'checklist4': CHECKLISTS_VISITAS[3],
        'checklist5': CHECKLISTS_VISITAS[4],
        'day': agora.day,
        'month': agora.month,
        'year': agora.year,
    }

    total = db.session.execute(sql, params).scalar()

    return jsonify(total), 200
