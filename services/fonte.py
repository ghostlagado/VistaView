"""De onde o app atual puxa os indicadores.

Duas fontes possíveis, com as mesmas funções: `services.metricas` (o warehouse) e
`services.showcase` (demonstração sintética). A escolha é por app, no `create_app`, e
rotas e tempo real perguntam a mesma coisa — assim um dado sintético não consegue aparecer
numa consulta real, nem o contrário.
"""

from services import metricas


def indicadores(app=None):
    if app is None:
        from flask import current_app
        app = current_app
    return app.config.get("VISTA_FONTE", metricas)
