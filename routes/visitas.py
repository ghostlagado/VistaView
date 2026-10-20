from flask import Blueprint, jsonify

from services import metricas

visitas_bp = Blueprint("Visitas de Supervisores", __name__)

# ============================================================
# VISITAS DO MÊS
# ============================================================
@visitas_bp.route('/mes/<opt>/<gr>')
def visitasMes(opt, gr):
    campo = metricas.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(metricas.visitas_mes(campo, gr)), 200

# ============================================================
# VISITAS DO DIA
# ============================================================
@visitas_bp.route('/dia/<opt>/<gr>')
def visitasDia(opt, gr):
    campo = metricas.coluna_de_filtro(opt)
    if not campo:
        return jsonify({'error': 'Opção inválida'}), 400
    return jsonify(metricas.visitas_dia(campo, gr)), 200
