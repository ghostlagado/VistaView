# Fase 1 — Auditoria e baseline

Data da auditoria: 2026-10-20 · Branch: `refactor/tv-dashboard` · Commit de partida: `7fdc512`

## 1. Mapa da arquitetura atual

```
app.py            cria Flask, registra blueprints, inicializa SQLAlchemy e SocketIO,
                  define / (dash.html) e /showcase (Example.html)
wsgi.py           ponto de entrada de produção (socketio.run)
utils/
  config.py       whitelist `opts` (GER/GR/DIR) e os 5 UUIDs de checklist de visita
  db.py           instância única de SQLAlchemy (sem models)
  socket.py       instância de SocketIO (não era inicializada)
  blueprints.py   mapa blueprint → url_prefix
  actions.py      chamada HTTP ao provedor de cotações (brapi.dev)
routes/
  general.py      /top3_sups /top3_uni /get_unidades /graph_days /graph_days_ant
                  /get_performance /get_gerentes
  visitas.py      /visitas/mes /visitas/dia
  tarefas.py      /tarefas/total /tarefas/dia /tarefas/mes/anterior /tarefas/escalonadas
  acoes.py        /actions/value
templates/
  dash.html       dashboard real (usa {{gr}}/{{opt}} via sessionStorage)
  Example.html    demonstração estática (valores hardcoded)
  index.html      versão antiga, órfã (nenhuma rota a renderiza)
static/js/
  base.js         11 fetches + cálculo de meta/gap + preenchimento dos cards
  chart.js        gráficos alimentados pelo back-end
  chart_ex.js     gráficos alimentados por dados hardcoded (pertence ao Showcase)
static/css/dash.css, static/style/index.css
```

Camada de dados: **SQL Server** do GPS Vista (`Tarefa`, `RECURSO`, `dw_vista.dbo.DM_ESTRUTURA`,
`dw_vista.dbo.DM_CR`) acessado por SQL cru parametrizado via SQLAlchemy. Não há modelos ORM,
não há migrações e `db.create_all()` é no-op.

## 2. Inventário de funcionalidades a preservar

| Indicador | Fonte | Regra observada |
| --- | --- | --- |
| Total mês | `/tarefas/total` | `Tarefa` com `Status = 85`, `Expirada = 0`, `TerminoReal` no mês/ano correntes |
| Total dia | `/tarefas/dia` | mesma regra + `DAY(TerminoReal)` |
| Mês anterior | `/tarefas/mes/anterior` | base para a meta |
| Visitas mês/dia | `/visitas/mes`, `/visitas/dia` | filtro adicional pelos 5 `ChecklistId` de visita |
| Escalonadas | `/tarefas/escalonadas` | `Escalonado > 0`, `Status IN (25, 10, 70)` — **sem** filtro de mês |
| Performance | `/get_performance` | `Escalonado = 0` → no prazo; `> 0` → fora do prazo |
| Top 3 unidades | `/top3_uni` | ranking por `Nivel_03` |
| Unidades completas | `/get_unidades` | lista usada no marquee |
| Top 3 supervisores | `/top3_sups` | por `RECURSO.Nome` de quem finalizou |
| Gerências | `/get_gerentes` | por `DM_CR.Gerente` |
| Série diária | `/graph_days`, `/graph_days_ant` | mês atual × mês anterior |
| Meta mês | `base.js` | `mês anterior × 1,15` (15% configurável) |
| Meta dia | `base.js` | `meta mês ÷ dias restantes` |
| Gap mês/dia | `base.js` | `realizado − meta`, cor por sinal |
| Recorte | `opts` | `GER`/`GR`/`DIR` define a coluna de filtro |
| Cotação | `/actions/value` | preço atual de `GGPS3` |
| Demo | `/showcase` | página estática com números fixos |

## 3. Problemas encontrados

### Críticos (impediam o app de funcionar) — corrigidos nesta fase

1. **`requirements.txt` vazio.** Nenhuma dependência declarada; a instalação do README
   (`pip install -r requirements.txt`) não instalava nada. → preenchido.
2. **`routes/` e `utils/` sem `__init__.py`.** Qualquer ambiente com o pacote PyPI `routes`
   instalado importa o pacote errado e o app quebra com `ImportError` na inicialização. → adicionados.
3. **`wsgi.py` importava `socketio` de `app.py`, que não existia.** Todo deploy WSGI falhava.
   → `app.py` agora inicializa o SocketIO de `utils/socket.py`; `wsgi.py` consome `HOST`/`PORT`.
4. **Rota `/` caía com 500.** `dash.html` usa `{{gr}}`/`{{opt}}` e `render_template('dash.html')`
   não passava contexto → `UndefinedError` em `gr.split()`. → contexto via `DEFAULT_GR`/`DEFAULT_OPT`.
5. **7 de 12 URLs do front-end não existiam no back-end** (`/total_de_tarefas`, `/escalonadas`,
   `/visitas_mes`, `/visitas_dia`, `/tarefas_mes_ant`, `/tarefas_dia`, `/get_act_value`) porque os
   blueprints foram criados com prefixos que o JS nunca passou a usar. → JS rebatizado para as
   rotas reais; **os contratos do back-end foram preservados** (podem ter outros consumidores).
6. **`meta` era sempre `null`** em `base.js` (`var meta = porcentagemMeta/100` sobrescrito logo
   abaixo por `var meta = null`). Todos os cards de META, META DIA e GAP ficavam `NaN`. → corrigido.
7. **Formato de resposta divergente em `/tarefas/escalonadas`** (devolve `{"total": n}`, o JS lia o
   objeto inteiro). → JS lê `js['total']`.
8. **Uma falha de qualquer indicador abortava todo o restante** (`start()` encadeava `await` sem
   tratamento; a cotação era a primeira chamada e um 500 do provedor zerava o dashboard). →
   cada etapa isolada; falha externa passa a afetar apenas o próprio card.
9. **`DEBUG = getenv("DEBUG","false").lower == "true"`** comparava o método, não o texto: sempre
   `False`, mesmo com `DEBUG=true`. → `.lower() == "true"`.
10. **`.env.example` inconsistente**: `HOST` declarado duas vezes (a segunda linha é `PORT`), sem
    `PORT`, sem `DEBUG`, sem `SECRET`. → reescrito e consistente com o código e com o README.

### Corrigidos por serem pré-requisito das fases seguintes

11. **Regra de mês anterior quebrava em janeiro**: `agora.month - 1` gerava `MONTH = 0` e a meta
    do ano novo ficava zerada. → janeiro passa a referenciar dezembro do ano anterior
    (mantida a regra de negócio, corrigida a aritmética).
12. **`metaDiaria = metaAtual/(30-dia)`**: divisor fixo em 30 (errado em fevereiro e meses de 31)
    e divisão por zero no último dia do mês. → usa o número real de dias do mês e nunca divide por zero.

### Em aberto (tratados nas fases 2 a 8)

13. **`DB_URI` ausente derruba o processo no import** (`RuntimeError` do Flask-SQLAlchemy).
    Configuração precisa ser validada e o modo demo precisa funcionar sem o banco.
14. **`utils/actions.py` sem timeout, sem checagem de status e sem tratamento de erro.** Uma
    resposta inesperada do provedor produz `KeyError: 'results'` e HTTP 500 (reproduzido na
    auditoria). Sem cache: cada navegador conectado consulta o provedor individualmente.
15. **Cotação única e fixa (`GGPS3`)**, sem símbolos configuráveis e sem persistência.
16. **Sem persistência de cotações** e **sem MongoDB na infraestrutura atual** (só SQL Server).
    A decisão sobre onde persistir está registrada em `docs/cotacoes.md` (Fase 6/7).
17. **SocketIO declarado mas nunca usado** — nenhum evento, nenhum handler, nenhuma reconexão.
    A "atualização em tempo real" hoje é um `<meta http-equiv="refresh" content="600">`, que
    recarrega a página inteira a cada 10 minutos.
18. **`templates/index.html` é órfã** (nenhuma rota a renderiza) e referencia arquivos inexistentes
    (`/static/Gpslogo.png`, `/static/favicon.png`); carrega `base.js`, que falharia nela. Não foi
    removida: uso não verificado.
19. **`Example.html` não carrega JavaScript nenhum** — os dois `<canvas>` nunca recebem um
    `Chart`. O repositório Showcase tem a versão funcional (`chart_ex.js` ligada na página).
20. **`static/style/index.css`** é usado apenas pela página órfã.
21. **Segurança**: CORS liberado (`allow_headers=["*"]`) e `SECRET` sem valor padrão. Não há
    segredo em versionamento e o `.gitignore` cobre `.env`. A interpolação de `{campo}` no SQL é
    segura porque `campo` só vem da whitelist `opts` — há teste cobrindo isso.

## 4. Comparação com `VistaView_Showcase`

O Showcase é um site estático (sem Python, sem banco) e é **mais completo que a cópia dentro do
VistaView**:

| Arquivo | Situação |
| --- | --- |
| `css/dash.css` | idêntico ao do VistaView — nada a migrar |
| `img/*` (5 arquivos) | idênticos a `static/img/*` — nada a migrar |
| `js/chart_ex.js` | Showcase tem 7 pontos de dado; a cópia `Example.html` do VistaView tem 2 e ainda está ligada em nenhum lugar |
| `index.html` | versão do Showcase carrega `chart_ex.js` e trata a data; `templates/Example.html` não carrega script — os gráficos da demo estão quebrados |
| `.vscode/settings.json` | configuração de editor, sem valor funcional |

Conclusão: o Showcase **não possui regra de negócio, rota ou serviço exclusivo**. O que ele traz de
útil é o layout de demonstração já copiado e um gerador de série falsa. A migração da Fase 5 é,
portanto, substituir a demo estática por um modo demo real (dados sintéticos pelo mesmo contrato de
API e os mesmos eventos em tempo real). O repositório Showcase não deve ser excluído antes de
confirmar que ninguém o usa como referência visual.

## 5. Baseline de testes

Nenhum teste existia no repositório. Criados em `tests/`:

- `test_contracts.py` — toda `fetch()` do front-end precisa resolver numa rota real; `/` e
  `/showcase` renderizam; `opt` inválido devolve 400 nas 13 rotas parametrizadas.
- `test_calculos.py` — formato de resposta de cada indicador, agregação de performance, os 5
  checklists, whitelist de `opts` e ausência de injeção.
- `test_data_referencia.py` — janela mês/mês-anterior, incluindo a virada de janeiro.

Resultado: **30 passed** (`./.venv/bin/python -m pytest tests -q`). As rotas que dependem do
SQL Server são exercitadas com o layer de execução interceptado; nenhuma consulta real é feita.

Ambiente da baseline: Python 3.14.7 em `.venv`, `DB_URI=sqlite://` apenas para desenvolvimento.
O provedor de cotações não tem chave no ambiente local, por isso `/actions/value/` responde 500
— comportamento que a Fase 7 elimina.

## 6. Critérios de aceitação anti-regressão

Cada fase abaixo precisa manter estas verdades:

1. As 13 rotas JSON existentes continuam com o mesmo path, método e forma de resposta.
2. Os filtros de negócio (`Status = 85`, `Expirada = 0`, `Escalonado`, os 5 checklists, a whitelist
   `GER/GR/DIR`) permanecem inalterados, exceto onde um bug for corrigido e registrado aqui.
3. `/` renderiza mesmo com falha de qualquer indicador individual ou do provedor de cotações.
4. O modo demo não toca no banco real e é visualmente identificável.
5. Nenhum cliente conectado gera uma chamada ao provedor de cotações por conta própria.
6. `tests/` passa em conjunto com os testes novos de cada fase.
