from flask import Blueprint, jsonify

from services.fonte import indicadores

tarefas_bp = Blueprint("Tarefas", __name__)

# ============================================================
# TOTAL DE ESCALONADAS
# ============================================================
@tarefas_bp.route('/escalonadas/<opt>/<gr>')
def escalonadas(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify({'total': fonte.escalonadas(campo, gr)}), 200

# ============================================================
# TOTAL DE TAREFAS
# ============================================================
@tarefas_bp.route('/total/<opt>/<gr>')
def totalTarefas(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.tarefas_total(campo, gr)), 200

# ============================================================
# TAREFAS DO MÊS ANTERIOR
# ============================================================
@tarefas_bp.route('/mes/anterior/<opt>/<gr>')
def tarefasMesAnt(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.tarefas_mes_anterior(campo, gr)), 200

# ============================================================
# TAREFAS DO DIA
# ============================================================
@tarefas_bp.route('/dia/<opt>/<gr>')
def tarefasDia(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.tarefas_dia(campo, gr)), 200
