"""Critérios de aceitação anti-regressão (docs/auditoria-e-baseline.md §6).

Cada teste aqui corresponde a um item da lista que a auditoria da Fase 1 definiu como
verdade que nenhuma fase pode quebrar. Os números de item estão nos docstrings para
permitir rastrear o requisito até a entrega.
"""

import pytest

from app import create_app
from services import metricas, showcase
from services.cotacoes import FalhaDeCotacao
from utils.config import CHECKLISTS_VISITAS, Settings

# ---------------------------------------------------------------- item 1
BASELINE = {
    "/",
    "/showcase",
    "/actions/value/",
    "/get_gerentes/<opt>/<gr>",
    "/get_performance/<opt>/<gr>",
    "/get_unidades/<opt>/<gr>",
    "/graph_days/<opt>/<gr>",
    "/graph_days_ant/<opt>/<gr>",
    "/tarefas/dia/<opt>/<gr>",
    "/tarefas/escalonadas/<opt>/<gr>",
    "/tarefas/mes/anterior/<opt>/<gr>",
    "/tarefas/total/<opt>/<gr>",
    "/top3_sups/<opt>/<gr>",
    "/top3_uni/<opt>/<gr>",
    "/visitas/dia/<opt>/<gr>",
    "/visitas/mes/<opt>/<gr>",
    # única rota nova: o caminho HTTP de fallback da faixa de cotações (Fase 7).
    "/actions/cotacoes/",
}


def rotas(app):
    return {str(rule) for rule in app.url_map.iter_rules() if rule.endpoint != "static"}


def test_o_mapa_de_rotas_e_o_da_baseline_mais_a_rota_de_cotacoes(app):
    """Item 1: as 13 rotas JSON continuam com o mesmo path; nada foi renomeado ou perdido."""
    assert rotas(app) == BASELINE


def test_as_rotas_de_indicador_aceitam_so_get(app):
    """Item 1: o método não mudou — quem consome as rotas chama GET."""
    for rule in app.url_map.iter_rules():
        if str(rule) in BASELINE and str(rule) != "/showcase":
            assert rule.methods >= {"GET"}
            assert not (rule.methods & {"POST", "PUT", "DELETE"}), str(rule)


# ---------------------------------------------------------------- item 3
FOLHAS = (
    "tarefas_total", "tarefas_dia", "tarefas_mes_anterior", "visitas_mes", "visitas_dia",
    "escalonadas", "performance", "top3_unidades", "top3_sups", "gerentes", "unidades",
    "graph_days", "graph_days_ant",
)


@pytest.fixture()
def sem_backoff(monkeypatch):
    """O backoff é real (2 s, 8 s); num teste ele só atrasa a suíte."""
    monkeypatch.setattr("services.cotacoes.gevent.sleep", lambda segundos: None)


@pytest.fixture()
def tudo_quebrado(monkeypatch):
    """Warehouse e provedor fora do ar ao mesmo tempo — o pior dia possível da TV."""
    def estourar(nome):
        def _folha(*args, **kwargs):
            raise RuntimeError(f"{nome} fora do ar")
        return _folha

    for folha in FOLHAS:
        monkeypatch.setattr(metricas, folha, estourar(folha))
    monkeypatch.setattr("services.cotacoes.buscar",
                        lambda *a, **k: (_ for _ in ()).throw(FalhaDeCotacao("provedor fora do ar")))
    return None


def test_a_pagina_sai_mesmo_com_tudo_fora_do_ar(app, tudo_quebrado):
    """Item 3: `/` renderiza mesmo com falha de qualquer indicador e do provedor."""
    resposta = app.test_client().get("/")
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert 'id="listaCotacoes"' in html and "painel" in html


def test_o_ciclo_nao_quebra_com_indicadores_fora_do_ar(tudo_quebrado):
    """Item 3: a exceção do banco fica no ciclo, que marca degradado e mantém o último valor.

    Usa um app próprio: o `app` da suíte é o da aplicação real e o estado degradado
    vazaría para os testes de tempo real que compartilham aquela instância.
    """
    app = create_app(_settings())
    atualizador = app.extensions["vista_atualizador"]
    assert atualizador.ciclo(app) is None
    assert atualizador.degradado and atualizador._falhas_consecutivas == 1
    assert atualizador.snapshot is None


def test_o_provedor_fora_do_ar_nao_derruba_o_snapshot(app, capture_sql, sem_backoff, monkeypatch):
    """Item 3 e 5: sem provedor o painel sai igual, com a faixa marcada como indisponível."""
    def estourar(*args, **kwargs):
        raise FalhaDeCotacao("timeout")

    monkeypatch.setattr("services.cotacoes.buscar", estourar)
    servico = app.extensions["vista_cotacoes"]
    assert servico.ciclo(app) is None

    with app.app_context():
        dados = app.extensions["vista_atualizador"].calcular(app)

    assert all(c["indisponivel"] and c["preco"] is None for c in dados["cotacoes"])
    assert dados["totalMes"] is not None or "totalMes" in dados


# ---------------------------------------------------------------- item 5
def test_nenhuma_requisicao_http_chama_o_provedor(app, capture_sql, monkeypatch):
    """Item 5: nenhum cliente conectado gera chamada ao provedor por conta própria."""
    chamadas = []

    def vigia(*args, **kwargs):
        chamadas.append(args)
        raise AssertionError("o provedor não devia ser chamado aqui")

    monkeypatch.setattr("services.cotacoes.buscar", vigia)
    cliente = app.test_client()
    with app.app_context():
        app.extensions["vista_atualizador"].calcular(app)
    for _ in range(20):
        assert cliente.get("/").status_code == 200
        assert cliente.get("/actions/cotacoes/").status_code == 200
        assert cliente.get("/actions/value/").status_code == 200
    assert chamadas == []


# ---------------------------------------------------------------- item 4 e registro
def _settings(**over):
    base = dict(
        host="127.0.0.1", port=8092, debug=False, secret="s",
        db_uri="sqlite:///:memory:", default_opt="GR", default_gr="Parana Interior",
    )
    base.update(over)
    return Settings(**base)


def test_o_registro_de_servicos_inicia_e_encerra_uma_unica_vez():
    import services

    class Servico:
        def __init__(self):
            self.inicios = 0
            self.fins = 0

        def start(self, app):
            self.inicios += 1

        def stop(self, app):
            self.fins += 1

    um, dois = Servico(), Servico()
    services._servicos.extend([um, dois])
    try:
        services.iniciar_todos(None)
        services.iniciar_todos(None)
        assert (um.inicios, dois.inicios) == (1, 1)
        services.encerrar_todos(None)
        services.encerrar_todos(None)
        assert (um.fins, dois.fins) == (1, 1)
    finally:
        services._servicos.remove(um)
        services._servicos.remove(dois)
        services._iniciados.discard(id(um))
        services._iniciados.discard(id(dois))


def test_modo_demo_registra_so_o_painel():
    demo = create_app(_settings(db_uri="", demo=True))
    assert "vista_atualizador" in demo.extensions
    assert "vista_cotacoes" not in demo.extensions
    assert demo.config["VISTA_FONTE"] is showcase


# ---------------------------------------------------------------- item 2 e segurança
@pytest.mark.parametrize("opt,coluna", [
    ("GER", "cr.Gerente"),
    ("GR", "cr.GerenteRegional"),
    ("DIR", "cr.DiretorRegional"),
])
def test_a_whitelist_de_recorte_persiste(opt, coluna):
    """Item 2: os três recortes continuam sendo os únicos interpoláveis no SQL."""
    assert metricas.coluna_de_filtro(opt) == coluna


@pytest.mark.parametrize("injetado", [
    "cr.Gerente; DROP TABLE Tarefa", "1=1", "GR' OR '1'='1", "", None,
])
def test_fora_da_whitelist_nao_vira_sql(injetado):
    assert metricas.coluna_de_filtro(injetado) is None


@pytest.mark.parametrize("funcao,args", [
    ("tarefas_total", ()),
    ("tarefas_dia", ()),
    ("visitas_mes", ()),
    ("visitas_dia", ()),
    ("escalonadas", ()),
])
def test_os_filtros_de_negocio_continuam_no_sql(capture_sql, funcao, args):
    """Item 2: `Status = 85`, `Expirada = 0`, `Escalonado` e os checklists não mudaram."""
    getattr(metricas, funcao)(*("cr.GerenteRegional", "Parana Interior", *args))
    sql = capture_sql["sql"].upper()

    if funcao.startswith("visitas"):
        assert "CHECKLISTID IN" in sql
        # Os 5 checklists são parâmetros vinculados, não texto interpolado.
        valores = set(capture_sql["params"].values())
        assert len(valores & set(CHECKLISTS_VISITAS)) == 5
    if funcao.startswith("tarefas"):
        assert "EXPIRADA = 0" in sql
        assert "STATUS = 85" in sql
    if funcao == "escalonadas":
        assert "ESCALONADO" in sql


def test_nenhum_segredo_aparece_em_resposta_http(monkeypatch):
    """Segurança: token, SECRET e a URI do banco não vazam pela interface."""
    app = create_app(_settings(secret="SEGREDODEAPP", action_api="TOKENDEBRAPI"))
    cliente = app.test_client()
    corpos = [
        cliente.get("/").get_data(as_text=True),
        cliente.get("/actions/cotacoes/").get_data(as_text=True),
        cliente.get("/actions/value/").get_data(as_text=True),
    ]
    for segredo in ("SEGREDODEAPP", "TOKENDEBRAPI"):
        assert all(segredo not in corpo for corpo in corpos), segredo


def test_o_arquivo_de_ambiente_continua_fora_do_versionamento():
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[1]
    assert ".env" in (raiz / ".gitignore").read_text(encoding="utf-8").split()
