"""Configuração central e ciclo de vida dos serviços em segundo plano."""

import pytest

import services
from app import create_app
from utils.config import Settings, _flag


def _settings(**over):
    base = dict(
        host="127.0.0.1", port=8092, debug=False, secret="s",
        db_uri="sqlite:///:memory:", default_opt="GR", default_gr="Parana Interior",
    )
    base.update(over)
    return Settings(**base)


@pytest.mark.parametrize("valor,esperado", [
    ("true", True), ("TRUE", True), ("1", True), ("yes", True), ("on", True),
    ("false", False), ("0", False), ("", False), ("nonsense", False), (" True ", True),
])
def test_debug_e_interpretado_como_valor(monkeypatch, valor, esperado):
    monkeypatch.setenv("DEBUG", valor)
    assert Settings.from_env().debug is esperado


def test_valores_de_escada_tem_padrao_seguro(monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    env = Settings.from_env()
    assert env.debug is False
    assert env.host == "0.0.0.0"
    monkeypatch.setenv("PORT", "80x2")
    assert Settings.from_env().port == 8092
    assert _flag("PORT") is False


@pytest.mark.parametrize("campo,valor", [
    ("db_uri", ""), ("secret", ""), ("default_opt", "NAO_EXISTE"),
])
def test_configuracao_invalida_falha_com_mensagem_acionavel(campo, valor):
    with pytest.raises(RuntimeError) as err:
        _settings(**{campo: valor}).validar()
    assert campo in str(err.value).lower()


def test_configuracao_valida_passa_silenciosa():
    assert _settings().validar() is None


def test_create_app_expoe_o_recorte_padrao_para_o_template():
    with create_app(_settings()).test_client() as c:
        html = c.get("/").get_data(as_text=True)
    assert 'data-gr="Parana Interior"' in html
    assert 'data-opt="GR"' in html
    assert 'data-meta="15.0"' in html


def test_create_app_recusa_configuracao_incompleta():
    with pytest.raises(RuntimeError):
        create_app(_settings(db_uri=""))


class Contador:
    def __init__(self):
        self.starts = 0
        self.stops = 0

    def start(self, app):
        self.starts += 1

    def stop(self, app):
        self.stops += 1


class Explosivo:
    def start(self, app):
        raise RuntimeError("subiu quebrado")

    def stop(self, app):
        raise RuntimeError("falhou ao parar")


@pytest.fixture()
def registro_limpo():
    guardado = (list(services._servicos), set(services._iniciados))
    services._servicos.clear()
    services._iniciados.clear()
    yield
    services._servicos, services._iniciados = guardado


def test_servico_inicia_uma_unica_vez(registro_limpo, app):
    s = Contador()
    services.registrar(s)
    services.iniciar_todos(app)
    services.iniciar_todos(app)
    assert s.starts == 1


def test_registrar_duas_vezes_o_mesmo_servico_nao_duplica(registro_limpo, app):
    s = Contador()
    services.registrar(s)
    services.registrar(s)
    services.iniciar_todos(app)
    assert s.starts == 1


def test_encerramento_e_ordenado_e_repetivel(registro_limpo, app):
    a, b = Contador(), Contador()
    services.registrar(a)
    services.registrar(b)
    services.iniciar_todos(app)
    services.encerrar_todos(app)
    services.encerrar_todos(app)
    assert (a.stops, b.stops) == (1, 1)


def test_servico_que_nao_subiu_nao_e_encerrado(registro_limpo, app):
    s = Contador()
    services.registrar(s)
    services.encerrar_todos(app)
    assert s.stops == 0


def test_falha_na_subida_do_servico_e_explicita(registro_limpo, app):
    services.registrar(Explosivo())
    services.registrar(Contador())
    with pytest.raises(RuntimeError):
        services.iniciar_todos(app)


def test_falha_no_encerramento_nao_derruba_o_processo(registro_limpo, app):
    ruins = Explosivo()
    services.registrar(ruins)
    services._iniciados.add(id(ruins))
    services.encerrar_todos(app)


def test_sinal_de_desligamento_encerra_os_servicos(registro_limpo, app):
    import wsgi

    s = Contador()
    services.registrar(s)
    services.iniciar_todos(app)

    with pytest.raises(SystemExit) as exito:
        wsgi._encerrar(15, None)
    assert exito.value.code == 0
    assert s.stops == 1
