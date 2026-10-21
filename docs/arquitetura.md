# Arquitetura

Como o Vista View está organizado hoje, e por que cada peça está onde está. Este documento
descreve o código real do repositório; decisões com alternativas descartadas ficam em
[`decisoes-tecnicas.md`](decisoes-tecnicas.md).

## As camadas

```text
navegador na TV
   |
   v  HTTP / Socket.IO
[ templates + static/js ]  desenha o payload, escuta o socket, cai para consulta se precisar
   |
   v
[ routes/ ]                valida o recorte e serializa — nenhuma regra de negócio aqui
   |
   v  fonte = app.config["VISTA_FONTE"]
[ IndicadoresWarehouse ]  [ IndicadoresDemonstracao ]  [ AtualizadorCotacoes ]
   metricas.py                showcase.py                  cotacoes.py
   |
   v  ORM (só a fonte real)
[ models/ ]                Tarefa - Recurso - Estrutura - Cr: espelho de leitura, nunca escrita
   |
   v  SQLAlchemy
[ SQLite | SQL Server ]    decidido por DB_URI: SQL Server com URI, SQLite local sem ela
```

## 1. `models/` — um espelho de leitura, não um schema nosso

As quatro classes descrevem tabelas que pertencem a outro time (`TAREFA`, `RECURSO`,
`dw_vista.dbo.DM_ESTRUTURA`, `dw_vista.dbo.DM_CR`). Daí as escolhas que pareceriam estranhas
num modelo ORM comum:

| Escolha | Motivo |
| ------- | ------ |
| Nome físico da coluna no 1º argumento de `mapped_column` (`"TerminoReal"`) | o SQL gerado precisa bater com o do warehouse; o Python fica em `snake_case` |
| Nenhum `ForeignKey` físico | o vínculo é lógico na origem, e o painel não escreve nada lá |
| `relationship(viewonly=True)` com `primaryjoin` explícito | o join fica declarado num lugar só, sem insinuar cascade ou escrita |
| Chaves primárias declaradas | só para o mapeamento identificador do SQLAlchemy funcionar; nenhuma consulta depende delas |
| `Nivel_01`…`Nivel_05` não mapeadas | copiar coluna que ninguém lê aumenta a superfície de mudança quando o DBA mexe na origem |

Regras de negócio que são propriedade da tabela moram aqui como constantes e propriedades:
`STATUS_CONCLUIDA = 85`, `STATUS_ABERTAS = (25, 10, 70)`, `Tarefa.concluida`,
`Tarefa.eh_visita`.

### O recorte é a parte sensível

`GER`/`GR`/`DIR` escolhe qual coluna da cadeia de comando vira filtro. Antes isso era
interpolado como texto no `WHERE`. Hoje `Cr.coluna_do_recorte(opt)` devolve a **coluna
mapeada** correspondente, ou `None`:

```python
campo = fonte.coluna_de_filtro(opt)   # Cr.gerente_regional, Cr.gerente ou Cr.diretor_regional
if campo is None:
    return jsonify({"error": "Opção inválida"}), 400
```

Um valor fora da whitelist não produz string nenhuma — não há o que injetar. Detalhe
prático para quem mexe nisso: `ColumnOperators.__bool__` levanta `NotImplementedError`,
então o teste é sempre `campo is None`, nunca `if not campo`.

## 2. `services/` — as regras, uma vez

Duas classes com o mesmo contrato de 13 folhas + `painel()`:

* `IndicadoresWarehouse` (`metricas.py`) monta consultas SQLAlchemy a partir dos modelos;
* `IndicadoresDemonstracao` (`showcase.py`) devolve cifras sintéticas determinísticas.

`montar_painel(fonte, opt, gr, agora, meta)` agrega as folhas e contém a regra de meta. Ele
não sabe qual fonte recebeu, e é assim que HTTP, Socket.IO e o modo demo chegam no mesmo
número com a mesma fórmula.

A escolha de fonte acontece uma vez, em `create_app`, e vai para
`app.config["VISTA_FONTE"]`; `services/fonte.py::indicadores()` é a única pergunta que as
rotas fazem. O corolário é a regra de ouro do projeto: **dado real e dado de demonstração
não se misturam jamais** — não existe caminho no código por onde uma cifra sintética entre
numa consulta real, porque os dois lados nunca compartilham objeto nem sessão.

`realtime.py` (`AtualizadorPainel`) é o greenlet que recalcula o painel a cada
`ATUALIZACAO_SEGUNDOS`, guarda o último snapshot, calcula o delta e marca `degradado` quando
a fonte falha — sem derrubar o ciclo e sem apagar o que estava na tela. `cotacoes.py` é o
único cliente do provedor: um ciclo, um cache, todos os leitores.

## 3. Portabilidade entre SQLite e SQL Server

A mesma estrutura de consulta compila para os dois bancos; o que muda é apenas o dialeto:

| Precisão | SQL Server | SQLite |
| -------- | ---------- | ------ |
| mês/ano/dia de uma data | `DATEPART(month, …)` | `CAST(STRFTIME('%m', …) AS INTEGER)` |
| `TOP 1` / `TOP 3` | `TOP n` | `LIMIT n OFFSET 0` |
| leitura sem lock | `WITH(NOLOCK)` (hint) | não existe — o hint é declarado só para o dialeto `mssql` |
| schema das tabelas de estrutura | `dw_vista.dbo` | não há schema cruzado: prefixo vazio |
| `CASE` de performance | `CASE WHEN …` | `CASE WHEN …` |

O `WITH(NOLOCK)` é aplicado por `_com_hint`, que usa `with_hint(entidade, "WITH(NOLOCK)",
"mssql")` — a restrição de dialeto faz parte da chamada, então ele simplesmente não aparece no SQLite.

O prefixo `dw_vista.dbo` **não** é por dialeto: `Table.schema` é atributo do mapeamento, e
com ele posto o SQLite também o imprimiria (e quebraria). Por isso a decisão é de processo,
tomada no `create_app` uma vez, antes de qualquer consulta:

```python
models.aplicar_esquema(settings.esquema)   # "dw_vista.dbo" só quando a URI é mssql
```

`Settings.validar()` recusa `VISTA_ESQUEMA` com URI SQLite, porque é uma combinação que não
pode funcionar.

### SQLite local

* arquivo `instance/dw_vista_local.sqlite3`, já coberto pelo `.gitignore`;
* `create_app` chama `db.create_all()` **apenas** para URI SQLite — contra o warehouse isso
  seria um `CREATE TABLE` num banco que este painel apenas lê;
* `python -m services.semente` popula o espelho com duas janelas determinísticas (mês
  anterior completo e mês corrente até hoje) e **recusa** URI que não seja SQLite;
* nada no boot insere dados: popular é decisão de quem desenvolve, e um painel que se
  auto-semeia esconderia que está mostrando cifra inventada.

## 4. Frontend

`templates/dash.html` é o painel 16:9 sem rolagem. `static/js/painel.js` é o único desenhador:
recebe o payload de `painel()` — do socket ou das rotas HTTP — e desenha. `tempo-real.js`
traz o snapshot, aplica delta, mantém o estado `Online`/`Offline` e o relógio alinhado ao
horário do servidor (`emitidoEm`, com deslocamento medido no navegador).

A forma do payload é contrato: os 13 endpoints JSON e o `dashboard:snapshot` entregam o mesmo
objeto, e `tests/test_contracts.py` + `tests/test_demo.py` quebram se alguém renomear chave.

## 5. Onde cada coisa é testada

| Arquivo | Assunto |
| ------- | ------- |
| `test_contracts.py` | path, método e forma de cada rota |
| `test_calculos.py` | filtros de negócio na consulta compilada e a forma dos rankings |
| `test_data_referencia.py` | janelas de mês, mês anterior e virada de janeiro |
| `test_portabilidade.py` | as 13 folhas compiladas para os dois bancos + o painel executado num SQLite semeado |
| `test_tempo_real.py` | snapshot, delta, reconexão e degradação |
| `test_demo.py` | isolamento da fonte sintética e contrato com o modo real |
| `test_cotacoes.py` | cache, limites, backoff e indisponibilidade do provedor |
| `test_layout_tv.py` | faixa contínua, selo único, relógio, números e ausência de rolagem |
| `test_regressao.py` | os seis critérios anti-regressão da auditoria |
