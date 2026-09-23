# ======================================================================
# IMPORTS
# ======================================================================
from gevent import monkey; monkey.patch_all() # SEMPRE EM PRIMEIRA INSTANCIA
from dotenv import load_dotenv; load_dotenv()
from flask import Flask, render_template
from utils.blueprints import bps
from flask_cors import CORS
from os import getenv
from utils.db import db

# ======================================================================
# CONFIGURAÇÕES
# ======================================================================
PORT = int(getenv('PORT', 8092))
HOST = getenv("HOST", "0.0.0.0")
DEBUG = getenv("DEBUG", "false").lower == "true" 

app = Flask(__name__)
CORS(app, allow_headers=["*"])
app.config["SECRET_KEY"] = getenv("SECRET")
app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DB_URI")

for bp, url_prefix in bps.items(): 
    app.register_blueprint(bp, url_prefix=url_prefix)

db.init_app(app)
with app.app_context(): 
    db.create_all()

# ======================================================================
# ROTAS
# ======================================================================
@app.route('/')
def home(): 
    return render_template('dash.html')

@app.route('/showcase')
def showcase(): 
    return render_template("Example.html")
    
if __name__ == '__main__': 
    app.run(host=HOST, port=PORT, debug=DEBUG)