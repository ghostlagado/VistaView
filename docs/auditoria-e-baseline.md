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
| Unidades completas | `/get_unidades` | lista usada na faixa de unidades do rodapé |
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

### Itens 13 a 21 — o que aconteceu com cada um

Status registrados na Fase 9, um por item da auditoria. "Resolvido" significa validado com
teste ou execução real, não apenas escrito.

13. **`DB_URI` ausente derruba o processo no import** (`RuntimeError` do Flask-SQLAlchemy).
    Configuração precisa ser validada e o modo demo precisa funcionar sem o banco.
    → **Resolvido na fase 2.** `utils/config.py:Settings.validar()` falha na subida com a
    lista do que falta (`DB_URI` fora do demo, `SECRET` sempre, `DEFAULT_OPT` fora da
    whitelist, percentuais e ciclos fora de faixa), e `MODO_DEMO=true` dispensa o banco.
    Coberto por `tests/test_config.py` (inclusive `test_create_app_recusa_configuracao_incompleta`).
14. **`utils/actions.py` sem timeout, sem checagem de status e sem tratamento de erro.** Uma
    resposta inesperada do provedor produz `KeyError: 'results'` e HTTP 500 (reproduzido na
    auditoria). Sem cache: cada navegador conectado consulta o provedor individualmente.
    → **Resolvido na fase 7.** O módulo foi removido e substituído por `services/cotacoes.py`:
    timeout de conexão/leitura, checagem de status, erro definitivo ≠ transitório, três
    tentativas com backoff, respeito ao `Retry-After`, cache em memória lido por todas as TVs
    e uma única fila de atualização. `/actions/value/` mantém o contrato de número e passou a
    responder `0` com HTTP 200 em vez de 500. Validação real: 3 clientes Socket.IO + ~1.100
    requisições HTTP em 75s resultaram em 3 chamadas ao provedor.
15. **Cotação única e fixa (`GGPS3`)**, sem símbolos configuráveis e sem persistência.
    → **Resolvido na parte de símbolos (fase 7).** `COTACOES_SIMBOLOS` aceita até 5 ativos e
    todos viram uma requisição só; mais que isso a configuração é rejeitada antes de subir.
    Persistência continua aberta — ver 16.
16. **Sem persistência de cotações** e **sem MongoDB na infraestrutura atual** (só SQL Server).
    A decisão sobre onde persistir está registrada em `docs/cotacoes.md` (Fase 6/7).
    → **Aberto, é decisão e não implementação.** Não há MongoDB no requirements, no repositório
    nem no docker; o brief pedia Mongo "após verificar a compatibilidade com a infraestrutura
    existente". As três opções (só memória, Mongo novo, tabela em `dw_vista`) e os riscos de
    cada uma estão descritos em `docs/cotacoes.md`. Mudar o schema compartilhado ou criar
    serviço externo exige aprovação, então nada foi implementado por conta própria.
17. **SocketIO declarado mas nunca usado** — nenhum evento, nenhum handler, nenhuma reconexão.
    A "atualização em tempo real" hoje é um `<meta http-equiv="refresh" content="600">`, que
    recarrega a página inteira a cada 10 minutos.
    → **Resolvido na fase 4.** `services/realtime.py` roda o ciclo de painel, emite
    `dashboard:snapshot` / `dashboard:update` (só o que mudou) / `dashboard:status` e trata
    `dashboard:solicitar`; o meta refresh foi removido de `templates/dash.html` (confirmado por
    busca no arquivo). Reconexão validada com o servidor sendo morto e subido de novo.
18. **`templates/index.html` é órfã** (nenhuma rota a renderiza) e referencia arquivos inexistentes
    (`/static/Gpslogo.png`, `/static/favicon.png`); carrega `base.js`, que falharia nela. Não foi
    removida: uso não verificado.
    → **Mantida, intencionalmente.** Remover arquivo sem uso verificado está na lista de ações que
    pedem aprovação. Nada no código novo a importa.
19. **`Example.html` não carrega JavaScript nenhum** — os dois `<canvas>` nunca recebem um
    `Chart`. O repositório Showcase tem a versão funcional (`chart_ex.js` ligada na página).
    → **Contornado, não consertado.** A demonstração real passou a ser o modo demo do painel
    (`MODO_DEMO=true`), com o mesmo contrato de rota e os mesmos eventos; `/showcase` continua
    servindo a página estática como referência visual histórica, com os gráficos parados de
    antes. Se a referência antiga ainda for usada por alguém, ela segue disponível.
20. **`static/style/index.css`** é usado apenas pela página órfã.
    → **Mantido junto com o item 18.** Mesmo motivo.
21. **Segurança**: CORS liberado (`allow_headers=["*"]`) e `SECRET` sem valor padrão. Não há
    segredo em versionamento e o `.gitignore` cobre `.env`. A interpolação de `{campo}` no SQL é
    segura porque `campo` só vem da whitelist `opts` — há teste cobrindo isso.
    → **Parcialmente resolvido.** `SECRET` agora é obrigatória e validada na subida (fase 2); o
    token do provedor (`ACTION_API`) só existe no processo do servidor e há teste afirmando que
    não aparece em resposta HTTP nem em mensagem de erro; o `.gitignore` cobre `.env` (também
    testado). O CORS liberado **não** foi alterado: restringir a origem é mudança de contrato
    externo que pode quebrar consumidores existentes e precisa de aprovação.

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
4. O modo demo não toca no banco real. A parte "visualmente identificável" do critério foi
   relaxada em 2026-10-20 pelo refinamento de navbar, que removeu o selo DEMO da tela; ver a
   nota na tabela abaixo.
5. Nenhum cliente conectado gera uma chamada ao provedor de cotações por conta própria.
6. `tests/` passa em conjunto com os testes novos de cada fase.

### Como cada critério é verificado hoje

| Critério | Teste que o trava |
| --- | --- |
| 1 — rotas e formas inalteradas | `test_regressao.py::o_mapa_de_rotas_e_o_da_baseline_mais_a_rota_de_cotacoes` (comparação com o conjunto congelado na auditoria), `as_rotas_de_indicador_aceitam_so_get`, `test_contracts.py::toda_chamada_fetch_existe_no_back_end` |
| 2 — filtros de negócio | `test_regressao.py::os_filtros_de_negocio_continuam_no_sql` (5 casos, parâmetros de bind conferidos), `a_whitelist_de_recorte_persiste`, `fora_da_whitelist_nao_vira_sql` |
| 3 — tela resiste a falha | `a_pagina_sai_mesmo_com_tudo_fora_do_ar`, `o_ciclo_nao_quebra_com_indicadores_fora_do_ar`, `o_provedor_fora_do_ar_nao_derruba_o_snapshot` |
| 4 — demo isolado | `test_demo.py::as_rotas_de_demo_nao_tocam_o_banco`, `o_ciclo_real_nao_se_confunde_com_demo`, `showcase_nao_importa_nada_de_dados_reais`; a identificação saiu da tela e virou `test_o_modo_fica_registrado_no_dom` + `test_o_demo_nao_ganha_badge_na_tela` (ver [`docs/modo-demo.md`](modo-demo.md)) |
| 5 — uma fila de cotações | `test_regressao.py::nenhuma_requisicao_http_chama_o_provedor`, `test_cotacoes.py` (verde único, cache lido por todos) |
| 6 — suíte verde junto | `python -m pytest -q` → **183 passed** (30 na baseline da Fase 1; as fases 5 a 8 somaram demo, cotações e regressão, e o refinamento de layout de 2026-10-20 somou `test_layout_tv.py`) |

