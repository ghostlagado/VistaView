# Contribuindo

O Vista View é um painel de TV que roda 24h em gerência. Isso define o padrão de
contribuição: uma regressão não é uma tela feia — é um número errado no chão de uma sala onde
ninguém vai inspecionar o DOM.

## Antes de mexer

1. Leia [`docs/arquitetura.md`](docs/arquitetura.md) — ela diz onde cada responsabilidade
   mora e por quê.
2. Leia os seis critérios de [`docs/auditoria-e-baseline.md`](docs/auditoria-e-baseline.md).
   Cada um tem teste em `tests/test_regressao.py`; quebrar um é decisão consciente, não
   efeito colateral.
3. Rode a suíte antes de começar, para saber o ponto de partida:

```bash
python -m pytest -q
```

## Ambiente

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
python -m services.semente        # popula o espelho SQLite local
python app.py                     # http://localhost:8092
```

Três modos, e eles não se misturam:

| Modo | Como | Fonte dos indicadores | Cotações |
| ---- | ---- | --------------------- | -------- |
| demonstração | `MODO_DEMO=true` | `IndicadoresDemonstracao` (sintética) | faixa sintética, nenhuma chamada de rede |
| desenvolvimento | `MODO_DEMO=false` e nada mais | ORM sobre o SQLite local | provedor real, se `ACTION_API` existir |
| warehouse | `DB_URI=mssql+pyodbc://…` | ORM sobre o SQL Server | idem |

## Convenções deste código

* **Português nos nomes e nos comentários.** Identificadores, mensagens de erro e docstrings
  são em português; o inglês fica para termos técnicos que não têm tradução usada
  (`schema`, `hint`, `greenlet`).
* **Comentário explica o porquê, não o quê.** Toda decisão não-óbvia tem o motivo escrito
  junto (por que o SQLite não leva prefixo de schema, por que `campo is None` e não
  `not campo`). Um comentário que só repete o código é removido na revisão.
* **Nada de SQL em texto.** Consulta se monta a partir de `models/`. Se algo parecer
  precisar de texto cru, a alternativa é um hint restrito a dialeto ou uma coluna nova no
  espelho — e isso vai para `docs/decisoes-tecnicas.md`.
* **Regra de negócio uma vez só.** `85`, `Expirada = 0` e os cinco checklists existem em um
  lugar (`models/tarefa.py`, `utils/config.py`); uma segunda cópia é bug.
* **Camadas não pulam.** `routes/` não consulta banco; `models/` não conhece Flask;
  `services/` não conhece HTTP.
* **`ColumnOperators.__bool__` levanta `NotImplementedError`.** Coluna mapeada se testa com
  `is None`. Sempre.

## Testes

Toda mudança de cálculo precisa de dois tipos de teste: o valor (o que a folha devolve) e a
forma (o que a rota entrega). Se a mudança toca em consulta, adicione o caso em
`tests/test_portabilidade.py` — as 13 folhas são compiladas para os dois bancos ali, e um
diaeto novo quebra a suíte em vez de quebrar a TV.

Sem rede na suíte: o provedor de cotações é interceptado por sessão HTTP falsa e as consultas
são capturadas antes de executar (ver `capture_sql` em `tests/conftest.py`). Um teste que
dependa de internet ou do warehouse não passa no CI nem na máquina do colega.

```bash
python -m pytest -q                     # tudo
python -m pytest tests/test_portabilidade.py -q
```

## Commits e pull request

* Mensagem no padrão que já está no histórico: `tipo: descrição curta em minúscula`
  (`fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
* Um commit por mudança coesa. História revisável vale mais que commit pequeno por arquivo
  quando o arquivo isolado não faz sentido.
* Antes de abrir o PR: suíte verde, painel aberto em `MODO_DEMO=true` **e** no modo SQLite,
  e nenhuma credencial nova em diff (`.env` não é versionado; se a mudança pede variável nova,
  `.env.example` e o README mudam junto).
* Se a mudança altera o payload do painel, atualize `docs/arquitetura.md` e os testes de
  contrato no mesmo PR — o frontend e o Socket.IO consomem as mesmas chaves.

## O que não aceitar

* Dados de demonstração alcançando o caminho real (ou vice-versa). A fonte é escolhida uma
  vez, em `create_app`; nada deve contornar `app.config["VISTA_FONTE"]`.
* `db.create_all()` ou qualquer `INSERT` contra o warehouse. Este projeto lê.
* Novos recortes fora de `GER/GR/DIR` sem discutir antes: a whitelist é a defesa do único
  lugar onde houve interpolação de texto no passado.
* Dependência nova sem motivo medido. `docs/cotacoes.md` existe porque trocar provedor foi
  decisão com números, não preferência.

## Reportando problema

Para defeito comum, uma issue com: modo (`MODO_DEMO`, `DB_URI`), versão, o que esperava, o
que apareceu na tela, e o log do servidor se houver. **Não cole** token, URI de banco com
credencial nem dado real de gerência em issue — este repositório é público. Para
vulnerabilidade, veja [`SECURITY.md`](SECURITY.md).
