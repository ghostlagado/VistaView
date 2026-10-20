"""Cotações pela HTTP.

`/value/` existia antes do painel e respondia um número só; continua respondendo o mesmo
número, mas lido do cache do ciclo compartilhado. Chamava a API a cada requisição, e com
`X-Brapi-Concurrency-Limit: 1` isso significava TVs disputando a mesma cota.

`/cotacoes/` é a mesma faixa que o tempo real entrega, para o caminho de fallback do
navegador quando o socket não conecta.
"""

from flask import Blueprint, current_app, jsonify

actions_bp = Blueprint("Ações Financeiras", __name__)


@actions_bp.route("/value/")
def actValue():
    lista = current_app.config["VISTA_COTACOES"]()
    preco = lista[0]["preco"] if lista and lista[0]["preco"] is not None else None
    return jsonify(preco if preco else 0), 200


@actions_bp.route("/cotacoes/")
def cotacoes():
    return jsonify(current_app.config["VISTA_COTACOES"]()), 200
