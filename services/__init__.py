"""Serviços em segundo plano do Vista View.

Cada serviço implementa `start(app)` e `stop(app)`. O registro garante que um serviço
seja iniciado uma única vez (o reloader do Flask importa o app mais de uma vez) e
encerrado de forma ordenada no desligamento.
"""

_servicos = []
_iniciados = set()


def registrar(servico) -> None:
    if servico not in _servicos:
        _servicos.append(servico)


def iniciar_todos(app) -> None:
    for servico in _servicos:
        if id(servico) in _iniciados:
            continue
        servico.start(app)
        _iniciados.add(id(servico))


def encerrar_todos(app) -> None:
    for servico in reversed(_servicos):
        if id(servico) not in _iniciados:
            continue
        _iniciados.discard(id(servico))
        try:
            servico.stop(app)
        except Exception:
            app.logger.exception("falha ao encerrar %s", type(servico).__name__)
