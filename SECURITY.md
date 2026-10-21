# Segurança

O Vista View é um painel de leitura exposto numa rede de gerência, com um repositório
público. Este documento diz o que é sensível aqui, como o código protege cada ponto, e o que
fazer se algo escapar.

## O que é sensível neste projeto

| Item | Onde vive | Nunca vai para |
| ---- | --------- | -------------- |
| `DB_URI` com usuário e senha do warehouse | `.env` (local) | commit, resposta HTTP, log, issue pública |
| `SECRET` (chave de sessão do Flask) | `.env` (local) | idem |
| `ACTION_API` (token da brapi.dev) | `.env` (local) | idem |
| Números operacionais do GPS Vista (tarefas, visitas, ranking de pessoas) | banco de origem | demonstração, screenshot de PR, issue |

O `.gitignore` cobre `.env` e `instance/` — o espelho SQLite local fica fora do
versionamento exatamente porque ele pode acabar com dado real dentro. Só `.env.example` é
versionado, e ele não contém segredo nenhum: os valores de exemplo são texto inválido de
propósito (`seu-token-da-brapi`, `troque-esta-chave`).

## Como o código protege

**Injeção de SQL.** O único ponto que já interpolou entrada do URL no texto da consulta era
a escolha da coluna de recorte (`GER`/`GR`/`DIR`). Hoje `Cr.coluna_do_recorte` devolve a
coluna **mapeada** correspondente, ou `None`, e um `None` vira HTTP 400 antes de qualquer
consulta. Não existe mais caminho por onde texto do usuário chegue ao SQL: toda consulta é
montada pelo SQLAlchemy a partir de `models/`, e todo valor (recorte, checklist, mês, dia)
entra como bind parameter. `tests/test_regressao.py` e `tests/test_calculos.py` assinam isso
com entradas de tentativa de injeção.

**Escrita acidental no warehouse.** Os modelos são espelho de leitura: nenhum `ForeignKey`
físico, todos os relacionamentos `viewonly`, nenhuma chamada de `add`/`insert`/`update`/
`delete` em `services/` ou `models/`. O `create_all()` do boot roda **somente** quando a URI
é SQLite, e o comando de semente (`services/semente.py`) levanta erro se apontarem ele para
um banco que não seja SQLite.

**Vazamento por interface.** O token do provedor e a chave de sessão não aparecem em resposta
HTTP nem em log de erro — há teste cobrindo as três rotas públicas. As rotas de indicador
são `GET` e não devolvem nada além do payload do painel.

**Sessão em demonstração.** Com `MODO_DEMO=true` e `SECRET` ausente, o processo gera uma
chave aleatória descartável (`secrets.token_hex(32)`) em vez de um valor padrão fixo no
código. Fora da demonstração a chave continua obrigatória no ambiente: sem ela o app não
sobe.

**Frontend.** O painel não renderiza HTML de origem externa: os nomes vêm do banco e entram
no DOM como `textContent`, e o CSS é estático. Não há `eval`, nem construção de URL a partir
de dado do painel.

## Superfície exposta e o que ainda não está resolvido

Assumir isso é parte da segurança; fingir que não existe não protege ninguém.

* **Sem autenticação.** Qualquer host que alcance a porta lê o painel. O projeto é pensado
  para rede interna de gerência; em rede exposta, a barreira precisa ser reversi/proxy ou
  firewall na frente — não está no código.
* **CORS aberto** (`allow_headers=["*"]`). É o comportamento herdado do projeto original;
  não permite ler segredo nenhum (as rotas não pedem credencial), mas permite que qualquer
  origem consuma o painel. Restringir `origins` é uma mudança com efeito em quem consome
  hoje — abra uma issue antes.
* **Socket.IO sem namespace autenticado.** O snapshot vai para quem conectar. Mesma
  implicação do item anterior.
* **Dados pessoais nominais.** Rankings mostram nome de gerente, supervisor e unidade. Não é
  segredo técnico, mas é dado interno de RH: trate screenshot e issue com cautela.
* **Werkzeug em desenvolvimento.** `app.py` usa `allow_unsafe_werkzeug=True` de propósito,
  porque é o atalho de desenvolvimento. Produção é `wsgi.py` atrás de servidor próprio.

## Reportando uma vulnerabilidade

Não abra issue pública com detalhe explorável — este repositório é público e o painel roda em
rede interna.

1. Use **"Report a vulnerability"** na aba Security do repositório no GitHub (advisory
   privado), se habilitado.
2. Se não estiver, abra uma issue apenas com o título `security: <resumo sem detalhe>` e
   aguarde o mantenedor pedir os detalhes por canal privado.
3. Inclua, quando souber: versão/commit, modo (`MODO_DEMO`, `DB_URI`), o que é exposto e como
   reproduzir. **Nunca** cole token, URI com credencial ou dado real de gerência.

Trabalhamos para responder em até 5 dias úteis. Correção de vulnerabilidade tem prioridade
sobre feature: se a escolha for entre lançar um indicador e fechar um vazamento, fecha-se o
vazamento.

## Dependências

`requirements.txt` fixa as versões usadas e validadas. Ao atualizar:

```bash
pip install -U -r requirements.txt   # em venv limpo
python -m pytest -q
```

Verifique especialmente SQLAlchemy (o contrato de portabilidade em
`tests/test_portabilidade.py` é quem avisa se um dialeto mudou de comportamento) e
Flask-SocketIO/gevent (ordem de import do monkey patch em `app.py` é requisito, não estilo).
