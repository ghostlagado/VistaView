# Modo demonstração (`MODO_DEMO`)

## Para que serve
Abrir o painel numa TV sem conectar o warehouse nem a API de cotações: em treinamento,
feira, gravação de vídeo ou desenvolvimento local. O modo é escolhido por configuração e
vale para a aplicação inteira — não existe uma página paralela de demo com contrato próprio.

```bash
MODO_DEMO=true .venv/bin/python wsgi.py
```

## O que muda

| | modo real | modo demo |
|---|---|---|
| indicadores | `IndicadoresWarehouse` (`services/metricas.py`), lendo SQL Server com `DB_URI` ou o SQLite local sem ela | `IndicadoresDemonstracao` (`services/showcase.py`), sintético |
| cotações | provedor externo (fase 7) | série sintética no cartão "Cotações" |
| `DB_URI` | opcional (sem ela, SQLite local) | dispensada |
| `SECRET` | obrigatória | dispensada — o processo gera uma chave de sessão descartável |
| `<body data-modo>` | `real` | `demo` |
| `nome_ciclo`/`fonte` no `dashboard:status` | `painel` | `demo` |

As rotas, os formatos de resposta, o cálculo da meta e as cores semânticas são os mesmos
nos dois modos: `services/metricas.montar_painel()` é compartilhado, e o teste
`test_payload_do_demo_tem_as_mesmas_chaves_do_real` garante que o payload sintético tem as
mesmas chaves do real (mais `cotacoes`).

### O selo visual saiu da tela

O refinamento de navbar pedido em 2026-10-20 determinou uma barra limpa e a remoção do badge
**DEMO**. A identificação passou a ser do DOM para fora — `data-modo`, o campo `fonte` do
`dashboard:status`, a variável de ambiente — e não do DOM para os olhos.

Consequência honesta: uma TV em modo demo não se distingue de uma TV em modo real para quem
olha a tela, e o critério 4 da auditoria ("visualmente identificável") ficou mais fraco em
identificação, não em isolamento — os dados continuam incapazes de se misturar. Antes de
apresentar o demo para um público que também vê números reais, revalide essa troca. Fazer o
badge voltar é barato: um `{% if demo %}` no `templates/dash.html` reaproveitando a classe
âmbar `.selo--alerta`, e inverter `test_o_demo_nao_ganha_badge_na_tela`.

## Como os dados sintéticos são gerados

`services/showcase.py` sorteia a partir de uma semente `SHA-256(recorte | chave | período)`.
Consequências deliberadas:

- o mesmo instante produz sempre o mesmo painel — a tela não "pisca" números;
- os rankings mudam de mês, não de ciclo: um supervisor não troca de posição sem motivo;
- o total do dia e as séries crescem com a fração da jornada (07:00–19:00), então uma
  apresentação de dez minutos mostra o painel andando;
- a série do dia termina exatamente no `totalDia` exibido, e o gráfico do mês anterior tem
  tantos dias quantos o mês corrente.

Nada aqui lê ou escreve banco, chamadas HTTP ou arquivos. Há um teste que procura
`utils.db`, `db.session`, `requests`, `utils.actions` e `brapi` no arquivo e falha se
alguém incluir.

## Por que não contamina os dados reais

A escolha da fonte acontece uma vez, no `create_app`, e vai para
`app.config["VISTA_FONTE"]`. Rotas (`routes/*.py`) e o ciclo de tempo real perguntam a essa
chave; não há um caminho que decida por conta própria. Por isso:

- um app em modo demo não consegue consultar o warehouse — o teste
  `test_as_rotas_de_demo_nao_tocam_o_banco` monkeypatch `db.session.execute` para falhar o
  teste e serve as rotas normalmente;
- um app real não consegue servir dado sintético — o teste espelho confirma que a mesma
  rota executa SQL contra `TAREFA`.

Os dados sintéticos nunca são persistidos: não há escrita em banco, arquivo ou cache
compartilhado.

## Auditoria do repositório `VistaView_Showcase`

Comparado arquivo a arquivo com o Vista View (out/2026):

| Showcase | Situação no repositório principal |
|---|---|
| `css/dash.css` | idêntico a `static/css/dash.css` |
| `img/*` | idênticos a `static/img/*` |
| `index.html` | equivalente ao `templates/dash.html` antigo (mesmos `id`s); o layout novo da Fase 3 substitui a página |
| `js/chart_ex.js` | presente em `static/js/chart_ex.js`, só que com a série de exemplo truncada em 2 pontos |

Nenhuma regra de negócio, rota ou indicador exclusivo do Showcase deixou de existir aqui.
A única diferença real era a série mock de 7 dias do `chart_ex.js`, que o modo demo
substitui por dados sintéticos vivos e coerentes. O repositório `VistaView_Showcase` não
foi alterado nem removido.

`templates/Example.html` (rota `/showcase`) continua no ar como referência visual do
layout antigo; ele não carrega `chart_ex.js`. Remover a rota é decisão à parte, porque o
uso por terceiros não foi verificado.
