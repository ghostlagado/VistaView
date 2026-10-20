"""Entrypoint de produção.

Executa o servidor Socket.IO e encerra os serviços em segundo plano de forma ordenada
em SIGINT/SIGTERM. Os handlers só são instalados quando este arquivo é o processo
principal: atrás de um gestor (gunicorn/uWSGI) quem decide o sinal é o gestor.
"""

import signal
import sys

import services
from app import HOST, PORT, app, socketio


def _encerrar(signum, _frame):
    services.encerrar_todos(app)
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _encerrar)
    signal.signal(signal.SIGTERM, _encerrar)
    socketio.run(app, host=HOST, port=PORT)
