# ======================================================================
# IMPORTS
# ======================================================================
from gevent import monkey; monkey.patch_all() # SEMPRE EM PRIMEIRA INSTANCIA
from dotenv import load_dotenv; load_dotenv()
from flask import Flask, render_template
from utils.socket import criar_socketio
from utils.blueprints import bps
from flask_cors import CORS
from utils.config import SETTINGS
from utils.db import db
from services import metricas, showcase
from services.cotacoes import AtualizadorCotacoes, normalizar_simbolos
from services.realtime import AtualizadorPainel, registrar_handlers
import services

# ======================================================================
# APLICAÇÃO
# ======================================================================
def create_app(settings=SETTINGS):
    settings.validar()

    app = Flask(__name__)
    CORS(app, allow_headers=["*"])
    app.config["SECRET_KEY"] = settings.secret
    # Em demonstração nada consulta o banco, mas o SQLAlchemy exige uma URI para iniciar.
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.db_uri or "sqlite:///:memory:"
    app.config["DEFAULT_GR"] = settings.default_gr
    app.config["DEFAULT_OPT"] = settings.default_opt
    app.config["META_PERCENTUAL"] = settings.meta_percentual
    app.config["MODO_DEMO"] = settings.demo

    for bp, url_prefix in bps.items():
        app.register_blueprint(bp, url_prefix=url_prefix)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Única decisão sobre de onde vêm os indicadores: rotas e tempo real usam o mesmo.
    indicadores = showcase if settings.demo else metricas
    app.config["VISTA_FONTE"] = indicadores

    # Única decisão sobre de onde vêm as cotações. Em demonstração a faixa é sintética,
    # então nenhuma requisição sai para o provedor; no modo real um único greenlet é o
    # cliente da API e todos os leitores pegam o cache.
    if settings.demo:
        cotar = showcase.cotacoes
    else:
        atualizador_cotacoes = AtualizadorCotacoes(
            simbolos=normalizar_simbolos(settings.cotacoes_simbolos),
            token=settings.action_api,
            intervalo=settings.cotacoes_segundos,
            velho_depois_min=settings.cotacoes_velho_min,
        )
        app.extensions["vista_cotacoes"] = atualizador_cotacoes
        services.registrar(atualizador_cotacoes)
        cotar = atualizador_cotacoes.cotacoes
    app.config["VISTA_COTACOES"] = cotar

    def calcular_painel(opt, gr, agora=None, meta_percentual=None):
        """As cifras do recorte mais a faixa de cotações, sempre lida do cache."""
        dados = indicadores.painel(opt, gr, agora, meta_percentual)
        dados["cotacoes"] = cotar()
        return dados

    # Uma instância por app (ver utils/socket.py).
    socketio = criar_socketio()
    socketio.init_app(app)
    app.extensions["vista_socketio"] = socketio

    atualizador = AtualizadorPainel(
        socketio,
        recorte=(settings.default_opt, settings.default_gr),
        intervalo=settings.atualizacao_segundos,
        calcular=calcular_painel,
        nome_ciclo="demo" if settings.demo else "painel",
    )
    app.extensions["vista_atualizador"] = atualizador
    registrar_handlers(socketio)
    services.registrar(atualizador)

    @app.route('/')
    def home():
        return render_template(
            'dash.html',
            gr=app.config["DEFAULT_GR"],
            opt=app.config["DEFAULT_OPT"],
            meta_percentual=app.config["META_PERCENTUAL"],
            demo=settings.demo,
        )

    @app.route('/showcase')
    def vitrine():
        return render_template("Example.html")

    return app


app = create_app()
socketio = app.extensions["vista_socketio"]
HOST = SETTINGS.host
PORT = SETTINGS.port
DEBUG = SETTINGS.debug

if __name__ == '__main__':
    services.iniciar_todos(app)
    try:
        socketio.run(app, host=HOST, port=PORT, debug=DEBUG, allow_unsafe_werkzeug=True)
    finally:
        services.encerrar_todos(app)
