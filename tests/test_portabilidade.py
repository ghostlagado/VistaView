"""Uma consulta, dois bancos: o contrato de portabilidade e o painel real no SQLite.

A refactorização ORM existe para isto poder ser afirmado com evidência, e não com
intenção. Duas frentes:

1. **Compilação.** Toda folha é compilada para SQL Server e para SQLite, e as asserções
   são sobre as trocas de dialeto que o SQLAlchemy faz — `TOP` por `LIMIT`, `DATEPART` por
   `STRFTIME`, `WITH(NOLOCK)` só no primeiro. Se alguém escrever uma função de data que só
   um dos bancos tem, este arquivo para.
2. **Execução.** As mesmas folhas rodam contra um SQLite semeado por
   `services.semente`, e o painel é cobrado por coerência interna: a soma da série diária
   bate com o total do mês, o top 3 é o começo do ranking, e um recorte sem linhas devolve
   zero em vez de erro.

O caminho de SQL Server não pode ser executado aqui (não há instância na suíte), e é por
isso que a compilação é assinada separadamente: ela é a evidência disponível mais forte
de que os dois bancos recebem a mesma consulta.
"""

import datetime as real_dt

import pytest
from sqlalchemy.dialects import mssql, sqlite

from models import Cr, aplicar_esquema
from services import showcase
from services.metricas import IndicadoresWarehouse
from services.semente import semear
from utils.config import Settings
from utils.db import db

FOLHAS = (
    "tarefas_total", "tarefas_dia", "tarefas_mes_anterior", "visitas_mes", "visitas_dia",
    "escalonadas", "performance", "top3_unidades", "top3_sups", "gerentes", "unidades",
    "graph_days", "graph_days_ant",
)

CAMPO = Cr.gerente_regional
GR = "Parana Interior"
AGORA = real_dt.datetime(2026, 10, 20, 15, 30)


class Captor:
    """Executa de mentirinha: guarda a última consulta para ela ser compilada a seco."""

    def __init__(self):
        self.consultas = []

    def execute(self, statement, *args, **kwargs):
        self.consultas.append(statement)
        return type("R", (), {
            "scalar": lambda self: 0,
            "mappings": lambda self: type("A", (), {"all": lambda self: []})(),
        })()


def compilar(statement, dialect):
    return str(statement.compile(dialect=dialect,
                                 compile_kwargs={"literal_binds": True}))


@pytest.fixture()
def compilador():
    """Folha por folha, devolve `(sql do SQL Server, sql do SQLite)` da mesma consulta.

    O schema é pinado em `""` antes de cada rodada, porque a decisão é de processo, não de
    consulta: `aplicar_esquema` muda o `Table` compartilhado, e um teste anterior que o
    deixou como `dw_vista.dbo` mudaria o texto compilado aqui.
    """
    def rodar(nome):
        aplicar_esquema("")
        captor = Captor()
        folha = getattr(IndicadoresWarehouse(captor), nome)
        if nome == "escalonadas":
            folha(CAMPO, GR)
        else:
            folha(CAMPO, GR, AGORA)
        assert captor.consultas, f"{nome} não emitiu consulta"
        statement = captor.consultas[-1]
        return (compilar(statement, mssql.dialect()),
                compilar(statement, sqlite.dialect()))
    return rodar


# ------------------------------------------------------------------ 1. compilação
@pytest.mark.parametrize("folha", FOLHAS)
def test_a_mesma_consulta_compile_para_os_dois_bancos(compilador, folha):
    mssql_sql, sqlite_sql = compilador(folha)
    assert "FROM TAREFA" in mssql_sql.upper().replace("[", "").replace("]", "")
    # Os nomes físicos vêm do mapeamento, então a única diferença permitida é sintaxe.
    assert "DW_VISTA" not in mssql_sql  # sem schema: é o que o app configurou para SQLite
    assert sqlite_sql.strip()


@pytest.mark.parametrize("folha", FOLHAS)
def test_o_hint_de_leitura_so_existe_no_sql_server(compilador, folha):
    mssql_sql, sqlite_sql = compilador(folha)
    assert "WITH(NOLOCK)" in mssql_sql
    assert "NOLOCK" not in sqlite_sql


@pytest.mark.parametrize("folha", ["tarefas_dia", "tarefas_mes_anterior", "visitas_dia"])
def test_o_top_um_vira_limit_no_sqlite(compilador, folha):
    mssql_sql, sqlite_sql = compilador(folha)
    assert "TOP " in mssql_sql.upper()
    assert "LIMIT" in sqlite_sql.upper()


@pytest.mark.parametrize("folha", ["tarefas_total", "graph_days", "performance"])
def test_a_janela_de_calendario_usa_a_funcao_de_cada_banco(compilador, folha):
    mssql_sql, sqlite_sql = compilador(folha)
    assert "DATEPART(MONTH" in mssql_sql.upper()
    assert "strftime('%m'" in sqlite_sql.lower()
    assert "DATEPART" not in sqlite_sql.upper()
    assert "STRFTIME" not in mssql_sql.upper()


@pytest.mark.parametrize("folha", ["graph_days", "graph_days_ant"])
def test_a_serie_diaria_agrupa_por_dia_em_ambos(compilador, folha):
    mssql_sql, sqlite_sql = compilador(folha)
    assert "GROUP BY" in mssql_sql.upper() and "GROUP BY" in sqlite_sql.upper()
    assert "DATEPART(DAY" in mssql_sql.upper()
    assert "strftime('%d'" in sqlite_sql.lower()


def test_o_case_de_performance_compile_em_ambos(compilador):
    mssql_sql, sqlite_sql = compilador("performance")
    assert "CASE WHEN" in mssql_sql.upper() and "CASE WHEN" in sqlite_sql.upper()


def test_a_semente_recusa_um_banco_que_nao_seja_sqlite():
    with pytest.raises(RuntimeError, match="SQLite"):
        semear("mssql+pyodbc://usuario:senha@host:1433/dw_vista")


def test_o_prefixo_de_schema_e_do_processo_nao_do_dialeto(compilador):
    """Por que o app decide o schema uma vez, no `create_app`, e nunca por consulta.

    `Table.schema` é um atributo do mapeamento: posto `dw_vista.dbo`, ele aparece no SQL
    dos dois bancos — inclusive no SQLite, onde não existe schema cruzado e a consulta
    quebraria. Não há truque de dialeto aqui; o que há é a decisão certa no lugar certo
    (`Settings.from_env` só preenche `esquema` para URI `mssql`), e `validar()` recusa a
    combinação que não pode funcionar.
    """
    try:
        aplicar_esquema("dw_vista.dbo")
        captor = Captor()
        IndicadoresWarehouse(captor).tarefas_total(CAMPO, GR, AGORA)
        statement = captor.consultas[-1]
        mssql_sql = compilar(statement, mssql.dialect())
        sqlite_sql = compilar(statement, sqlite.dialect())
    finally:
        aplicar_esquema("")

    assert "dw_vista.dbo.[DM_ESTRUTURA]" in mssql_sql
    assert '"dw_vista.dbo"."DM_ESTRUTURA"' in sqlite_sql
    # E com o prefixo tirado — o estado do app em SQLite — os dois bancos voltam a
    # endereçar a tabela pelo nome simples.
    mssql_depois, sqlite_depois = compilador("tarefas_total")
    assert "dw_vista.dbo" not in mssql_depois and "dw_vista.dbo" not in sqlite_depois


def test_configurar_esquema_num_sqlite_e_recusado_na_partida():
    """Falha no boot é melhor que um painel de zeros mudos na TV."""
    from utils.config import Settings

    with pytest.raises(RuntimeError, match="VISTA_ESQUEMA"):
        Settings(host="h", port=1, debug=False, secret="s",
                 db_uri="sqlite:///x.sqlite3", default_opt="GR", default_gr="g",
                 esquema="dw_vista.dbo").validar()


# ------------------------------------------------------------------ 2. execução
@pytest.fixture(scope="module")
def painel_local(tmp_path_factory):
    """App real lendo de um SQLite semeado — o painel vindo do banco, não de um fake."""
    raiz = tmp_path_factory.mktemp("espelho")
    uri = f"sqlite:///{raiz / 'dw_vista.sqlite3'}"
    saida = semear(uri, hoje=AGORA.date())
    assert "populado" in saida

    config = Settings(host="127.0.0.1", port=8097, debug=False, secret="s",
                      db_uri=uri, default_opt="GR", default_gr=GR)
    from app import create_app
    aplicacao = create_app(config)
    with aplicacao.app_context():
        yield aplicacao, IndicadoresWarehouse(db.session).painel("GR", GR, AGORA)


def test_o_painel_real_vem_do_banco_semeado(painel_local):
    _, painel = painel_local
    assert painel["totalMes"] > 0
    assert painel["mesAnterior"] > 0
    assert painel["escalonadas"] > 0


def test_a_soma_da_serie_bate_com_a_consulta_de_mesma_janela(painel_local):
    _, painel = painel_local
    assert painel["dias"]["dia"] == list(range(1, AGORA.day + 1))
    # A série diária e o gráfico de performance compartilham a janela (recorte, mês,
    # não expirada) e nenhuma das duas filtra por status — herdado do SQL original. Já o
    # número grande do painel (`totalMes`) conta só as concluídas: a soma das barras é
    # maior que ele de propósito, e é isso que os dois asserts abaixo assinam.
    assert sum(painel["dias"]["total"]) == sum(painel["performance"]["total"])
    assert sum(painel["dias"]["total"]) >= painel["totalMes"]
    assert painel["dias"]["total"][-1] >= painel["totalDia"]
    # O mês anterior é cortado no mesmo dia de hoje: barras comparáveis.
    assert painel["diasAnt"]["dia"] == list(range(1, AGORA.day + 1))


def test_o_top3_e_o_comeco_do_ranking_de_unidades(painel_local):
    _, painel = painel_local
    assert painel["top3Uni"]["uni"] == painel["unidades"]["uni"][:3]
    assert painel["top3Uni"]["total"] == painel["unidades"]["total"][:3]
    assert len(painel["unidades"]["uni"]) == 12


def test_visitas_sao_subconjunto_das_tarefas_e_performance_fecha(painel_local):
    _, painel = painel_local
    assert 0 < painel["visitasMes"] <= painel["totalMes"]
    assert painel["visitasDia"] <= painel["visitasMes"]
    assert sum(painel["performance"]["total"]) >= painel["totalMes"]
    assert painel["performance"]["st"] == ["FORA DO PRAZO", "NO PRAZO"]


def test_o_recorte_filtra_de_verdade(painel_local):
    aplicacao, painel = painel_local
    ausente = IndicadoresWarehouse(db.session).painel("GR", "Regional Que Nao Existe", AGORA)
    assert all(ausente[chave] == 0 for chave in
               ("totalMes", "totalDia", "visitasMes", "visitasDia", "escalonadas"))
    assert ausente["unidades"]["uni"] == []
    # O recorte do próprio painel não é o de outra regional: os números diferem.
    outro = IndicadoresWarehouse(db.session).painel("GR", "Sao Paulo Capital", AGORA)
    assert outro["totalMes"] != painel["totalMes"]
    assert outro["totalMes"] > 0


def test_as_rotas_http_servem_o_mesmo_painel_do_banco(painel_local):
    aplicacao, painel = painel_local
    with aplicacao.test_client() as cliente:
        assert cliente.get(f"/tarefas/total/GR/{GR}").get_json() == painel["totalMes"]
        corpo = cliente.get(f"/get_unidades/GR/{GR}").get_json()
    assert corpo["uni"] == painel["unidades"]["uni"]


def test_a_fonte_de_demo_e_um_objeto_com_as_mesmas_folhas_do_warehouse():
    """A troca de fonte é por contrato: se faltar uma folha, o painel quebra na hora."""
    for nome in FOLHAS + ("painel", "coluna_de_filtro"):
        assert hasattr(showcase.INDICADORES, nome), nome
        assert hasattr(IndicadoresWarehouse, nome), nome
