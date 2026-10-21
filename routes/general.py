from flask import Blueprint, jsonify

from services.fonte import indicadores

general_bp = Blueprint("Rotas Gerais", __name__)

# ============================================================
# TOP 3 SUPERVISORES
# ============================================================
@general_bp.route('/top3_sups/<opt>/<gr>')
def visitasSup(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if campo is None:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.top3_sups(campo, gr)), 200

# ============================================================
# TOP 3 UNIDADES
# ============================================================
@general_bp.route('/top3_uni/<opt>/<gr>')
def countuni(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if campo is None:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.top3_unidades(campo, gr)), 200

# ============================================================
# TODAS AS UNIDADES
# ============================================================
@general_bp.route('/get_unidades/<opt>/<gr>')
def getunidades(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if campo is None:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.unidades(campo, gr)), 200

# ============================================================
# GRÁFICO - DIAS DO MÊS
# ============================================================
@general_bp.route('/graph_days/<opt>/<gr>')
def graphdias(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if campo is None:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.graph_days(campo, gr)), 200

# ============================================================
# GRÁFICO - DIAS DO MÊS ANTERIOR
# ============================================================
@general_bp.route('/graph_days_ant/<opt>/<gr>')
def graphdiasant(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if campo is None:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.graph_days_ant(campo, gr)), 200

# ============================================================
# PERFORMANCE
# ============================================================
@general_bp.route('/get_performance/<opt>/<gr>')
def getperfomance(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if campo is None:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.performance(campo, gr)), 200

# ============================================================
# GERENTES
# ============================================================
@general_bp.route('/get_gerentes/<opt>/<gr>')
def getGerentes(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if campo is None:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.gerentes(campo, gr)), 200
