"""Cotações de ações: um único processo fala com o provedor.

Medido na brapi (docs/cotacoes.md): `X-Brapi-Concurrency-Limit: 1` e
`RateLimit-Limit: 20` por janela de 60 s. Se cada TV conectada chamasse o provedor, o
limite estouraria no primeiro minuto e a cota mensal gratuita acabaria antes do mês. Por
isso este módulo é o único que faz requisição HTTP, e o painel — o ciclo de tempo real e
as rotas — lê o cache dele.

A resposta da brapi sai com `cache-control: s-maxage=300`: perguntar mais rápido que
cinco minutos não muda o preço, só gasta cota. Daí o intervalo padrão.
"""

import re
from datetime import datetime, timedelta, timezone

import gevent
import requests

PROVEDOR = "brapi"
URL = "https://brapi.dev/api/v2/stocks/quote"
MAX_SIMBOLOS = 5
INTERVALO_PADRAO = 300
# Cotação mais velha que isto é marcada na tela. Preferível admitir o atraso a fingir
# tempo real: quem decide comprar ou cobrar pelo painel precisa saber a idade do número.
VELHO_DEPOIS_MIN = 15
TENTATIVAS = 3
_ESPERA_ENTRE_TENTATIVAS = (2, 8)
_TIMEOUT = (5, 10)  # conectar, ler
MAX_ESPERA = 1800

# B3: de 4 a 6 alfanuméricos (GGPS3, PETR4, VAVC11, AAPL34 para BDR de empresa externa).
_SIMBOLO = re.compile(r"^[A-Z0-9]{4,6}$")

# 401/403/404 são definitivos: sem token, sem cota ou símbolo inexistente. Retentar um
# desses só gasta a cota mensal e atrasa o aviso de configuração.
_DEFINITIVOS = (401, 403, 404)


class FalhaDeCotacao(Exception):
    """A cotação não veio. O painel continua com a última válida."""


class FalhaDefinitiva(FalhaDeCotacao):
    """Requisição recusada pelo provedor; retentar não muda o resultado."""


class LimiteAtingido(FalhaDeCotacao):
    """O provedor pediu espera (`Retry-After`). A espera é respeitada, não ignorada."""

    def __init__(self, esperar, *args):
        super().__init__(*args)
        self.esperar = esperar


def agora_utc():
    return datetime.now(timezone.utc)


def normalizar_simbolos(texto, limite=MAX_SIMBOLOS):
    """Interpreta `COTACOES_SIMBOLOS` e devolve apenas símbolos válidos, sem repetição.

    Um nome inválido é descartado em vez de derrubar a faixa inteira: uma TV de gerência
    não pode perder todas as cotações porque alguém digitou um espaço a mais.
    """
    validos = []
    for bruto in (texto or "").split(","):
        simbolo = bruto.strip().upper().removesuffix(".SA")
        if _SIMBOLO.match(simbolo) and simbolo not in validos:
            validos.append(simbolo)
    return validos[:limite]


def _instante(valor):
    """`"2026-10-20T17:59:30.000Z"` → datetime com fuso, ou None."""
    if not valor:
        return None
    texto = str(valor)
    for formato in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(texto, formato).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None


def _segundos(valor, padrao):
    try:
        return max(int(valor), 0)
    except (TypeError, ValueError):
        return padrao


def buscar(simbolos, token, sessao=None, url=URL, timeout=_TIMEOUT):
    """Uma requisição para todos os símbolos de uma vez.

    Devolve `(buscado_em, resultados)`. Levanta `FalhaDefinitiva` ou `LimiteAtingido` —
    o chamador decide o que fazer com cada uma.
    """
    if not simbolos:
        raise FalhaDefinitiva("nenhum símbolo configurado (COTACOES_SIMBOLOS)")

    resposta = (sessao or requests).get(
        url,
        params={"symbols": ",".join(simbolos)},
        headers={"Authorization": f"Bearer {token}"} if token else {},
        timeout=timeout,
    )

    if resposta.status_code in _DEFINITIVOS:
        raise FalhaDefinitiva(
            f"{PROVEDOR} respondeu {resposta.status_code}: {resposta.text[:160]}"
        )
    if resposta.status_code == 429:
        raise LimiteAtingido(_segundos(resposta.headers.get("Retry-After"), 60),
                             f"{PROVEDOR} respondeu 429 (limite de requisições)")
    resposta.raise_for_status()

    corpo = resposta.json()
    if not isinstance(corpo, dict):
        raise FalhaDeCotacao(f"{PROVEDOR} devolveu resposta sem corpo JSON de objeto")
    buscado_em = _instante(corpo.get("requestedAt")) or agora_utc()
    return buscado_em, (corpo.get("results") or [])


def _registro(resultado):
    """Um item do provedor → o que guardamos em cache. None quando não é cotação usável."""
    dados = resultado.get("data") or {}
    simbolo = str(resultado.get("symbol") or resultado.get("requestedSymbol") or "").upper()
    preco = dados.get("regularMarketPrice")
    cotizado_em = _instante(dados.get("regularMarketTime"))
    if not simbolo or preco is None or cotizado_em is None:
        return None
    return {
        "preco": preco,
        "variacao": dados.get("regularMarketChangePercent"),
        "cotizado_em": cotizado_em,
        "provedor": PROVEDOR,
    }


class AtualizadorCotacoes:
    """Greenlet único que atualiza o cache; `cotacoes()` é leitura, nunca HTTP."""

    def __init__(self, simbolos=(), token="", intervalo=INTERVALO_PADRAO,
                 velho_depois_min=VELHO_DEPOIS_MIN, sessao=None, url=URL):
        self.simbolos = list(simbolos)
        self.token = token
        self.intervalo = max(int(intervalo), 60)
        self.velho_depois = timedelta(minutes=velho_depois_min)
        self._sessao = sessao
        self._url = url
        self._validos = {}
        self._buscado_em = None
        self._parar = gevent.event.Event()
        self._verde = None
        self._respeitar = 0
        self.falhas_consecutivas = 0
        self.degradado = False

    # -- leitura ---------------------------------------------------------
    def cotacoes(self, agora=None):
        """Última cotação válida de cada símbolo configurado, com a idade marcada.

        Símbolo sem cotação vem como item indisponível: a faixa existe na tela mesmo sem
        provedor, e o gerente vê que aquele número não chegou — não que vale zero.
        """
        agora = agora or agora_utc()
        saida = []
        for simbolo in self.simbolos:
            registro = self._validos.get(simbolo)
            if registro is None:
                saida.append({
                    "simbolo": simbolo, "preco": None, "variacao": None,
                    "cotizadoEm": "", "buscadoEm": None, "provedor": PROVEDOR,
                    "atual": False, "indisponivel": True,
                })
                continue
            velho = (agora - registro["cotizado_em"]) > self.velho_depois
            saida.append({
                "simbolo": simbolo,
                "preco": registro["preco"],
                "variacao": registro["variacao"],
                "cotizadoEm": registro["cotizado_em"].astimezone().strftime("%H:%M"),
                "buscadoEm": self._buscado_em.isoformat() if self._buscado_em else None,
                "provedor": registro["provedor"],
                "atual": not velho,
                "indisponivel": False,
            })
        return saida

    @property
    def snapshot(self):
        return self.cotacoes()

    # -- ciclo -----------------------------------------------------------
    def _colher(self):
        """Tenta o provedor até `TENTATIVAS` vezes, com backoff entre as tentativas."""
        erros = []
        for tentativa in range(TENTATIVAS):
            try:
                return buscar(self.simbolos, self.token, sessao=self._sessao, url=self._url)
            except (FalhaDefinitiva, LimiteAtingido) as erro:
                raise erro
            except Exception as erro:
                erros.append(erro)
                if tentativa < TENTATIVAS - 1:
                    gevent.sleep(_ESPERA_ENTRE_TENTATIVAS[tentativa])
        raise FalhaDeCotacao(
            f"{PROVEDOR} falhou em {TENTATIVAS} tentativas: {erros[-1]!r}"
        ) from erros[-1]

    def ciclo(self, app):
        """Uma atualização. Falha mantém a última cotação válida; não apaga a tela."""
        try:
            buscado_em, resultados = self._colher()
        except LimiteAtingido as erro:
            self._respeitar = erro.esperar
            self._falhou(app, erro)
            return None
        except FalhaDeCotacao as erro:
            self._falhou(app, erro)
            return None

        recebidos = 0
        for resultado in resultados:
            registro = _registro(resultado)
            if registro is None:
                continue
            simbolo = str(resultado.get("symbol") or resultado.get("requestedSymbol") or "").upper()
            self._validos[simbolo] = registro
            recebidos += 1

        self._buscado_em = buscado_em
        self.falhas_consecutivas = 0
        self.degradado = recebidos == 0 and bool(self.simbolos)
        if self.degradado:
            app.logger.warning("%s não devolveu nenhuma cotação usável", PROVEDOR)
        return self.cotacoes(buscado_em)

    def _falhou(self, app, erro):
        self.falhas_consecutivas += 1
        self.degradado = True
        app.logger.warning("cotações: %s", erro)

    def _espera(self):
        espera, self._respeitar = self._respeitar, 0
        if espera:
            return min(espera, MAX_ESPERA)
        if not self.falhas_consecutivas:
            return self.intervalo
        return min(self.intervalo * 2 ** self.falhas_consecutivas, MAX_ESPERA)

    def _loop(self, app):
        while not self._parar.is_set():
            self.ciclo(app)
            if self._parar.wait(self._espera()):
                break

    # -- ciclo de vida ---------------------------------------------------
    def start(self, app):
        if self._verde is not None or not self.simbolos:
            return
        self._parar.clear()
        self._verde = gevent.spawn(self._loop, app)

    def stop(self, app=None):
        self._parar.set()
        verde, self._verde = self._verde, None
        if verde is not None:
            verde.kill(block=False)
