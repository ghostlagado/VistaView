from flask import Blueprint, jsonify

from services.fonte import indicadores

visitas_bp = Blueprint("Visitas de Supervisores", __name__)

# ============================================================
# VISITAS DO MÊS
# ============================================================
@visitas_bp.route('/mes/<opt>/<gr>')
def visitasMes(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if campo is None:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.visitas_mes(campo, gr)), 200

# ============================================================
# VISITAS DO DIA
# ============================================================
@visitas_bp.route('/dia/<opt>/<gr>')
def visitasDia(opt, gr):
    fonte = indicadores()
    campo = fonte.coluna_de_filtro(opt)
    if campo is None:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(fonte.visitas_dia(campo, gr)), 200
