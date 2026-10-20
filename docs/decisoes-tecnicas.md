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
