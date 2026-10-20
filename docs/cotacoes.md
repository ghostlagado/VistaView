# Provedores de cotações — comparação e escolha (fase 6)

Documento exigido pelo brief: **comparar os provedores gratuitos antes de escolher e
justificar a escolha antes de implementar**. Todos os números abaixo são medições reais
feitas em 2026-10-20, a partir desta máquina, durante o pregão da B3 (15:00 horário local,
18:00 UTC). Nada aqui é estimado de documentação quando houve teste disponível — quando não
houve, está marcado.

## O que motivou a comparação

O código atual (`utils/actions.py`) chama
`https://brapi.dev/api/v2/stocks/quote?symbols=GGPS3` com `Authorization: Bearer <ACTION_API>`.
Medido hoje, sem token, os dois endpoints da brapi respondem:

```
GET https://brapi.dev/api/quote/GGPS3                  401  0,20s  {"error":true,"code":"MISSING_TOKEN"}
GET https://brapi.dev/api/v2/stocks/quote?symbols=GGPS3 401  0,21s  {"error":true,"code":"MISSING_TOKEN"}
```

Ou seja: a brapi passou a exigir token inclusive no endpoint clássico. Isso explica as
falhas de `/actions/value/` que já apareciam na auditoria (fase 1) e significa que o
provedor em uso **não é mais gratuito sem cadastro** — é a primeira coisa que a comparação
precisava descobrir.

## Metodologia

- `curl` com `--max-time 12`, medindo `%{http_code} %{time_total}s %{size_download}b`.
- Símbolos-teste: `GGPS3` (B3, o ativo hoje configurado), `PETR4`/`VALE3` (B3), `AAPL`
  (internacional).
- Cada provedor foi testado sem credencial primeiro; os que exigem cadastro foram avaliados
  pelo que a própria página de planos/documentação declara, e isso está separado do que foi
  medido.
- Latência = tempo total da requisição, do `curl` ao primeiro byte completo, mesma rede.

## Comparativo

| critério | brapi.dev | Yahoo Finance (`query*.finance.yahoo.com`) | Stooq | Twelve Data | Finnhub | Alpha Vantage | FMP |
|---|---|---|---|---|---|---|---|
| **B3 (ações BR)** | ✅ medido (PETR4/VALE3/MGLU3/ITUB4 sem token; demais só com token) | ✅ medido com sufixo `.SA` (PETR4.SA, GGPS3.SA) | ❌ medido: `404` em `q/l/` para `ggps3.sa` e `aapl.us`, com e sem User-Agent | ⚠️ declarado: free tier **não** inclui B3 | ⚠️ não medido (exige key) | ⚠️ não medido (exige key) | ⚠️ não medido (exige key) |
| **internacional** | ❌ foco declarado no mercado brasileiro | ✅ medido: `AAPL` → 200, USD/NMS | — | ✅ | ✅ | ✅ | ✅ |
| **vários ativos em 1 chamada** | ✅ medido: `?symbols=PETR4,VALE3` → 200, 0,19s | ✅ medido: `v8/finance/spark?symbols=GGPS3.SA,PETR4.SA,AAPL` → 200 em 0,22s com os 3 símbolos | — | ✅ | ✅ | ❌ (1 símbolo/chamada em `GLOBAL_QUOTE`) | ✅ |
| **limite gratuito** | 15.000 req/mês (declarado); 4 ativos liberados sem token, "sem limite" (declarado) | não publicado; sem cota formal | não publicado | 800 req/dia, 8/min (declarado) | exige key (`401` medido) | exige key (declarado, 25 req/dia no free) | exige key (`401` medido: "Invalid API KEY") |
| **tempo real × atrasado** | ⚠️ **atrasado**: a página de planos declara atualização a cada 30 min no free. Medido: `regularMarketTime` = `2026-10-20T17:59:30Z` com 18:00:58Z no momento da consulta (~1,5 min). As duas coisas conflitam; ver "Consequência para o painel". | ⚠️ não garantido: endpoint não oficial, sem SLA | atrasado a EOD (não medido aqui) | forex/crypto em tempo real; ações atrasadas (declarado) | — | free com limite baixo | — |
| **autenticação** | token obrigatório (medido) | nenhuma (medido) | nenhuma | key | key | key | key |
| **estabilidade observada** | ✅ estável: 8 requisições, todas 200/401 esperados, 0,19–0,34s, sem bloqueio | ❌ **frágil**: funcionou na primeira sessão (6 chamadas `chart` seguidas → `200 200 200 200 200 200`, 0,33–0,57s) e depois passou a responder `429 "Edge: Too Many Requests"` em `query1` **e** `query2`, com e sem User-Agent de navegador, **inclusive após ~10 min de espera** | 404 consistente | — | — | — | — |
| **restrições de uso** | planos comerciais; atribuição/crédito no free (declarado no site) | termos de usuário da Yahoo: endpoint interno não documentado, sem licença de redistribuição | termos não verificados | uso não comercial no free | — | termo de uso | — |
| **campos úteis medidos** | `regularMarketPrice`, `regularMarketChange`, `regularMarketChangePercent`, `regularMarketPreviousClose`, `regularMarketTime`, `currency`, `longName`, e `requestedAt` no topo da resposta | `close`, `fulldayChange`, `fulldayChangePercent`, `fulldayPrice`, `previousClose`, `chartPreviousClose`, `timestamp`, `start`, `end`, `symbol`, `dataGranularity` (em `spark`) | — | — | — | — | — |

## Leitura dos números

1. **Nenhum provedor gratuito sozinho fecha o requisito.** O brief pede cobertura
   brasileira **e** internacional, atualização em tempo real e até cinco ativos. A brapi tem
   B3 boa, batch e cadência previsível, mas é atrasada e não cobre exterior. O Yahoo cobre
   os dois mercados em uma única chamada e não pede credencial, mas não tem cota publicada,
   não tem SLA, e nesta máquina ficou bloqueado em `429` por mais de dez minutos — um painel
   de TV que roda o dia inteiro não pode depender disso como fonte primária.
2. **Os provedores com planos gratuitos generosos e cobertura internacional exigem cadastro
   e não cobrem B3 no free** (Twelve Data: 800 req/dia, mas sem B3). Os que poderiam cobrir
   B3 com key (Alpha Vantage, FMP) têm cota gratuita baixa (25–250 req/dia), o que não
   sustenta um ciclo de 60 s: `5 símbolos × 1 chamada batch × 480 ciclos/dia = 480
   req/dia`, acima do Alpha Vantage e do FMP free.
3. **A matemática do free tier da brapi fecha.** Com token gratuito, 15.000 req/mês ÷ ~21
   dias úteis ≈ 700 req/dia. Um único processo compartilhado que faz **uma** chamada batch
   por ciclo, a cada 60 s, numa jornada de 8 h = 480 req/dia — cabe, com folga de ~30%.
   Isso só é verdade porque o design exige um ciclo compartilhado: se cada TV conectada
   chamasse o provedor, o limite estouraria no primeiro dia.
4. **Consequência direta para o painel:** nenhuma fonte gratuita é verificavelmente "tempo
   real", e a cadência declarada pela brapi (30 min) conflita com o timestamp medido
   (~1,5 min). O painel não pode afirmar ao gerente que o preço é de agora. A implementação
   deve, portanto, tratar **atualização atrasada como o caso normal** e mostrar o tempo do
   próprio provedor (`regularMarketTime`), marcando a cotação como desatualizada quando ele
   passar do limite configurado — em vez de fingir tempo real.

## Escolha

**Primária: brapi.dev, com token gratuito, um único processo compartilhado fazendo batch de
até 5 símbolos por ciclo.** Justificativa: é o único provedor gratuito cuja cobertura B3 foi
**medida funcionando** hoje, cuja cota gratuita é **publicada e compatível** com o ciclo de
60 s, que devolve todos os ativos em uma chamada, e que traz o `regularMarketTime` de cada
cotação — o campo que permite marcar o dado como velho em vez de mentir a frescura.

**Secundária (opcional, ligada por configuração): Yahoo `v8/finance/spark`.** É a única forma
de atender o requisito de cobertura internacional sem pagar. Fica desabilitada por padrão
porque a estabilidade medida foi ruim (`429` sustentado), e, quando habilitada, o painel a
trata como melhor esforço: um símbolo internacional que falhe aparece com a última cotação
válida e a marca de desatualizado, nunca como erro que derrube o cartão nem o ciclo.

**Descartados:** Stooq (404 em todos os formatos testados a partir desta rede), Twelve Data
(sem B3 no free), Finnhub/Alpha Vantage/FMP (exigem key; os dois últimos com cota gratuita
insuficiente para 60 s), IEX Cloud (desligado). Manter um deles como terceiro nível não
agrega: com duas fontes já há redundância suficiente para um painel de TV, e mais provedores
significam mais chaves, mais códigos de erro e mais superfície de falha.

### O que isso implica para o `ACTION_API` existente

O `.env.example` já prevê `ACTION_API`, e `utils/actions.py` já monta o header
`Authorization: Bearer`. A mudança é: validar o símbolo (`^[A-Z0-9]{4,6}[0-9]?$`, até 5,
configurável), checar `response.status_code` antes de `.json()` (hoje um `401` produz
`KeyError: 'results'` → 500), aplicar timeout, cache, retentativas com backoff e
preservar a última cotação válida. `ACTION_API` continua o mesmo nome de variável — nenhum
consumidor atual quebra, e o `GGPS3` que a tela já mostra volta a funcionar assim que o
token for colocado, já que sem token a brapi devolve 401 exatamente para ele.

## Persistência: decisão pendente, não implementada

O brief pede "persistar as cotações válidas e atualizar os metadados no MongoDB **após
verificar a compatibilidade com a infraestrutura existente**". A verificação foi feita:

- `requirements.txt` / `requirements-dev.txt`: sem `pymongo`, sem `motor`, sem `odm`.
- Busca por `mongo` no repositório (código, config, docs, compose): **nada**.
- Não há `docker-compose.yml` nem outro serviço de MongoDB declarado.
- A única persistência existente é SQLAlchemy sobre SQL Server `dw_vista`, que é um
  warehouse **compartilhado** com outras aplicações do GPS Vista.

Ou seja, o MongoDB **não existe nesta infraestrutura**. Introduzi-lo é instalar um serviço
novo, não "usar o que já há". E a alternativa — criar uma tabela de cotações no `dw_vista` —
é uma mudança de schema num banco compartilhado, o que o próprio brief coloca na lista de
ações que exigem aprovação. Nenhuma das duas foi feita. Enquanto a decisão não sai, a fase 7
persiste as cotações no processo (última válida + metadados de tempo/provedor) e o painel
funciona: o requisito de "manter a última cotação válida e marcar quando estiver
desatualizada" não depende de banco.

As opções, para escolha:

1. **Só memória** (zero risco, zero infra; a última cotação se perde a cada restart do
   serviço — no restart o painel mostra o selo "consulta" até o próximo ciclo, que chega em
   segundos).
2. **MongoDB** como o brief sugere — exige decisão sobre onde ele roda (instância nova,
   self-hosted ou gerenciada; as gratuitas têm limite de escrita e de rede).
3. **Tabela no SQL Server `dw_vista`** — aproveita o que já existe, mas é uma mudança de
   schema em banco compartilhado e o warehouse não foi feito para escrita de alta frequência.

## O que ainda não foi validado

- O comportamento da brapi **com** token (cota real, cadência real de atualização,
  cobertura além dos 4 símbolos liberados). Só um token gratuito cadastrado permitiria
  medir — e é exatamente a escolha que depende do item de persistência/configuração.
- Se `GGPS3` volta a responder com token (a hipótese é que sim: o `401` é por token ausente,
  não por símbolo inexistente, já que `PETR4` na mesma chamada responde `200`).
- Cadência de recuperação do `429` do Yahoo (medido: seguisse em `429` depois de ~10 min).
