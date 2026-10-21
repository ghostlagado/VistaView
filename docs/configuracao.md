# Configuração

Tudo que a aplicação lê do ambiente passa por `utils/config.py::Settings`, que valida e faz o
processo falhar na subida com a lista de problemas. Não há segunda leitura de `os.environ`.

Copie o modelo antes de subir:

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

`.env.example` não tem segredo: os valores de exemplo são texto inválido de propósito.
`.gitignore` cobre `.env` e `instance/`.

## Variáveis

| Variável               | Descrição                                                              | Padrão |
| ---------------------- | ---------------------------------------------------------------------- | ------ |
| `HOST`                 | Host de execução                                                       | `0.0.0.0` |
| `PORT`                 | Porta da aplicação                                                     | `8092` |
| `DEBUG`                | Modo debug                                                             | `false` |
| `SECRET`               | Chave de sessão do Flask                                               | no demo é gerada; fora do demo, obrigatória |
| `DB_URI`               | URI SQLAlchemy do banco. **Opcional**: sem ela o painel lê do espelho SQLite local | `instance/dw_vista_local.sqlite3` |
| `VISTA_ESQUEMA`        | Prefixo das tabelas de estrutura no SQL Server                         | `dw_vista.dbo` quando a URI é `mssql` |
| `DEFAULT_OPT`          | Recorte padrão: `GER`, `GR` ou `DIR`                                   | `GR` |
| `DEFAULT_GR`           | Regional exibida por padrão                                            | `Parana Interior` |
| `META_PERCENTUAL`      | Crescimento sobre o mês anterior usado no cálculo da meta              | `15` |
| `ATUALIZACAO_SEGUNDOS` | Ciclo do painel em tempo real (mínimo 15)                              | `60` |
| `ACTION_API`           | Token da brapi.dev (cadastro gratuito)                                 | — |
| `COTACOES_SIMBOLOS`    | Até 5 ativos da B3, separados por vírgula                              | `GGPS3` |
| `COTACOES_SEGUNDOS`    | Ciclo que consulta o provedor (mínimo 60)                              | `300` |
| `COTACOES_VELHO_MIN`   | Idade a partir da qual a cotação aparece marcada como desatualizada     | `15` |
| `MODO_DEMO`            | Painel com dados sintéticos, sem banco e sem API externa                | `false` |

Limites recusados na subida, não ajustados em silêncio: `ATUALIZACAO_SEGUNDOS` < 15,
`COTACOES_SEGUNDOS` < 60, `COTACOES_VELHO_MIN` < 1, `META_PERCENTUAL` < 0 e mais de 5 símbolos
em `COTACOES_SIMBOLOS`. O porquê de cada um está em [`modo-demo.md`](modo-demo.md) e
[`cotacoes.md`](cotacoes.md).

## Os três modos

| Modo | Como ativar | Fonte dos indicadores | Banco | Cotações |
| ---- | ----------- | --------------------- | ----- | -------- |
| demonstração | `MODO_DEMO=true` | `IndicadoresDemonstracao` (sintética) | nenhum | faixa sintética, zero chamada de rede |
| desenvolvimento | nada além do `.env` | `IndicadoresWarehouse` sobre SQLite | `instance/dw_vista_local.sqlite3` | provedor real se `ACTION_API` existir |
| warehouse | `DB_URI=mssql+pyodbc://…` | `IndicadoresWarehouse` sobre SQL Server | `dw_vista` | idem |

A fonte é escolhida uma vez, em `create_app`, e vale para as rotas e para o Socket.IO. Dado
real e dado de demonstração não se misturam.

## Bancos suportados

Os modelos são um espelho de leitura e a mesma consulta compila para os dois bancos:

| Banco | Como ativar | O que muda |
| ----- | ----------- | ---------- |
| **SQLite** | nada — é o padrão | arquivo local, sem servidor, sem prefixo de schema |
| **SQL Server** | `DB_URI=mssql+pyodbc://...` | tabelas de estrutura em `dw_vista.dbo`, leitura com `WITH(NOLOCK)` |

As diferenças de dialeto são do SQLAlchemy (`TOP 1`/`LIMIT 1`,
`DATEPART(month, …)`/`CAST(STRFTIME('%m', …) AS INTEGER)`) e o hint de leitura existe só no
dialeto `mssql`. `tests/test_portabilidade.py` assina isso consulta por consulta. Detalhes em
[`arquitetura.md`](arquitetura.md#3-portabilidade-entre-sqlite-e-sql-server).

`VISTA_ESQUEMA` com URI SQLite é recusado na validação: `Table.schema` é atributo do
mapeamento, não do dialeto, e o prefixo quebraria todas as consultas.

## Populando o SQLite local

Sem o espelho preenchido, o painel abre com tudo zerado e o boot avisa no log — é o caso de
quem acabou de clonar:

```bash
python -m services.semente            # cria o schema e insere as duas janelas
python -m services.semente --limpar   # refaz do zero
```

O comando **recusa** qualquer URI que não seja SQLite: o warehouse é lido, nunca escrito. Os
dados são determinísticos (seed fixa, datas ancoradas no dia da execução) e servem para ver o
painel com número realista durante o desenvolvimento — não são demonstração nem substituto do
warehouse.
