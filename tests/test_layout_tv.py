"""Contrato visual do painel de TV.

Estes testes não medem pixels: travam as decisões de layout que foram pedidas
explicitamente, para que uma edição futura não as desfaça em silêncio — a barra
voltando a ter três tags, o letreiro se repetindo em texto, a faixa de unidades
caindo de volta num `<marquee>` ou o relógio perdendo os segundos.
"""

import re
from pathlib import Path

import pytest


@pytest.fixture()
def raiz():
    return Path(__file__).resolve().parents[1]


@pytest.fixture()
def html(raiz):
    return (raiz / "templates/dash.html").read_text(encoding="utf-8")


@pytest.fixture()
def css(raiz):
    return (raiz / "static/css/painel.css").read_text(encoding="utf-8")


@pytest.fixture()
def js(raiz):
    return (raiz / "static/js/painel.js").read_text(encoding="utf-8")


def trecho(texto, inicio, fim):
    comeco = texto.index(inicio)
    return texto[comeco:texto.index(fim, comeco)]


# ------------------------------------------------------------------ barra
def test_a_barra_tem_uma_unica_tag_de_status(html):
    cabecalho = trecho(html, "<header", "</header>")
    assert cabecalho.count('id="selo') == 1
    assert "seloQualidade" not in html
    assert "seloAtualizacao" not in html


def test_o_estado_da_tag_vem_da_conexao_real_nao_da_pagina(js):
    """`Offline` antes do primeiro `connect` do socket, `Online` depois."""
    estados = trecho(js, "const ESTADOS = {", "};")
    assert re.search(r"conectado:\s*\['Online'", estados)
    for nome in ("iniciando", "desconectado", "reconectando", "indisponivel"):
        assert re.search(nome + r":\s*\['Offline'", estados)


def test_a_marca_aparece_uma_unica_vez(html):
    assert "cabecalho__logo" in html
    assert "cabecalho__titulo" not in html
    assert not re.search(r">\s*GPS\s*VISTA\s*<", html)


def test_o_demo_nao_reaparece_como_badge(html):
    assert "DEMO" not in html
    assert "selo--demo" not in html


# ------------------------------------------------------------------ relógio
def test_o_relogio_mostra_segundos_e_anda_so(js):
    assert "second: '2-digit'" in js
    assert re.search(r"setInterval\(tick,\s*1000\)", js)
    assert "atualizado há" not in js


def test_o_relogio_se_alinha_pelo_tempo_do_servidor_e_nao_por_requisicao(js):
    assert "sincronizarRelogio(st && st.emitidoEm)" in js
    # A referência no caminho HTTP é o cabeçalho de uma resposta que já ia acontecer.
    assert "headers.get('Date')" in js


# ------------------------------------------------------------------ faixa
def test_a_faixa_nao_usa_a_tag_marquee(html, js, css):
    assert "<marquee" not in html
    assert "marquee" not in js
    assert "animation: deslizar" in css


def test_a_faixa_duplica_o_conteudo_e_anda_um_periodo_exato(css, js):
    assert "translateX(-50%)" in css
    assert "faixa__grupo" in js and "faixa__trilho" in js
    # Par de cópias: é o que faz -50% cair na borda do período, sem emenda.
    assert re.search(r"if \(alvo % 2\) alvo \+= 1", js)


def test_a_faixa_respeita_quem_pediu_menos_movimento(css):
    bloco = trecho(css, "@media (prefers-reduced-motion: reduce)", "}")
    assert "faixa__trilho" in bloco
    assert "animation: none" in bloco


def test_a_faixa_para_quando_tudo_cabe_na_janela(js):
    assert "faixa--parada" in js
    assert "tudoVisivel" in js


# ------------------------------------------------------------------ tipografia e folga
def test_os_numeros_dos_cards_descem_2px_sem_perder_a_hierarquia(css):
    regra = trecho(css, ".kpi__valor {", "}")
    assert re.search(r"font-size:\s*calc\(1\.9em\s*-\s*2px\)", regra)
    assert "font-weight: 800" in regra


def test_a_folga_sai_de_uma_escala_só(css):
    assert "--folga:" in css and "--respiro:" in css
    assert css.count("var(--folga)") >= 5


def test_a_tela_nao_rola_em_16_9(css):
    assert re.search(r"html, body \{[^}]*overflow: hidden", css)
    assert "height: 100vh" in css
