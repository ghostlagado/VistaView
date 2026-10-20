from flask import Blueprint, jsonify

from services import metricas

general_bp = Blueprint("Rotas Gerais", __name__)

# ============================================================
# TOP 3 SUPERVISORES
# ============================================================
@general_bp.route('/top3_sups/<opt>/<gr>')
def visitasSup(opt, gr):
    campo = metricas.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(metricas.top3_sups(campo, gr)), 200

# ============================================================
# TOP 3 UNIDADES
# ============================================================
@general_bp.route('/top3_uni/<opt>/<gr>')
def countuni(opt, gr):
    campo = metricas.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(metricas.top3_unidades(campo, gr)), 200

# ============================================================
# TODAS AS UNIDADES
# ============================================================
@general_bp.route('/get_unidades/<opt>/<gr>')
def getunidades(opt, gr):
    campo = metricas.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(metricas.unidades(campo, gr)), 200

# ============================================================
# GRÁFICO - DIAS DO MÊS
# ============================================================
@general_bp.route('/graph_days/<opt>/<gr>')
def graphdias(opt, gr):
    campo = metricas.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(metricas.graph_days(campo, gr)), 200

# ============================================================
# GRÁFICO - DIAS DO MÊS ANTERIOR
# ============================================================
@general_bp.route('/graph_days_ant/<opt>/<gr>')
def graphdiasant(opt, gr):
    campo = metricas.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(metricas.graph_days_ant(campo, gr)), 200

# ============================================================
# PERFORMANCE
# ============================================================
@general_bp.route('/get_performance/<opt>/<gr>')
def getperfomance(opt, gr):
    campo = metricas.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(metricas.performance(campo, gr)), 200

# ============================================================
# GERENTES
# ============================================================
@general_bp.route('/get_gerentes/<opt>/<gr>')
def getGerentes(opt, gr):
    campo = metricas.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(metricas.gerentes(campo, gr)), 200
