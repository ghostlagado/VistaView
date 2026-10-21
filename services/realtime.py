"""Publicação de eventos e atualização em tempo real do painel.

Um único ciclo no servidor recalcula o painel e transmite pelo fio apenas o que mudou.
Navegador nenhum consulta o banco por conta própria para manter a tela viva, e um novo
cliente conectado recebe o último snapshot em cache — não uma nova bateria de consultas.
"""

import gevent
from datetime import datetime, timezone
from flask import current_app
from flask_socketio import emit

EVENTO_SNAPSHOT = "dashboard:snapshot"
EVENTO_ATUALIZACAO = "dashboard:update"
EVENTO_STATUS = "dashboard:status"
EVENTO_SOLICITAR = "dashboard:solicitar"

_os_sockets_registrados = set()


def diff(anterior, atual):
    """Diferença de primeiro nível: campos inalterados não trafegam."""
    if not anterior:
        return dict(atual)
    return {chave: valor for chave, valor in atual.items() if anterior.get(chave) != valor}


def _estado_atualizador(atualizador):
    return {
        "fonte": getattr(atualizador, "nome_ciclo", None),
        "degradado": getattr(atualizador, "degradado", True),
        "falhasConsecutivas": getattr(atualizador, "_falhas_consecutivas", 0),
        "atualizadoEm": (getattr(atualizador, "snapshot", None) or {}).get("atualizadoEm"),
        # Instante em que o evento saiu, com fuso: é com ele que o relógio da TV se
        # alinha sem precisar de uma requisição só para perguntar que horas são.
        "emitidoEm": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


class AtualizadorPainel:
    """Greenlet que recalcula o painel de `intervalo` em `intervalo` segundos."""

    def __init__(self, socketio, recorte, intervalo=60, calcular=None, nome_ciclo="painel"):
        self.socketio = socketio
        self.recorte = tuple(recorte)
        self.intervalo = intervalo
        self.nome_ciclo = nome_ciclo
        self._calcular = calcular
        self._parar = gevent.event.Event()
        self._verde = None
        self._ultimo = None
        self._falhas_consecutivas = 0
        self.degradado = False

    # -- ciclo ---------------------------------------------------------
    def calcular(self, app):
        if self._calcular is None:
            # Sem injeção explícita, a fonte é a mesma das rotas. Cair num import direto
            # de `services.metricas` aqui faria um painel de demonstração consultar o
            # warehouse nas costas de quem configurou o modo.
            self._calcular = app.config["VISTA_FONTE"].painel
        with app.app_context():
            return self._calcular(*self.recorte)

    def ciclo(self, app):
        """Uma atualização. Falha de banco não derruba o greenlet nem apaga o último valor."""
        try:
            painel = self.calcular(app)
        except Exception:
            self._falhas_consecutivas += 1
            self.degradado = True
            app.logger.exception("falha ao atualizar o painel")
            self._emitir_status(app)
            return None

        self._falhas_consecutivas = 0
        self.degradado = False
        alteracoes = diff(self._ultimo, painel)
        self._ultimo = painel

        if alteracoes:
            self.socketio.emit(EVENTO_ATUALIZACAO, alteracoes, namespace="/")
        self._emitir_status(app)
        return painel

    def _emitir_status(self, app):
        self.socketio.emit(EVENTO_STATUS, _estado_atualizador(self), namespace="/")

    def _loop(self, app):
        # Primeira rodada imediato: quem conectar já encontra snapshot em cache.
        self.ciclo(app)
        while not self._parar.is_set():
            if self._parar.wait(self.intervalo):
                break
            self.ciclo(app)

    # -- ciclo de vida -------------------------------------------------
    def start(self, app):
        if self._verde is not None:
            return
        self._parar.clear()
        self._verde = gevent.spawn(self._loop, app)

    def stop(self, app=None):
        self._parar.set()
        verde, self._verde = self._verde, None
        if verde is not None:
            verde.kill(block=False)

    @property
    def snapshot(self):
        return self._ultimo


def registrar_handlers(socketio):
    """Connect e refresh sob pedido.

    Idempotente por instância de SocketIO: listeners duplicados fariam cada cliente
    receber o snapshot mais de uma vez. O atualizador é resolvido pelo app que atende
    o evento, não por closure, para que testes e o modo demo criem apps independentes.
    """
    if id(socketio) in _os_sockets_registrados:
        return

    def _responder():
        atualizador = current_app.extensions.get("vista_atualizador")
        snapshot = getattr(atualizador, "snapshot", None)
        if snapshot:
            emit(EVENTO_SNAPSHOT, snapshot, namespace="/")
        emit(EVENTO_STATUS, _estado_atualizador(atualizador), namespace="/")

    @socketio.on("connect", namespace="/")
    def _ao_conectar():
        _responder()

    @socketio.on(EVENTO_SOLICITAR, namespace="/")
    def _ao_solicitar():
        _responder()

    _os_sockets_registrados.add(id(socketio))
