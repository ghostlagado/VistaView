# Decisões técnicas

Registro incremental das decisões tomadas durante a refatoração. Cada entrada documenta
o problema, a alternativa escolhida e o que foi rejeitado.

## Fase 2 — arquitetura e configuração

### Fábrica de aplicação em `app.py`

`create_app(settings)` passou a montar o Flask, os blueprints, o SQLAlchemy, o SocketIO e
os serviços em segundo plano. `app = create_app()` continua exportado no módulo, então
`wsgi.py` e qualquer consumidor antigo seguem funcionando sem alteração de import.

Motivo: as fases 4, 5 e 7 precisam de instâncias de teste isoladas (modo demo ligado,
worker de cotações desligado) e de injetar configuração. Rejeitado: mover a fábrica para
`utils/app.py`, o que quebraria o `from app import app` já usado por `wsgi.py`.

### Configuração central em `utils/config.py`

Toda leitura de ambiente passou a acontecer num único lugar (`Settings.from_env()`), com
`validar()` produzindo mensagem acionável. Antes, `app.py` e `utils/actions.py` liam
`getenv` diretamente e uma ausência virava `RuntimeError` de framework no import.

Rejeitado: `pydantic-settings` ou `Flask-AppBuilder`. Não introduzir dependência para o
que 40 linhas de stdlib resolvem.

Constantes de negócio (`opts`, `CHECKLISTS_VISITAS`) permaneceram constantes de módulo:
não são configuração de execução e virar variável de ambiente aumentaria a superfície de
erro sem benefício.

### Ciclo de vida de serviços em segundo plano

`services/` mantém um registro mínimo (`registrar`, `iniciar_todos`, `encerrar_todos`).
Um serviço só inicia uma vez, o encerramento percorre a ordem inversa e um serviço que
falha ao parar é registrado sem derrubar o processo.

Subir um serviço com exceção **continua** derrubando a inicialização de propósito: um
worker de cotações que não subiu precisa ser visível, não silencioso.

`wsgi.py` instala os handlers de `SIGINT`/`SIGTERM` apenas quando é o processo principal;
atrás de um gestor externo quem trata o sinal é o gestor.

### Banco de dados

Nenhuma alteração de schema. `db.create_all()` continua no-op (não existem modelos ORM) e
as rotas seguem lendo o SQL Server do GPS Vista exatamente com as mesmas consultas. A
decisão de onde persistir cotações fica registrada na Fase 6/7, em `docs/cotacoes.md`.

### Validação real executada

- 54 testes em `tests/` (contra 30 da baseline), todos passando.
- `python wsgi.py` sobe em `0.0.0.0:8092`, responde `200` em `/` e `/showcase`, e o
  handshake do Socket.IO devolve `sid` com `upgrades: ["websocket"]`.
- `SIGTERM` encerra o processo em ~1 s e libera a porta.

## Fase 4 — comunicação em tempo real

Ordem adaptada: a infraestrutura em tempo real (Fase 4) foi construída antes do refactor
visual (Fase 3), porque a nova tela da TV seria escrita duas vezes sem isso.

### Extração das consultas para `services/metricas.py`

As 13 consultas e a regra de meta/gap saíram de `routes/` e de `static/js/base.js` para um
módulo sem Flask. Assim HTTP, Socket.IO e o modo demo (Fase 5) usam exatamente o mesmo
cálculo. Os paths, métodos e formatos de resposta das rotas não mudaram — os 30 testes da
baseline passaram sem alteração depois da extração.

Rejeitado: manter o cálculo no navegador e duplicá-lo no servidor. Duas implementações da
regra de meta divergiriam na primeira mudança de percentual.

### Eventos

| Evento | Direção | Conteúdo |
| --- | --- | --- |
| `dashboard:snapshot` | servidor → cliente | painel completo, a quem acabou de conectar |
| `dashboard:update` | servidor → cliente | somente os campos de primeiro nível que mudaram |
| `dashboard:status` | servidor → cliente | fonte, `degradado`, falhas consecutivas, horário |
| `dashboard:solicitar` | cliente → servidor | pede um snapshot novo (botão de refresh manual) |

Um ciclo no servidor recalcula e faz um único broadcast. O custo não cresce com o número de
TVs ligadas — há um teste que conta as chamadas de cálculo com 3 clientes conectados.

### Falha de banco não derruba o painel

O greenlet captura a exceção, incrementa `falhasConsecutivas`, marca `degradado` e mantém o
último snapshot válido em cache. Verificado ao vivo com `ATUALIZACAO_SEGUNDOS=15`: três
ciclos com banco indisponível, servidor no ar respondendo `200` e encerrando normal no
`SIGTERM`.

### SocketIO por app

`utils/socket.py` virou uma fábrica. Reproduzido e corrigido: chamar `socketio.init_app()`
com uma segunda instância de app substituía o handler interno de `connect` do primeiro, e o
snapshot parava de ser enviado silenciosamente. Isso teria quebrado o modo demo da Fase 5.

### Cliente

`static/js/tempo-real.js` é a única dona do socket: `conectar()` é idempotente, `on()` usa
`Set` (registrar a mesma função duas vezes não duplica o callback) e devolve um cancelador.
Se o Socket.IO não carregar, o estado vira `indisponivel` e a página segue funcionando pelo
caminho HTTP. Se a conexão cair e não voltar em 5 minutos, a TV recarrega a página em vez de
congelar com números velhos.

### Bundle do cliente

O `socket.io.js` embutido pelo Flask-SocketIO foi testado e rejeitado: ele serve uma versão
antiga e o próprio servidor responde `400 (unsupported version)` ao tentar carregá-lo. O
front-end passa a usar o cliente 4.x do jsDelivr, mesmo padrão já usado para Bootstrap e
Chart.js.

### Validação real executada

- 74 testes (54 da Fase 2 + 20 novos de tempo real).
- Servidor real: handshake `EIO=4` OK, `dashboard:solicitar` e snapshot testados com o
  cliente de teste do Flask-SocketIO, degradação observada ao vivo com banco indisponível.

---

## Fase 3 — painel para TV

### Reescrever `dash.html` em vez de maquilhar o Bootstrap

O layout antigo era `d-flex flex-wrap` com `flex-basis` e cartões de altura fixa: em 1080p a
página passava do pé da tela e em 720p os cartões se esmagavam. Como o requisito é "caber na
TV sem rolagem", `templates/dash.html` foi reescrito sobre uma grade própria
(`static/css/painel.css`), e o Bootstrap/Bootstrap Icons saíram da página — as duas
dependências de CDN que sobraram são Chart.js e o cliente Socket.IO.

Nenhuma rota, contrato ou indicador foi alterado nesta fase: o que mudou foi só a camada de
apresentação. `static/js/base.js`, `static/js/chart.js`, `static/css/dash.css` e
`templates/index.html` continuam no repositório sem serem referenciados por `dash.html`; não
foram apagados porque o uso por terceiros não foi verificado.

### Grade 16:9

`grid-template-rows: auto 1fr auto` (cabeçalho, corpo, rodapé) sobre `100vh` com
`overflow:hidden`. O corpo é `1.1fr / 3fr / 1.5fr`: rankings à esquerda, KPIs + gráfico do
dia + metas no centro, desempenho e gerências à direita. A tipografia base é
`clamp(12px, 1.05vw, 30px)` e as medidas internas usam `vmin`, então a mesma página escala de
1280×720 a 2560×1440 sem mudar de estrutura. Abaixo de 600px de altura a rolagem volta a ser
liberada de propósito — nesse tamanho a prioridade é continuar legível.

Cada lista é `flex` com `justify-content: space-between` e itens `flex: 0 1 auto`: com três
itens eles preenchem o cartão, com oito eles encolhem em vez de transbordar.

### Onde a tela desenha

`static/js/painel.js` é o único renderizador. Ele assina `VistaTempoReal` e conhece a forma de
`services.metricas.painel()`; se o socket não existir, remonta o mesmo objeto chamando as
rotas HTTP uma a uma. Os dois caminhos são cobertos por um teste que compara o mapa de rotas
da página com as chaves que o servidor devolve — se um campo nascer só de um lado, a TV
mostraria números diferentes conforme a conexão.

Os gráficos não são recriados: `criarGraficos()` instancia uma vez e `update('none')` troca
somente os dados, sem animação, para a tela não piscar a cada ciclo.

### Cores semânticas

Vermelho/verde não são decoração: gap negativo, escalonadas acima de zero e "fora do prazo"
são sempre vermelhos; gap positivo e "no prazo" são verdes; o rótulo de estado no cabeçalho
usa âmbar para "modo consulta" (sem socket) e vermelho para "dados desatualizados (n)".

### O que a Fase 3 não fez

A faixa de cotações existe na tela e no renderizador, mas ainda só mostra o valor que já era
mostrado antes (`/actions/value/`, GGPS3). Ela é alimentada de verdade pela Fase 7.

### Validação real executada

- 76 testes, incluindo os contratos de rota do novo `painel.js`.
- Renderizações headless em Chromium a 1280×720, 1366×768, 1920×1080 e 2560×1440: nenhuma
  barra de rolagem, todos os cartões preenchidos, ranking de gerências completo.
- Caminho de tempo real confirmado no navegador: `estado() === 'conectado'`, 19 chaves no
  snapshot, "tempo real ativo" e "atualizado há Ns" avançando.
- Caminho HTTP confirmado com o CDN bloqueado (`modo consulta`), e as metas calculadas na
  página bateram com as do servidor (1.506 / 137 / −19 / −79).
- Estado degradado confirmado com o banco fora do ar: cartões mudam para "sem dados no
  momento" e o cabeçalho marca "dados desatualizados (n)" — sem inventar meta zerada.

## Fase 7 — cotações

### Um greenlet para todas as TVs

`services/cotacoes.py` é o único código do projeto que faz requisição HTTP de cotação. A
medição da própria brapi decidiu o desenho: `x-brapi-concurrency-limit: 1` — duas TVs
consultando ao mesmo tempo já é uma delas recusada. O painel, o ciclo de tempo real e as
rotas HTTP leem `AtualizadorCotacoes.cotacoes()`, que é uma função de cache. Validado com
três clientes socket.io conectados e ~1.100 requisições HTTP em 75 segundos: três chamadas
ao provedor no total (uma por ciclo), mesma faixa para as três telas.

### A faixa entra no painel, não em evento novo

`app.config["VISTA_COTACOES"]` é a mesma costura de `VISTA_FONTE`: `create_app` decide se
as cotações vêm do cache do provedor ou do modo demo, e `calcular_painel` junta as duas
coisas no snapshot. Como as cotações são uma chave a mais do snapshot, elas viajam pelo
canal `dashboard:update` que já existia e o `painel.js` já sabia desenhar. Não foi
preciso criar evento, listener nem protocolo novo. O caminho HTTP de fallback ganhou
`/actions/cotacoes/`, que devolve a mesma lista.

### Falha definitiva não é retentada

401/403/404 viram `FalhaDefinitiva` e encerram o ciclo na primeira tentativa: retentar um
token ausente gasta a cota mensal e atrasa o aviso. Timeout e 5xx são transitórios e têm
até três tentativas com backoff (2 s, 8 s). 429 carrega o `Retry-After` do provedor, que
passa a valer como espera do próximo ciclo — o limite do provedor é respeitado, não
ignorado. Entre ciclos com falha a espera dobra até o teto de 30 minutos.

### A idade do número faz parte do dado

Nenhuma fonte gratuita é comprovadamente em tempo real (a brapi atrasa ~3 minutos; a
documentação dela diz 30). Então a tela mostra a hora da cotação e marca em âmbar quando
ela passa de `COTACOES_VELHO_MIN`; quando não há cota nenhuma, mostra `—` com borda
vermelha, nunca `0`. Em falha, o último preço válido continua na tela.

### O que a Fase 7 não fez

- Persistência fora do processo: o MongoDB pedido no brief não existe na infraestrutura
  (verificação em `docs/cotacoes.md`), e criar tabela no `dw_vista` compartilhado é mudança
  de schema que exige aprovação. Nada foi escrito em banco.
- Provedor internacional (Yahoo) não foi implementado: medido nesta sessão, ele respondeu
  `429` sustentado, e escrever um cliente que não se consegue validar seria código morto.
  A cobertura internacional entra hoje pelos BDRs da B3 (`AAPL34`, `MSFT34`), que são o
  mesmo endpoint.
- `utils/actions.py` foi removido: era o chamador antigo, sem timeout e sem checagem de
  status, e o único import dele (`routes/acoes.py`) foi reescrito sobre o cache.

### Validação real executada

- 146 testes (eram 101), com 43 novos em `tests/test_cotacoes.py` usando uma sessão HTTP
  falsa — nenhuma requisição de teste sai para a internet.
- Servidor real contra a brapi, nos quatro ativos liberados sem token: faixa pintada em
  1920×1080 com `PETR4 57.93 -0.12% 15:12`, `VALE3`, `MGLU3 +11.92%`, `ITUB4 +2.21%`.
- Estado desatualizado forçado com `COTACOES_VELHO_MIN=2`: cotação de 15:15 lida às 15:18
  ficou âmbar com o preço preservado.
- Estado indisponível forçado com `COTACOES_SIMBOLOS=GGPS3` sem token: `401`, uma tentativa,
  aviso no log com a mensagem do provedor, faixa com `—`.
- `/actions/value/` (contrato antigo) verificado ao vivo: `0` com HTTP 200 sem cota — antes
  desta fase a mesma rota devolvia 500.
- Modo demo verificado ao vivo: sem `vista_cotacoes`, sem nenhuma menção à brapi no log,
  faixa sintética com `provedor: "demo"`.
