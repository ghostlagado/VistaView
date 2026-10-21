"""Contratos de rota entre o front-end (static/js) e o back-end (routes/).

Estes testes existem porque, na auditoria inicial, 7 de 12 chamadas `fetch` do
front-end apontavam para URLs que não existiam no back-end.
"""

import re
from pathlib import Path

import pytest

JS_FILES = ["static/js/base.js", "static/js/chart.js"]
FETCH_RE = re.compile(r"fetch\(\s*[`'\"]([^`'\"]+)[`'\"]")

# `painel.js` monta a URL a partir de um mapa, então o contrato é o próprio mapa.
PAINEL_JS = "static/js/painel.js"
ROTAS_BLOCO_RE = re.compile(r"const ROTAS = \{(.*?)^\s*\}", re.S | re.M)
ROTAS_ITEM_RE = re.compile(r"[`'\"](/[^`'\"]+)[`'\"]")

# Meta e gap saem do servidor no snapshot, mas no caminho HTTP são calculados na página.
DERIVADOS_NO_NAVEGADOR = {"metaMes", "metaDia", "gapMes", "gapDia"}
# `atualizadoEm` vem do servidor no snapshot; na consulta HTTP a página usa a hora local.
SÓ_NO_SNAPSHOT = {"atualizadoEm"}
# `recorte` é metadado do filtro, não é desenhado.
SÓ_NO_SNAPSHOT.add("recorte")


def painel_source(app_root):
    return (app_root / PAINEL_JS).read_text(encoding="utf-8")


def rotas_http(source):
    bloco = ROTAS_BLOCO_RE.search(source)
    assert bloco, f"{PAINEL_JS} perdeu o mapa ROTAS; o contrato deixaria de ser coberto."
    return {chave for chave, _ in re.findall(r"(\w+):\s*[`'\"](/[^`'\"]+)[`'\"]", bloco.group(1))}


def frontend_paths(app_root):
    paths = set()
    for rel in JS_FILES:
        source = (app_root / rel).read_text(encoding="utf-8")
        for raw in FETCH_RE.findall(source):
            paths.add(re.sub(r"\$\{[^}]+\}", "PLACEHOLDER", raw))

    for rota in ROTAS_ITEM_RE.findall(ROTAS_BLOCO_RE.search(painel_source(app_root)).group(1)):
        paths.add(rota + "PLACEHOLDER/PLACEHOLDER")
    # Chamadas literais de `painel.js` (cotações e o valor antigo da ação) não levam recorte.
    for rota in FETCH_RE.findall(painel_source(app_root)):
        paths.add(rota)
    return paths


@pytest.fixture()
def app_root():
    return Path(__file__).resolve().parents[1]


def test_toda_chamada_fetch_existe_no_back_end(app, app_root):
    resolver = app.url_map.bind("localhost")
    missing = []
    for path in sorted(frontend_paths(app_root)):
        try:
            resolver.match(path)
        except Exception:
            missing.append(path)
    assert not missing, f"fetch() do front-end sem rota no back-end: {missing}"


def test_os_dois_caminhos_de_pintura_tem_o_mesmo_payload(app, app_root, capture_sql):
    """Socket.IO entrega o snapshot; sem socket a página remonta o mesmo objeto.

    Se um campo nascer só de um lado, a TV mostra números diferentes conforme a conexão.
    """
    with app.app_context():
        atualizador = app.extensions["vista_atualizador"]
        campos_do_snapshot = set(atualizador.calcular(app))
    cobertos_pelo_http = rotas_http(painel_source(app_root)) | DERIVADOS_NO_NAVEGADOR
    # Cotação não é por recorte: tem rota própria, fora do mapa de indicadores.
    cobertos_pelo_http.add("cotacoes")

    assert campos_do_snapshot - cobertos_pelo_http == SÓ_NO_SNAPSHOT
    assert cobertos_pelo_http - campos_do_snapshot == set()


def test_a_rota_de_cotacoes_devolve_a_faixa_do_cache(app):
    """O caminho HTTP de fallback precisa da mesma lista que o snapshot entrega."""
    resposta = app.test_client().get("/actions/cotacoes/")
    assert resposta.status_code == 200
    lista = resposta.get_json()
    assert isinstance(lista, list) and lista
    assert {"simbolo", "preco", "variacao", "cotizadoEm", "buscadoEm", "provedor",
            "atual", "indisponivel"} <= set(lista[0])


def test_a_rota_de_cotacoes_nao_consulta_o_provedor(app, monkeypatch):
    """A rota lê cache: abrir o painel não pode gastar a cota mensal em cada requisição."""
    import services.cotacoes as cotacoes

    def estourar(*args, **kwargs):
        raise AssertionError("rota HTTP não pode chamar o provedor")

    monkeypatch.setattr(cotacoes, "buscar", estourar)
    assert app.test_client().get("/actions/cotacoes/").status_code == 200
    assert app.test_client().get("/actions/value/").status_code == 200


def test_pagina_principal_renderiza_com_recorte(app, client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert f'data-gr="{app.config["DEFAULT_GR"]}"' in html
    assert f'data-opt="{app.config["DEFAULT_OPT"]}"' in html
    assert f'data-meta="{app.config["META_PERCENTUAL"]}"' in html


def test_pagina_principal_carrega_tempo_real_sem_recarregar_a_pagina(app, client):
    html = client.get("/").get_data(as_text=True)
    assert "http-equiv" not in html, "meta refresh convivendo com Socket.IO: a TV piscaria."
    assert "/static/js/tempo-real.js" in html
    assert "/static/js/painel.js" in html


def test_pagina_de_demonstracao_renderiza(app, client):
    assert client.get("/showcase").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/top3_sups/XX/gr",
        "/top3_uni/XX/gr",
        "/get_unidades/XX/gr",
        "/graph_days/XX/gr",
        "/graph_days_ant/XX/gr",
        "/get_performance/XX/gr",
        "/get_gerentes/XX/gr",
        "/visitas/mes/XX/gr",
        "/visitas/dia/XX/gr",
        "/tarefas/escalonadas/XX/gr",
        "/tarefas/total/XX/gr",
        "/tarefas/mes/anterior/XX/gr",
        "/tarefas/dia/XX/gr",
    ],
)
def test_opt_invalido_e_recusado(client, path):
    resp = client.get(path)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Opção inválida"
