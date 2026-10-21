"""Contrato e comportamento da atualização em tempo real (Socket.IO)."""

from datetime import datetime, timezone

import pytest

from app import create_app
from services.realtime import (
    EVENTO_ATUALIZACAO,
    EVENTO_SNAPSHOT,
    EVENTO_STATUS,
    AtualizadorPainel,
    diff,
    registrar_handlers,
)
from utils.config import Settings


class Gravador:
    """Substitui o SocketIO e registra o que teria sido transmitido."""

    def __init__(self):
        self.enviados = []

    def emit(self, evento, dados, namespace="/"):
        self.enviados.append((evento, dados, namespace))

    def de(self, evento):
        return [d for e, d, _ in self.enviados if e == evento]

    @property
    def total(self):
        return len(self.enviados)


def _painel(**over):
    base = {"atualizadoEm": "2026-10-20T12:00:00", "totalMes": 100, "visitasMes": 7}
    base.update(over)
    return base


# ======================================================================
# diff
# ======================================================================
def test_diff_sem_snapshot_anterior_manda_tudo():
    atual = _painel()
    assert diff(None, atual) == atual
    assert diff({}, atual) == atual


def test_diff_so_manda_o_que_mudou():
    anterior = _painel()
    atual = _painel(totalMes=140, atualizadoEm="2026-10-20T12:01:00")
    assert diff(anterior, atual) == {
        "atualizadoEm": "2026-10-20T12:01:00",
        "totalMes": 140,
    }


def test_diff_ignora_campo_novo_inalterado():
    assert diff({"a": 1}, {"a": 1, "b": 2}) == {"b": 2}


# ======================================================================
# ciclo
# ======================================================================
@pytest.fixture()
def atualizador():
    gravador = Gravador()
    fonte = [_painel()]
    alvo = AtualizadorPainel(
        gravador, recorte=("GR", "Parana Interior"), intervalo=1,
        calcular=lambda *a: fonte[0], nome_ciclo="teste",
    )
    return alvo, gravador, fonte


def test_primeiro_ciclo_emite_tudo(atualizador, app):
    alvo, gravador, fonte = atualizador
    alvo.ciclo(app)
    assert gravador.de(EVENTO_ATUALIZACAO)[0] == fonte[0]


def test_ciclo_identico_nao_retransmite(atualizador, app):
    alvo, gravador, fonte = atualizador
    alvo.ciclo(app)
    gravador.enviados.clear()
    alvo.ciclo(app)
    assert gravador.de(EVENTO_ATUALIZACAO) == []
    # apenas o status, que sempre acompanha o ciclo
    assert gravador.total == 1


def test_ciclo_emite_apenas_o_delta(atualizador, app):
    alvo, gravador, fonte = atualizador
    alvo.ciclo(app)
    fonte[0] = _painel(totalMes=180, atualizadoEm="2026-10-20T12:05:00")
    gravador.enviados.clear()
    alvo.ciclo(app)
    assert gravador.de(EVENTO_ATUALIZACAO) == [
        {"atualizadoEm": "2026-10-20T12:05:00", "totalMes": 180}
    ]


def test_um_ciclo_por_rodada_independente_de_clientes(atualizador, app):
    alvo, gravador, fonte = atualizador
    alvo.ciclo(app)
    alvo.ciclo(app)
    alvo.ciclo(app)
    atualizacoes = gravador.de(EVENTO_ATUALIZACAO)
    assert len(atualizacoes) == 1
    assert len(gravador.de(EVENTO_STATUS)) == 3


def test_status_reporta_fonte_e_horario(atualizador, app):
    alvo, gravador, fonte = atualizador
    alvo.ciclo(app)
    status = gravador.de(EVENTO_STATUS)[0]
    assert status["fonte"] == "teste"
    assert status["degradado"] is False
    assert status["falhasConsecutivas"] == 0
    assert status["atualizadoEm"] == "2026-10-20T12:00:00"


def test_status_leva_instante_com_fuso_para_o_relogio_da_tv(atualizador, app):
    """`emitidoEm` é o que alinha o relógio da tela ao do servidor.

    Sem fuso, uma TV em outro fuso acertaria o relógio com uma defasagem de horas, e
    o painel mostraria segundos errados com a conexão perfeita.
    """
    alvo, gravador, fonte = atualizador
    alvo.ciclo(app)
    emitido = datetime.fromisoformat(gravador.de(EVENTO_STATUS)[0]["emitidoEm"])
    assert emitido.tzinfo is not None
    assert abs((datetime.now(timezone.utc) - emitido).total_seconds()) < 5


def test_falha_nao_apaga_o_ultimo_valor_valido(atualizador, app):
    alvo, gravador, fonte = atualizador
    alvo.ciclo(app)
    valor_valido = alvo.snapshot

    def quebrado(*a):
        raise RuntimeError("banco fora do ar")

    alvo._calcular = quebrado
    alvo.ciclo(app)

    assert alvo.snapshot == valor_valido
    assert alvo.degradado is True
    assert gravador.de(EVENTO_STATUS)[-1]["falhasConsecutivas"] == 1


def test_falhas_sucessivas_acumulam_e_uma_sucesso_zera(atualizador, app):
    alvo, gravador, fonte = atualizador

    def quebrado(*a):
        raise RuntimeError("banco fora do ar")

    alvo._calcular = quebrado
    alvo.ciclo(app)
    alvo.ciclo(app)
    assert gravador.de(EVENTO_STATUS)[-1]["falhasConsecutivas"] == 2

    alvo._calcular = lambda *a: fonte[0]
    alvo.ciclo(app)
    ultimo = gravador.de(EVENTO_STATUS)[-1]
    assert ultimo["falhasConsecutivas"] == 0 and ultimo["degradado"] is False


def test_snapshot_disponivel_para_quem_conecta(atualizador, app):
    alvo, gravador, fonte = atualizador
    assert alvo.snapshot is None
    alvo.ciclo(app)
    assert alvo.snapshot == fonte[0]


# ======================================================================
# Handlers e múltiplos clientes
# ======================================================================
@pytest.fixture()
def app_com_snapshot(app):
    """Substitui o atualizador do app por um snapshot conhecido."""
    app.extensions["vista_atualizador"]._ultimo = _painel()
    return app


def test_cliente_ao_conectar_recebe_snapshot_e_status(app_com_snapshot):
    socketio = app_com_snapshot.extensions["vista_socketio"]
    recebido = socketio.test_client(app_com_snapshot).get_received()
    assert [d["name"] for d in recebido] == [EVENTO_SNAPSHOT, EVENTO_STATUS]
    assert recebido[0]["args"][0]["totalMes"] == 100


def test_cliente_ao_conectar_sem_snapshot_recebe_apenas_status(app):
    socketio = app.extensions["vista_socketio"]
    app.extensions["vista_atualizador"]._ultimo = None
    recebido = socketio.test_client(app).get_received()
    assert [d["name"] for d in recebido] == [EVENTO_STATUS]
    assert recebido[0]["args"][0]["degradado"] is False


def test_registrar_handlers_nao_duplica_o_snapshot(app_com_snapshot):
    socketio = app_com_snapshot.extensions["vista_socketio"]
    registrar_handlers(socketio)
    registrar_handlers(socketio)
    nomes = [d["name"] for d in socketio.test_client(app_com_snapshot).get_received()]
    assert nomes.count(EVENTO_SNAPSHOT) == 1


def test_clientes_multiplos_recebem_o_mesmo_delta_e_o_calculo_e_unico(app_com_snapshot):
    socketio = app_com_snapshot.extensions["vista_socketio"]
    clientes = [socketio.test_client(app_com_snapshot) for _ in range(3)]
    for cliente in clientes:
        cliente.get_received()  # drena snapshot + status da conexão

    alvo = app_com_snapshot.extensions["vista_atualizador"]
    alvo._ultimo = _painel(totalMes=100)
    chamadas = []

    def calcular(*a):
        chamadas.append(a)
        return _painel(totalMes=500)

    alvo._calcular = calcular
    alvo.ciclo(app_com_snapshot)

    assert len(chamadas) == 1, "o ciclo não pode consultar o banco uma vez por cliente"

    deltas = [
        [p["args"][0] for p in cliente.get_received() if p["name"] == EVENTO_ATUALIZACAO]
        for cliente in clientes
    ]
    assert deltas[0] == deltas[1] == deltas[2] == [{"totalMes": 500}]


def test_app_criado_depois_nao_descarrega_os_handlers_do_primeiro(app):
    """Regressão: compartilhar um SocketIO entre apps silenciosamente perdia o connect."""
    primeiro = app.extensions["vista_socketio"]
    segundo = create_app(
        Settings(
            host="127.0.0.1", port=8093, debug=False, secret="s",
            db_uri="sqlite:///:memory:", default_opt="GR", default_gr="x",
        )
    )
    assert primeiro is not segundo.extensions["vista_socketio"]

    app.extensions["vista_atualizador"]._ultimo = _painel()
    segundo.extensions["vista_atualizador"]._ultimo = _painel(totalMes=777)

    um = [d["name"] for d in primeiro.test_client(app).get_received()]
    dois = [d["name"] for d in segundo.extensions["vista_socketio"].test_client(segundo).get_received()]
    assert um == dois == [EVENTO_SNAPSHOT, EVENTO_STATUS]


def test_refresh_sob_pedido_devolve_o_snapshot_atuali(app_com_snapshot):
    from services.realtime import EVENTO_SOLICITAR

    socketio = app_com_snapshot.extensions["vista_socketio"]
    cliente = socketio.test_client(app_com_snapshot)
    cliente.get_received()

    cliente.emit(EVENTO_SOLICITAR, namespace="/")
    nomes = [d["name"] for d in cliente.get_received()]
    assert nomes == [EVENTO_SNAPSHOT, EVENTO_STATUS]


def test_start_nao_sobe_dois_greenlets(app, monkeypatch):
    alvo = AtualizadorPainel(None, recorte=("GR", "x"), calcular=lambda *a: None)
    verdes = []
    monkeypatch.setattr(
        "services.realtime.gevent.spawn",
        lambda fn, *a: verdes.append(fn) or type("V", (), {"kill": lambda self, block=True: None})(),
    )
    alvo.start(app)
    alvo.start(app)
    assert len(verdes) == 1


def test_stop_sinaliza_o_loop_e_libera_o_greenlet(app, monkeypatch):
    alvo = AtualizadorPainel(None, recorte=("GR", "x"), calcular=lambda *a: None)
    mortos = []
    fake = type("V", (), {"kill": lambda self, block=True: mortos.append(block)})()
    monkeypatch.setattr("services.realtime.gevent.spawn", lambda fn, *a: fake)
    alvo.start(app)
    alvo.stop(app)

    assert alvo._parar.is_set()
    assert alvo._verde is None
    assert mortos == [False]


def test_pode_reiniciar_depois_de_parar(app, monkeypatch):
    alvo = AtualizadorPainel(None, recorte=("GR", "x"), calcular=lambda *a: None)
    contagem = []
    monkeypatch.setattr(
        "services.realtime.gevent.spawn",
        lambda fn, *a: contagem.append(fn) or type("V", (), {"kill": lambda self, block=True: None})(),
    )
    alvo.start(app)
    alvo.stop(app)
    alvo.start(app)
    assert len(contagem) == 2
