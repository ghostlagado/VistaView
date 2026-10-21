"""Socket.IO da aplicação.

Uma instância por app: registrar a mesma instância em dois apps faz o Flask-SocketIO
substituir os handlers do primeiro, e o `connect` deixa de ser chamado silenciosamente.
"""

from flask_socketio import SocketIO


def criar_socketio(cors_origins="*", async_mode="gevent") -> SocketIO:
    return SocketIO(cors_allowed_origins=cors_origins, async_mode=async_mode)
