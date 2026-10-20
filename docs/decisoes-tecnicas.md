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
congelar com números velhos — por isso o `<meta http-equiv="refresh">` ainda não foi removido.

### Bundle do cliente

O `socket.io.js` embutido pelo Flask-SocketIO foi testado e rejeitado: ele serve uma versão
antiga e o próprio servidor responde `400 (unsupported version)` ao tentar carregá-lo. O
front-end passa a usar o cliente 4.x do jsDelivr, mesmo padrão já usado para Bootstrap e
Chart.js.

### Validação real executada

- 74 testes (54 da Fase 2 + 20 novos de tempo real).
- Servidor real: handshake `EIO=4` OK, `dashboard:solicitar` e snapshot testados com o
  cliente de teste do Flask-SocketIO, degradação observada ao vivo com banco indisponível.
