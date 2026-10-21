# 📊 Vista View

<p align="center">
  <strong>Dashboard operacional do GPS Vista, feito para TV, atualizado em tempo real</strong>
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
* 📈 Cotações de até cinco ativos da B3

> Projeto desenvolvido para o **GPS Group**, com foco em acompanhamento, direcionamento e monitoramento das operações.

---

## 🖥️ Visão geral

O Vista View é uma camada de visualização sobre os dados do warehouse do GPS Vista. A tela
principal é um painel **16:9 sem rolagem**, pensado para ficar ligado em uma TV de gerência:
tipografia discreta com números tabulares, cores semânticas (verde/vermelho/âmbar) e
atualização empurrada pelo servidor por Socket.IO — a página não recarrega. A barra do topo
tem só o letreiro da marca, a regional, o relógio com segundos e um selo **Online/Offline**
que reflete o socket real; o rodapé faz as unidades desfilarem em movimento contínuo por CSS.

Um único ciclo no servidor recalcula o painel e transmite pelo socket apenas o que mudou. Se a
conexão não pegar, a mesma tela se remonta pelas requisições HTTP individuais.

![Vista View](https://github.com/user-attachments/assets/29acc152-ed30-446b-b85f-be4852b9aa88)

---

## 🚀 Tecnologias

| Tecnologia                     | Utilização                                     |
| ------------------------------ | ---------------------------------------------- |
| 🐍 **Python**                  | Linguagem principal                            |
| 🌶️ **Flask**                  | Aplicação Web e os blueprints de rota          |
| 🗃️ **SQLAlchemy 2 (ORM)**    | Modelos em `models/` e consultas portáveis entre SQL Server e SQLite |
| 🟢 **Gevent**                  | Concorrência, ciclos em segundo plano          |
| 🔌 **Flask-SocketIO**          | Snapshot e deltas em tempo real                |
| 📊 **Chart.js**                | Gráfico de realizado por dia e de desempenho   |
| 🌐 **Flask-CORS**              | Controle de requisições CORS                   |
| 🔐 **python-dotenv**           | Configuração através de `.env`                 |
| 🧪 **pytest**                  | 231 testes de contrato, cálculo, portabilidade e regressão |

---

## 📁 Estrutura do projeto

```text
VistaView/
│
├── app.py                 # app factory: configuração, fontes de dado e ciclos
├── wsgi.py                # entrada de produção (inicia e encerra os serviços)
│
├── models/                # espelho de leitura do warehouse, em ORM (só leitura)
│   ├── base.py            #   ModeloBase + aplicar_esquema (o schema por banco)
│   ├── tarefa.py          #   TAREFA: status, expirada, escalonada, checklist
│   ├── recurso.py         #   RECURSO: quem fechou a tarefa
│   ├── estrutura.py       #   DM_ESTRUTURA: a unidade e a ponte para a cadeia
│   └── cr.py              #   DM_CR: a cadeia de comando, dona do recorte
│
├── routes/                # camada HTTP: só valida o recorte e serializa
│   ├── acoes.py           #   /actions/value/ e /actions/cotacoes/ (leem cache)
│   ├── general.py         #   desempenho, rankings, unidades, gráficos
│   ├── tarefas.py         #   totais, meta do mês anterior, escalonadas
│   └── visitas.py         #   visitas do mês e do dia
│
├── services/              # regras de cálculo e processos em segundo plano
│   ├── metricas.py        #   IndicadoresWarehouse: as 13 folhas, em ORM
│   ├── showcase.py        #   IndicadoresDemonstracao: as mesmas folhas, sintéticas
│   ├── semente.py         #   popula o SQLite local (nunca o warehouse)
│   ├── fonte.py           #   costura que escolhe a fonte por configuração
│   ├── cotacoes.py        #   UM ciclo que consulta o provedor; todos leem o cache
│   └── realtime.py        #   AtualizadorPainel, diff e handlers do Socket.IO
│
├── utils/
│   ├── config.py          # Settings: o único ponto que lê o ambiente
│   ├── db.py, socket.py, blueprints.py
│
├── templates/
│   ├── dash.html          # painel 16:9
│   └── Example.html       # referência visual antiga (/showcase)
│
├── static/
│   ├── css/painel.css
│   ├── js/painel.js       # único desenhador da tela
│   ├── js/tempo-real.js   # socket, reconexão e recarga de último recurso
│   └── img/
│
├── tests/                 # contratos, cálculos, janelas de data, demo, cotações, regressão
├── docs/                  # auditoria, decisões, modo demo e cotações
│
├── .env.example
├── requirements.txt
└── requirements-dev.txt
```

---

## ⚙️ Configuração

A aplicação lê tudo do ambiente por um único objeto (`utils/config.py`), que valida os
valores e falha na subida com mensagem acionável — em vez de um `RuntimeError` de framework
no meio do atendimento.

Crie um arquivo `.env` baseado no arquivo disponibilizado no projeto:

```bash
cp .env.example .env
```

No Windows:

```powershell
copy .env.example .env
```

### Configurações

| Variável                 | Descrição                                                              | Padrão             |
| ------------------------ | ---------------------------------------------------------------------- | ------------------ |
| `HOST`                   | Host de execução                                                       | `0.0.0.0`          |
| `PORT`                   | Porta da aplicação                                                     | `8092`             |
| `DEBUG`                  | Modo debug                                                             | `false`            |
| `SECRET`                 | Chave de sessão do Flask                                               | no demo é gerada; fora do demo, obrigatória |
| `DB_URI`                 | URI SQLAlchemy do banco. **Opcional**: sem ela o painel lê do espelho SQLite local | `instance/dw_vista_local.sqlite3` |
| `VISTA_ESQUEMA`          | Prefixo das tabelas de estrutura no SQL Server       | `dw_vista.dbo` quando a URI é `mssql` |
| `DEFAULT_OPT`            | Recorte padrão: `GER`, `GR` ou `DIR`                                   | `GR`               |
| `DEFAULT_GR`             | Regional exibida por padrão                                            | `Parana Interior`  |
| `META_PERCENTUAL`        | Crescimento sobre o mês anterior usado no cálculo da meta             | `15`               |
| `ATUALIZACAO_SEGUNDOS`   | Ciclo do painel em tempo real (mínimo 15)                              | `60`               |
| `ACTION_API`             | Token da brapi.dev (cadastro gratuito)                                 | —                  |
| `COTACOES_SIMBOLOS`      | Até 5 ativos da B3, separados por vírgula                              | `GGPS3`            |
| `COTACOES_SEGUNDOS`      | Ciclo que consulta o provedor (mínimo 60)                              | `300`              |
| `COTACOES_VELHO_MIN`     | Idade a partir da qual a cotação aparece marcada como desatualizada    | `15`               |
| `MODO_DEMO`              | Painel com dados sintéticos, sem banco e sem API externa               | `false`            |

### Bancos suportados

Os modelos são um espelho de leitura, e a mesma consulta compila para os dois bancos:

| Banco         | Como ativar                          | O que muda                                                        |
| ------------- | ------------------------------------ | ----------------------------------------------------------------- |
| **SQLite**    | nada — é o padrão                    | arquivo local `instance/dw_vista_local.sqlite3`, sem servidor      |
| **SQL Server**| `DB_URI=mssql+pyodbc://...`          | tabelas de estrutura em `dw_vista.dbo` e leitura com `WITH(NOLOCK)`|

As diferenças de dialeto são feitas pelo SQLAlchemy — `TOP 1`/`LIMIT 1`,
`DATEPART(month, …)`/`CAST(STRFTIME('%m', …) AS INTEGER)` — e o hint de leitura é aplicado
só no SQL Server, onde ele existe. `tests/test_portabilidade.py` assina isso consulta por
consulta.

O SQLite é o caminho de desenvolvimento e de demonstração com dados reais; para ele existir
conteúdo, popula-se o espelho com:

```bash
python -m services.semente            # cria o schema e insere os dados
python -m services.semente --limpar   # refaz do zero
```

O comando **recusa** qualquer URI que não seja SQLite: o warehouse é lido, nunca escrito.

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

Para rodar os testes:

```bash
pip install -r requirements-dev.txt
```

Configure o `.env`:

```bash
cp .env.example .env
```

---

## ▶️ Execução

Sem `DB_URI` e sem `MODO_DEMO`, o painel lê do SQLite local. Se o arquivo ainda não existe
ou está vazio, o boot avisa no log — é o caso de quem acabou de clonar:

```bash
python -m services.semente    # popula instance/dw_vista_local.sqlite3
python wsgi.py
```

O `wsgi.py` sobe o servidor Socket.IO, inicia os ciclos em segundo plano (painel e
cotações) e os encerra de forma ordenada em `SIGINT`/`SIGTERM`. A aplicação será iniciada,
por padrão, em `http://localhost:8092`.

`python app.py` faz o mesmo em primeiro plano e é o atalho de desenvolvimento.

> Os ciclos precisam rodar no mesmo processo do servidor. Um servidor WSGI com vários
> workers multiplicaria os ciclos — e as cotações, que têm cota mensal. Para produção com
> gestor de processos, use um worker único com gevent ou separe o ciclo em processo próprio.

Rotas:

| Rota              | O que entrega                                          |
| ----------------- | ------------------------------------------------------ |
| `/`               | painel 16:9                                            |
| `/showcase`       | referência visual antiga (estática, sem dados)         |
| `/<indicador>/<opt>/<gr>` | os 13 endpoints JSON de indicador            |
| `/actions/cotacoes/` | faixa de cotações lida do cache                     |
| `/actions/value/` | valor do primeiro ativo (contrato antigo)              |

---

## 🧩 Arquitetura

Uma camada por responsabilidade, com uma decisão explícita em cada uma:

* **`models/`** é o espelho de leitura do warehouse: `Tarefa`, `Recurso`, `Estrutura` e `Cr`.
  Nenhuma escreve — não há `ForeignKey` físico declarado, os relacionamentos são `viewonly`
  e as chaves primárias existem só para o mapeamento identificador funcionar. É aqui que
  moram os nomes físicos das colunas (`NOME`, `TerminoReal`, `CODIGOHASH`) e as regras de
  status (`STATUS_CONCLUIDA = 85`, `STATUS_ABERTAS = (25, 10, 70)`).
* **`services/metricas.py`** (`IndicadoresWarehouse`) monta as 13 consultas a partir dos
  modelos. Não há uma linha de SQL em texto: o recorte vira a coluna mapeada escolhida por
  `Cr.coluna_do_recorte`, e um valor fora da whitelist `GER/GR/DIR` não produz string
  nenhuma para interpolar.
* **`routes/`** não calcula nada. Valida o recorte (fora da whitelist, 400) e serializa o
  que os serviços devolvem.
* **`services/`** também guarda os ciclos, sem dependência de Flask. A fonte dos
  indicadores é escolhida uma vez, em `create_app` (`app.config["VISTA_FONTE"]`), e é a
  mesma para as rotas e para o tempo real — por isso um dado sintético nunca vaza para uma
  consulta real, nem o contrário.
* **`utils/config.py`** é o único ponto que lê variáveis de ambiente.

O `WITH(NOLOCK)` do SQL original continua existindo, como hint restrito ao dialeto
`mssql` (`services/metricas.py::_com_hint`): no SQLite ele seria sintaxe inválida, e no
SQL Server continua significando "leitura que não espera lock".

---

## 📡 Tempo real

| Evento               | Direção          | Conteúdo                                                  |
| -------------------- | ---------------- | --------------------------------------------------------- |
| `dashboard:snapshot` | servidor → cliente | painel completo do recorte, para quem acabou de conectar |
| `dashboard:update`   | servidor → clientes | só o que mudou desde a rodada anterior                 |
| `dashboard:status`   | servidor → clientes | fonte do ciclo, degradação, falhas consecutivas, horário |
| `dashboard:solicitar` | cliente → servidor | pede o snapshot de novo (usado no carregamento)          |

Sem o socket, a tela cai em "modo consulta" e se remonta pelas rotas HTTP; se o Socket.IO
desistir de reconectar por cinco minutos, a TV recarrega a página.

---

## 🎭 Modo demonstração

```bash
MODO_DEMO=true python wsgi.py
```

Uma linha só basta: em demonstração o processo gera uma chave de sessão descartável e não
consulta banco nem provedor. Abre o painel com dados sintéticos determinísticos, sem warehouse
e sem API de cotações. As rotas, o cálculo da meta e os eventos são os mesmos do modo real. O
modo não ganha mais um selo na tela — o pedido de navbar limpa eliminou o badge âmbar — mas
continua registrado no DOM (`<body data-modo="demo">`) e no `dashboard:status`, cujo campo
`fonte` vem como `demo`. Detalhes e o trade-off em
[`docs/modo-demo.md`](docs/modo-demo.md).

---

## 📈 Cotações

Um único greenlet consulta a brapi.dev — uma requisição por ciclo, com os até cinco ativos
de `COTACOES_SIMBOLOS` na mesma chamada — e o painel inteiro lê o cache dele. A tela mostra
preço, variação, hora da cotação e marca em âmbar quando ela envelhece; sem resposta,
mostra `—` em vez de inventar zero. A comparação de provedores gratuitos que justificou a
escolha, com os números medidos, está em [`docs/cotacoes.md`](docs/cotacoes.md).

---

## 🧪 Testes

```bash
python -m pytest -q
```

231 testes, sem nenhuma saída de rede: as rotas são exercitadas com a camada de execução do
SQLAlchemy interceptada e o provedor de cotações, com uma sessão HTTP falsa. Cobrem o
contrato de cada rota (path, método e forma de resposta), os filtros de negócio na consulta
compilada, as janelas de data, a **portabilidade** (cada uma das 13 folhas compilada para SQL
Server e SQLite, e o painel inteiro executado contra um SQLite semeado), o diff do tempo
real, o isolamento do modo demo, os limites e o backoff das cotações, o layout do painel
(faixa contínua, selo único, relógio com segundos, números −2px, sem rolagem) e os seis
critérios de aceitação anti-regressão de
[`docs/auditoria-e-baseline.md`](docs/auditoria-e-baseline.md).

---

## 📚 Documentação

| Arquivo                                     | Conteúdo                                        |
| ------------------------------------------- | ----------------------------------------------- |
| [`CONTRIBUTING.md`](CONTRIBUTING.md)         | como rodar, testar e propor mudança neste código |
| [`SECURITY.md`](SECURITY.md)                 | o que é sensível, como reportar e o modelo de ameaça |
| [`docs/arquitetura.md`](docs/arquitetura.md) | modelos, fontes de dado e as trocas de dialeto   |
| [`docs/auditoria-e-baseline.md`](docs/auditoria-e-baseline.md) | o que o código era antes, com os problemas encontrados e a baseline de testes |
| [`docs/decisoes-tecnicas.md`](docs/decisoes-tecnicas.md)       | por que cada decisão foi tomada, fase a fase    |
| [`docs/modo-demo.md`](docs/modo-demo.md)                       | demonstração, isolamento e auditoria do Showcase |
| [`docs/cotacoes.md`](docs/cotacoes.md)                         | comparação de provedores e o que foi validado    |

---

## 🌐 CORS

O projeto possui suporte a CORS através do Flask-CORS:

```python
CORS(app, allow_headers=["*"])
```

Isso permite que a aplicação aceite requisições provenientes de diferentes origens, conforme a configuração atual do projeto.

---

## ⚡ Gevent

O monkey patch é aplicado na primeira linha de `app.py`, antes de qualquer import que faça
I/O:

```python
from gevent import monkey
monkey.patch_all()  # SEMPRE EM PRIMEIRA INSTANCIA
```

Quem sobe a aplicação por outra porta (um servidor WSGI próprio, por exemplo) precisa
manter essa ordem — importar `urllib3` antes do patch produz `RecursionError` em requisições
HTTPS, inclusive as de cotação.

---

## 🔐 Segurança

Resumo: `.env` nunca vai para o repositório (só `.env.example` é versionado), o token da
brapi é lido apenas no processo do servidor e não aparece em resposta HTTP nem em log de
erro, o recorte `GER/GR/DIR` é uma whitelist que devolve coluna mapeada — não texto — e o
modo demonstração não alcança o banco nem o provedor. Cada uma dessas garantias tem teste.

O modelo de ameaça, a lista do que é sensível e como reportar uma vulnerabilidade estão em
[`SECURITY.md`](SECURITY.md).
