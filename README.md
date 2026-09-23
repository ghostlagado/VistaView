# 📊 Vista View

<p align="center">
  <strong>Dashboard de monitoramento, métricas e metas para o GPS Vista</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Flask-Web%20Framework-000000?style=for-the-badge&logo=flask&logoColor=white">
  <img src="https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white">
  <img src="https://img.shields.io/badge/Ge­vent-Concurrent%20I%2FO-00A86B?style=for-the-badge">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge">
</p>

---

## 📌 Sobre o projeto

O **Vista View** é um dashboard desenvolvido para centralizar a visualização e o acompanhamento de informações do **GPS Vista**.

O projeto foi desenvolvido para apoiar o monitoramento operacional e gerencial, permitindo acompanhar informações relacionadas a:

* 📈 Métricas
* 🎯 Metas personalizadas
* 📅 Monitoramentos diários
* 📆 Monitoramentos mensais
* 📊 Gaps
* 👀 Visitas
* 🔎 Indicadores para acompanhamento de resultados

> Projeto desenvolvido para o **GPS Group**, com foco em acompanhamento, direcionamento e monitoramento das operações.

---

## 🖥️ Visão geral

O Vista View foi pensado como uma camada de visualização sobre os dados utilizados no acompanhamento do GPS Vista.

A aplicação disponibiliza uma interface web para centralizar as informações e facilitar a análise dos indicadores.

![Vista View](https://github.com/user-attachments/assets/29acc152-ed30-446b-b85f-be4852b9aa88)

---

## 🚀 Tecnologias

O projeto utiliza principalmente:

| Tecnologia                     | Utilização                          |
| ------------------------------ | ----------------------------------- |
| 🐍 **Python**                  | Linguagem principal                 |
| 🌶️ **Flask**                  | Aplicação Web                       |
| 🗃️ **SQLAlchemy**             | ORM e acesso ao banco               |
| 🟢 **Gevent**                  | Concorrência e execução do servidor |
| 🌐 **Flask-CORS**              | Controle de requisições CORS        |
| 🔐 **python-dotenv**           | Configuração através de `.env`      |
| 🎨 **HTML / CSS / JavaScript** | Interface da aplicação              |

---

## 📁 Estrutura do projeto

```text
VistaVIew/
│
├── routes/
│   └── ...
│
├── static/
│   └── ...
│
├── svgs/
│   └── ...
│
├── templates/
│   ├── dash.html
│   ├── Example.html
│   └── ...
│
├── utils/
│   ├── blueprints/
│   ├── db/
│   └── ...
│
├── .env.example
├── .gitattributes
├── .gitignore
├── LICENSE
├── README.md
├── app.py
├── requirements.txt
└── wsgi.py
```

---

## ⚙️ Configuração

O projeto utiliza variáveis de ambiente para configurar a aplicação.

Crie um arquivo `.env` baseado no arquivo disponibilizado no projeto:

```bash
cp .env.example .env
```

No Windows:

```powershell
copy .env.example .env
```

### Variáveis utilizadas

A aplicação utiliza as seguintes configurações:

```env
HOST=0.0.0.0
PORT=8092
DEBUG=false
SECRET=your-secret
DB_URI=your-database-uri
```

### Configurações

| Variável | Descrição                  | Padrão    |
| -------- | -------------------------- | --------- |
| `HOST`   | Host de execução           | `0.0.0.0` |
| `PORT`   | Porta da aplicação         | `8092`    |
| `DEBUG`  | Modo debug                 | `false`   |
| `SECRET` | Chave secreta do Flask     | —         |
| `DB_URI` | URI de conexão com o banco | —         |

---

## 📦 Instalação

Clone o projeto:

```bash
git clone https://github.com/foxtec198/VistaVIew.git
```

Entre no diretório:

```bash
cd VistaVIew
```

Crie um ambiente virtual:

```bash
python -m venv venv
```

### Windows

```powershell
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Configure o `.env`:

```bash
cp .env.example .env
```

Por fim, execute a aplicação:

```bash
python app.py
```

A aplicação será iniciada, por padrão, na porta:

```text
8092
```

---

## ▶️ Execução

A aplicação possui uma rota principal:

```text
/
```

que renderiza:

```text
templates/dash.html
```

Também existe uma rota de demonstração:

```text
/showcase
```

que renderiza:

```text
templates/Example.html
```

---

## 🧩 Arquitetura

A aplicação utiliza uma arquitetura baseada em **Flask Blueprints**.

Os blueprints são carregados através de:

```python
from utils.blueprints import bps
```

e registrados automaticamente:

```python
for bp, url_prefix in bps.items():
    app.register_blueprint(bp, url_prefix=url_prefix)
```

Isso permite manter as diferentes áreas da aplicação separadas em módulos dentro de `routes/`.

---

## 🗄️ Banco de dados

O acesso ao banco é realizado utilizando **SQLAlchemy**.

A URI de conexão é definida através da variável:

```env
DB_URI
```

e inicializada na aplicação:

```python
app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DB_URI")
```

O objeto de banco é inicializado através de:

```python
db.init_app(app)
```

Durante a inicialização da aplicação, as tabelas são criadas através de:

```python
with app.app_context():
    db.create_all()
```

---

## 🌐 CORS

O projeto possui suporte a CORS através do Flask-CORS:

```python
CORS(app, allow_headers=["*"])
```

Isso permite que a aplicação aceite requisições provenientes de diferentes origens, conforme a configuração atual do projeto.

---

## ⚡ Gevent

O projeto utiliza Gevent e aplica o monkey patch logo no início da aplicação:

```python
from gevent import monkey
monkey.patch_all()
```

A aplicação deve manter essa inicialização antes das demais importações que dependam de operações de I/O concorrentes.

---

## 🏗️ WSGI

O projeto também possui um arquivo:

```text
wsgi.py
```

destinado à execução da aplicação através de servidores WSGI.

Para ambientes de produção, recomenda-se utilizar um servidor WSGI/worker apropriado em vez do servidor de desenvolvimento do Flask.

---

## 🔐 Segurança
Não versione informações sensíveis no repositório.

O arquivo:

```text
.env
```

deve permanecer fora do controle de versão.

Utilize:

```text
.env.example
```

para documentar as variáveis necessárias sem expor credenciais.
