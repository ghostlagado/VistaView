from flask import Blueprint, jsonify
from utils.actions import getPrice
actions_bp = Blueprint("Ações Financeiras", __name__)

# ============================================================
# VALOR ATUAL
# ============================================================
@actions_bp.route('/value/')
def actValue():
    value = getPrice()
    return jsonify(value if value else 0), 200