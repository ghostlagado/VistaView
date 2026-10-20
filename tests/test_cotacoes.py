"""Serviço de cotações: um processo só fala com o provedor, o resto lê cache.

Cobertura da fase 7 — contrato do provedor, limites de cota, retentativas com backoff,
última cotação válida preservada e marcação de dado desatualizado. Nenhuma chamada real
de rede acontece aqui: o provedor é sempre uma sessão falsa, exceto no teste que prova
que o painel não a alcança.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from services.cotacoes import (
    AtualizadorCotacoes,
    FalhaDeCotacao,
    FalhaDefinitiva,
    LimiteAtingido,
    buscar,
    normalizar_simbolos,
)
from utils.config import Settings


def _settings(**over):
    base = dict(
        host="127.0.0.1", port=8092, debug=False, secret="s",
        db_uri="sqlite:///:memory:", default_opt="GR", default_gr="Parana Interior",
        cotacoes_simbolos="GGPS3,PETR4", action_api="token-de-teste",
    )
    base.update(over)
    return Settings(**base)


def _instante(minutos_atras=0):
    return datetime.now(timezone.utc) - timedelta(minutes=minutos_atras)


def _iso(instante):
    return instante.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _corpo(simbolos, cotizado_em=None):
    cotizado_em = cotizado_em or _iso(_instante())
    return {
        "requestedAt": _iso(_instante()),
        "took": 0,
        "results": [
            {
                "requestedSymbol": s,
                "symbol": s,
                "changed": False,
                "data": {
                    "regularMarketPrice": 10 + i,
                    "regularMarketChangePercent": round(0.5 * (i - 1), 2),
                    "regularMarketTime": cotizado_em,
                    "currency": "BRL",
                },
            }
            for i, s in enumerate(simbolos)
        ],
    }


class Resposta:
    def __init__(self, status=200, corpo=None, cabecalhos=None, texto=""):
        self.status_code = status
        self._corpo = {} if corpo is None else corpo
        self.headers = cabecalhos or {}
        self.text = texto or json.dumps(self._corpo)

    def json(self):
        return self._corpo

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}")


class Sessao:
    """No código do serviço a sessão HTTP tem exatamente a interface de `requests`."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.chamadas.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return self.respostas.pop(0) if len(self.respostas) > 1 else self.respostas[0]


class Verde:
    """Greenlet falso: o teste verifica que `stop` mata exatamente o que foi criado."""

    def __init__(self):
        self.morto = False

    def kill(self, block=True):
        self.morto = True


class SemTempo:
    """Backoff não dorme de verdade num teste; registra as esperas pedidas."""

    def __init__(self):
        import gevent

        self.esperas = []
        self.event = gevent.event
        self.sleep = self._sleep

    def _sleep(self, segundos):
        self.esperas.append(segundos)

    def spawn(self, *args, **kwargs):
        raise AssertionError("o teste não deve disparar greenlet")


@pytest.fixture()
def sem_espera(monkeypatch):
    fake = SemTempo()
    monkeypatch.setattr("services.cotacoes.gevent", fake)
    return fake


# ------------------------------------------------------------------ símbolos
@pytest.mark.parametrize("texto,esperado", [
    ("GGPS3", ["GGPS3"]),
    ("ggps3,petr4", ["GGPS3", "PETR4"]),
    (" GGPS3 , PETR4 ", ["GGPS3", "PETR4"]),
    ("PETR4.SA", ["PETR4"]),
    ("VAVC11", ["VAVC11"]),
    ("GGPS3,GGPS3", ["GGPS3"]),
    ("", []),
    (None, []),
    ("ggs", []),
    ("GGPS3#", []),
    ("BOA1234", []),
])
def test_normalizar_simbolos(texto, esperado):
    assert normalizar_simbolos(texto) == esperado


def test_no_maximo_cinco_ativos():
    """Brief: até cinco símbolos. O sexto é descartado, não enviado ao provedor."""
    assert len(normalizar_simbolos("AAAA1,BBBB2,CCCC3,DDDD4,EEEE5,FFFF6")) == 5


def test_config_recusa_mais_de_cinco_ativos():
    with pytest.raises(RuntimeError, match="5 ativos"):
        _settings(cotacoes_simbolos="A1AAA,B2BBB,C3CCC,D4DDD,E5EEE,F6FFF").validar()


def test_config_recusa_ciclo_muito_rapido():
    with pytest.raises(RuntimeError, match="COTACOES_SEGUNDOS"):
        _settings(cotacoes_segundos=5).validar()


def test_config_recusa_marca_de_velha_inutil():
    with pytest.raises(RuntimeError, match="COTACOES_VELHO_MIN"):
        _settings(cotacoes_velho_min=0).validar()


# ------------------------------------------------------------------- provedor
def test_busca_todos_os_simbolos_em_uma_unica_requisicao():
    sessao = Sessao(Resposta(corpo=_corpo(["GGPS3", "PETR4"])))
    buscado_em, resultados = buscar(["GGPS3", "PETR4"], "t", sessao=sessao)

    assert len(sessao.chamadas) == 1
    assert sessao.chamadas[0]["params"] == {"symbols": "GGPS3,PETR4"}
    assert len(resultados) == 2
    assert buscado_em.tzinfo is not None


def test_autenticacao_sai_quando_ha_token():
    sessao = Sessao(Resposta(corpo=_corpo(["GGPS3"])))
    buscar(["GGPS3"], "t", sessao=sessao)
    assert sessao.chamadas[0]["headers"] == {"Authorization": "Bearer t"}


def test_sem_token_nao_envia_cabecalho_vazio():
    sessao = Sessao(Resposta(corpo=_corpo(["GGPS3"])))
    buscar(["GGPS3"], "", sessao=sessao)
    assert sessao.chamadas[0]["headers"] == {}


def test_toda_requisicao_tem_timeout():
    sessao = Sessao(Resposta(corpo=_corpo(["GGPS3"])))
    buscar(["GGPS3"], "t", sessao=sessao)
    assert sessao.chamadas[0]["timeout"] == (5, 10)


def test_sem_simbolo_configurado_e_falha_definitiva():
    with pytest.raises(FalhaDefinitiva, match="COTACOES_SIMBOLOS"):
        buscar([], "t", sessao=Sessao(Resposta()))


@pytest.mark.parametrize("status", [401, 403, 404])
def test_recusa_do_provedor_e_definitiva(status):
    """401 é o caso real de hoje (token ausente): retentar só gastaria cota."""
    sessao = Sessao(Resposta(status=status, texto="nao autorizado"))
    with pytest.raises(FalhaDefinitiva):
        buscar(["GGPS3"], "t", sessao=sessao)
    assert len(sessao.chamadas) == 1


def test_mensagem_de_erro_nao_vaza_o_token():
    sessao = Sessao(Resposta(status=401, texto="MISSING_TOKEN"))
    with pytest.raises(FalhaDefinitiva) as erro:
        buscar(["GGPS3"], "SEGREDINHO", sessao=sessao)
    assert "SEGREDINHO" not in str(erro.value)


def test_limite_de_requisicoes_carrega_o_retry_after():
    sessao = Sessao(Resposta(status=429, cabecalhos={"Retry-After": "120"}))
    with pytest.raises(LimiteAtingido) as erro:
        buscar(["GGPS3"], "t", sessao=sessao)
    assert erro.value.esperar == 120


def test_resposta_sem_objeto_e_falha_de_cotacao():
    with pytest.raises(FalhaDeCotacao):
        buscar(["GGPS3"], "t", sessao=Sessao(Resposta(corpo=["surpresa"])))


# ---------------------------------------------------------------------- cache
def _servico(simbolos=("GGPS3", "PETR4"), **over):
    kwargs = dict(simbolos=list(simbolos), token="t", intervalo=300, velho_depois_min=15)
    kwargs.update(over)
    return AtualizadorCotacoes(**kwargs)


def test_faixa_existe_antes_da_primeira_resposta():
    """A tela não pode perder o cartão de cotações enquanto o provedor não respondeu."""
    servico = _servico()
    faixa = servico.cotacoes()

    assert [c["simbolo"] for c in faixa] == ["GGPS3", "PETR4"]
    assert all(c["indisponivel"] and c["preco"] is None and not c["atual"] for c in faixa)


def test_cotacoes_nao_faz_requisicao():
    class ProvedorQueNaoDeveriaSerChamado:
        def get(self, *a, **k):
            raise AssertionError("leitura de cache não pode chamar o provedor")

    servico = _servico(sessao=ProvedorQueNaoDeveriaSerChamado())
    assert len(servico.cotacoes()) == 2


def test_ciclo_valido_guarda_preco_variacao_e_horas():
    agora = _instante()
    corpo = _corpo(["GGPS3", "PETR4"], cotizado_em=_iso(agora))
    servico = _servico(sessao=Sessao(Resposta(corpo=corpo)))

    faixa = servico.ciclo(_App())

    assert [c["preco"] for c in faixa] == [10, 11]
    assert all(c["atual"] and not c["indisponivel"] for c in faixa)
    assert all(c["provedor"] == "brapi" and c["cotizadoEm"] for c in faixa)
    assert all(c["buscadoEm"] for c in faixa)
    assert not servico.degradado and servico.falhas_consecutivas == 0


def test_cotacao_desconhecida_e_marcada_como_velha():
    corpo = _corpo(["GGPS3", "PETR4"], cotizado_em=_iso(_instante(minutos_atras=40)))
    servico = _servico(sessao=Sessao(Resposta(corpo=corpo)))

    faixa = servico.ciclo(_App())

    assert all(not c["atual"] and not c["indisponivel"] for c in faixa)
    assert [c["preco"] for c in faixa] == [10, 11]


def test_falha_preserva_a_ultima_cotacao_valida(sem_espera):
    servico = _servico(
        sessao=Sessao(Resposta(corpo=_corpo(["GGPS3", "PETR4"])), Resposta(status=500))
    )
    app = _App()
    servico.ciclo(app)

    faixa = servico.ciclo(app)

    assert servico.degradado and servico.falhas_consecutivas == 1
    assert faixa is None
    assert [c["preco"] for c in servico.cotacoes()] == [10, 11]


def test_falha_definitiva_nao_e_retentada(sem_espera):
    servico = _servico(sessao=Sessao(Resposta(status=401, texto="MISSING_TOKEN")))
    servico.ciclo(_App())

    assert len(servico._sessao.chamadas) == 1
    assert servico.falhas_consecutivas == 1
    assert sem_espera.esperas == []


def test_retenta_com_backoff_e_depois_desiste(sem_espera):
    """Timeout de rede é transitório: três tentativas, cada uma esperando mais."""
    import requests

    class Instavel:
        def __init__(self):
            self.n = 0
            self.esperas = []

        def get(self, url, params=None, headers=None, timeout=None):
            self.n += 1
            if self.n == 3:
                return Resposta(corpo=_corpo(["GGPS3", "PETR4"]))
            raise requests.Timeout("socket timeout")

    servico = _servico(sessao=Instavel())
    faixa = servico.ciclo(_App())

    assert servico._sessao.n == 3
    assert sem_espera.esperas == [2, 8]
    assert [c["preco"] for c in faixa] == [10, 11]
    assert servico.falhas_consecutivas == 0


def test_limite_atingido_adia_o_proximo_ciclo_pelo_retry_after(sem_espera):
    servico = _servico(sessao=Sessao(Resposta(status=429, cabecalhos={"Retry-After": "90"})))
    servico.ciclo(_App())

    assert servico._espera() == 90
    assert servico._respeitar == 0


def test_espera_cresce_enquanto_houver_falhas():
    servico = _servico(intervalo=300)
    servico.falhas_consecutivas = 1
    assert servico._espera() == 600
    servico.falhas_consecutivas = 2
    assert servico._espera() == 1200
    servico.falhas_consecutivas = 9
    assert servico._espera() == 1800


def test_resposta_sem_cotacao_usavel_degrada_mas_nao_apaga(sem_espera):
    servico = _servico(
        sessao=Sessao(Resposta(corpo=_corpo(["GGPS3", "PETR4"])), Resposta(corpo={"results": []}))
    )
    servico.ciclo(_App())
    faixa = servico.ciclo(_App())

    assert servico.degradado
    assert [c["preco"] for c in faixa] == [10, 11]


def test_simbolo_nao_devolvido_pelo_provedor_fica_indisponivel():
    corpo = _corpo(["GGPS3"])
    corpo["results"] = corpo["results"][:1]
    servico = _servico(sessao=Sessao(Resposta(corpo=corpo)))
    servico.ciclo(_App())

    faixa = servico.cotacoes()
    assert faixa[0]["preco"] == 10
    assert faixa[1]["indisponivel"] and faixa[1]["simbolo"] == "PETR4"


def test_item_sem_preco_ou_hora_nao_entra_como_valido():
    corpo = _corpo(["GGPS3", "PETR4"])
    corpo["results"][1]["data"]["regularMarketPrice"] = None
    servico = _servico(sessao=Sessao(Resposta(corpo=corpo)))
    servico.ciclo(_App())

    faixa = servico.cotacoes()
    assert faixa[0]["preco"] == 10
    assert faixa[1]["indisponivel"]


# ---------------------------------------------------------------- ciclo de vida
def test_nao_inicia_sem_simbolo_configurado():
    servico = _servico(simbolos=())
    servico.start(_App())
    assert servico._verde is None


def test_um_start_nao_duplica_o_greenlet(monkeypatch):
    import services.cotacoes as modulo

    disparados = []

    def falso_spawn(*args, **kwargs):
        disparados.append(args)
        return Verde()

    monkeypatch.setattr(modulo.gevent, "spawn", falso_spawn)
    servico = _servico()
    servico.start(_App())
    servico.start(_App())

    assert len(disparados) == 1
    servico.stop()
    assert servico._verde is None


# -------------------------------------------------------------------- aplicação
class App:
    """O serviço só usa `app.logger` — o bastante para rodar sem Flask nos testes."""

    class _Log:
        def __init__(self):
            self.avisos = []

        def warning(self, msg, *args):
            self.avisos.append(msg % args if args else msg)

    def __init__(self):
        self.logger = App._Log()


def _App():
    return App()


def test_aviso_de_falha_nao_contem_o_token():
    app = _App()
    servico = _servico(token="SEGREDINHO", sessao=Sessao(Resposta(status=401, texto="unauthorized")))
    servico.ciclo(app)

    assert app.logger.avisos
    assert all("SEGREDINHO" not in aviso for aviso in app.logger.avisos)


def test_modo_real_monta_o_servico_e_modo_demo_nao():
    real = create_app(_settings())
    assert "vista_cotacoes" in real.extensions
    assert callable(real.config["VISTA_COTACOES"])

    demo = create_app(_settings(db_uri="", demo=True))
    assert "vista_cotacoes" not in demo.extensions


def test_snapshot_do_painel_traz_a_faixa_do_cache(capture_sql):
    real = create_app(_settings())
    dados = real.extensions["vista_atualizador"].calcular(real)
    assert [c["simbolo"] for c in dados["cotacoes"]] == ["GGPS3", "PETR4"]
    assert all(c["provedor"] == "brapi" for c in dados["cotacoes"])
