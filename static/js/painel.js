/*
 * Renderizador do painel para TV.
 *
 * Desenha o payload de `services.metricas.painel` — a mesma forma que o Socket.IO entrega
 * e que o caminho HTTP individual entrega. Não refaz gráficos nem listas do zero: atualiza
 * os objetos já criados, para que a tela não pisca a cada ciclo.
 */
(function () {
    const $ = function (id) { return document.getElementById(id); };

    const CORES = {
        verde: '#57c785',
        vermelho: '#e5484d',
        ambar: '#f0a92c',
        azul: '#3d9be9',
        suave: '#9fb0c1',
        grade: '#2a3745',
    };

    // Chave do payload -> id do cartão na página.
    const KPIs = {
        totalMes: 'kpi-totalMes',
        totalDia: 'kpi-totalDia',
        visitasMes: 'kpi-visitasMes',
        visitasDia: 'kpi-visitasDia',
        metaMes: 'kpi-metaMes',
        metaDia: 'kpi-metaDia',
        gapMes: 'kpi-gapMes',
        gapDia: 'kpi-gapDia',
        escalonadas: 'kpi-escalonadas',
    };

    const SEMANTICA = {
        totalMes: 'info',
        totalDia: 'info',
        visitasMes: 'neutro',
        visitasDia: 'neutro',
        metaMes: 'neutro',
        metaDia: 'neutro',
        escalonadas: function (v) { return v > 0 ? 'erro' : 'ok'; },
        gapMes: function (v) { return v >= 0 ? 'ok' : 'erro'; },
        gapDia: function (v) { return v >= 0 ? 'ok' : 'erro'; },
    };

    function numero(valor) {
        if (valor === null || valor === undefined || Number.isNaN(Number(valor))) return '—';
        return Number(valor).toLocaleString('pt-BR');
    }

    function nomeCurto(nome) {
        const partes = String(nome || '').trim().split(/\s+/);
        if (partes.length < 2) return nome || '—';
        return partes[0] + ' ' + partes[partes.length - 1];
    }

    function classeSemantica(chave, valor) {
        const regra = SEMANTICA[chave];
        if (typeof regra === 'function') return regra(valor);
        return regra || 'neutro';
    }

    function pintarKpi(chave, id, valor) {
        const cartao = $(id);
        if (!cartao) return;
        const alvo = cartao.querySelector('.kpi__valor') || cartao;
        alvo.textContent = numero(valor);
        cartao.classList.remove('kpi--ok', 'kpi--erro', 'kpi--neutro', 'kpi--info');
        cartao.classList.add('kpi--' + classeSemantica(chave, valor));
    }

    // ---------------------------------------------------------------- listas
    function pintarLista(id, nomes, totais, abreviar) {
        const ul = $(id);
        if (!ul) return;
        nomes = nomes || [];
        totais = totais || [];
        ul.textContent = '';

        if (nomes.length === 0) {
            const vazio = document.createElement('li');
            vazio.className = 'lista__vazio';
            vazio.textContent = 'Sem registros no período';
            ul.appendChild(vazio);
            return;
        }

        nomes.forEach(function (nome, i) {
            const li = document.createElement('li');
            li.className = 'lista__item';

            const posicao = document.createElement('span');
            posicao.className = 'lista__posicao';
            posicao.textContent = String(i + 1);

            const rotulo = document.createElement('span');
            rotulo.className = 'lista__nome';
            rotulo.textContent = abreviar ? nomeCurto(nome) : (nome || '—');

            const valor = document.createElement('span');
            valor.className = 'lista__valor';
            valor.textContent = numero(totais[i]);

            li.append(posicao, rotulo, valor);
            ul.appendChild(li);
        });
    }

    function pintarRodape(p) {
        const rodape = $('rodapeUnidades');
        if (!rodape) return;
        const uni = (p.unidades && p.unidades.uni) || [];
        const totais = (p.unidades && p.unidades.total) || [];
        rodape.textContent = '';

        const rotulo = document.createElement('span');
        rotulo.className = 'rodape__rotulo';
        rotulo.textContent = 'Unidades';
        rodape.appendChild(rotulo);

        if (uni.length === 0) {
            const vazio = document.createElement('span');
            vazio.className = 'rodape__vazio';
            vazio.textContent = 'sem unidades no recorte';
            rodape.appendChild(vazio);
            return;
        }

        uni.slice(0, 24).forEach(function (nome, i) {
            const item = document.createElement('span');
            item.className = 'rodape__item';
            item.textContent = (nome || '—') + ' ' + numero(totais[i]);
            rodape.appendChild(item);
        });
    }

    // ---------------------------------------------------------------- gráficos
    let graficoDias = null;
    let graficoDesempenho = null;

    function criarGraficos() {
        if (typeof Chart === 'undefined') return;
        Chart.defaults.color = CORES.suave;
        Chart.defaults.borderColor = CORES.grade;
        Chart.defaults.font.size = 14;
        Chart.defaults.animation = false;

        const dias = $('grafDias');
        if (dias) {
            graficoDias = new Chart(dias, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        { label: 'Mês anterior', data: [], borderColor: CORES.vermelho, borderWidth: 1, fill: false, pointRadius: 0 },
                        { label: 'Mês atual', data: [], borderColor: CORES.verde, borderWidth: 2, fill: { target: 'origin' }, backgroundColor: 'rgba(87,199,133,.12)', pointRadius: 0 },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { boxWidth: 12 } } },
                    scales: { x: { title: { display: true, text: 'Dia do mês' } }, y: { beginAtZero: true } },
                },
            });
        }

        const desempenho = $('grafDesempenho');
        if (desempenho) {
            graficoDesempenho = new Chart(desempenho, {
                type: 'doughnut',
                data: { labels: [], datasets: [{ data: [], borderWidth: 1, borderColor: CORES.grade, backgroundColor: [CORES.vermelho, CORES.verde] }] },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '62%',
                    plugins: { legend: { display: false } },
                },
            });
        }
    }

    function pintarGraficoDias(dias, diasAnt) {
        if (!graficoDias) return;
        graficoDias.data.labels = (dias && dias.dia) || [];
        graficoDias.data.datasets[0].data = (diasAnt && diasAnt.total) || [];
        graficoDias.data.datasets[1].data = (dias && dias.total) || [];
        graficoDias.update('none');
    }

    function pintarDesempenho(perf) {
        const total = ((perf && perf.total) || []).reduce(function (a, b) { return a + Number(b || 0); }, 0);
        const legenda = $('descLegenda');

        if (graficoDesempenho) {
            graficoDesempenho.data.labels = (perf && perf.st) || [];
            graficoDesempenho.data.datasets[0].data = (perf && perf.total) || [];
            graficoDesempenho.update('none');
        }
        if (!legenda) return;
        legenda.textContent = '';

        ((perf && perf.st) || []).forEach(function (rotulo, i) {
            const valor = Number((perf.total || [])[i] || 0);
            const percentual = total ? ((valor * 100) / total).toFixed(1) : '0.0';
            const linha = document.createElement('div');
            linha.className = 'desc__linha';

            const nome = document.createElement('span');
            nome.textContent = rotulo;
            nome.style.color = rotulo === 'NO PRAZO' ? CORES.verde : CORES.vermelho;

            const cifra = document.createElement('span');
            cifra.textContent = numero(valor) + ' · ' + percentual + '%';

            linha.append(nome, cifra);
            legenda.appendChild(linha);
        });
    }

    // ---------------------------------------------------------------- cotações
    // Fase 7 alimenta esta lista; enquanto não há provedor, o cartão fica discreto.
    function pintarCotacoes(lista) {
        const alvo = $('listaCotacoes');
        if (!alvo) return;
        alvo.textContent = '';

        if (!lista || lista.length === 0) {
            const vazio = document.createElement('div');
            vazio.className = 'lista__vazio';
            vazio.textContent = 'cotações indisponíveis';
            alvo.appendChild(vazio);
            return;
        }

        lista.forEach(function (c) {
            const item = document.createElement('div');
            item.className = 'cotacao';
            if (typeof c.variacao === 'number') {
                item.classList.add(c.variacao >= 0 ? 'cotacao--subiu' : 'cotacao--desceu');
            }
            if (c.indisponivel) item.classList.add('cotacao--indisponivel');
            else item.classList.add(c.atual === false ? 'cotacao--velha' : 'cotacao--atual');

            const simbolo = document.createElement('span');
            simbolo.className = 'cotacao__simbolo';
            simbolo.textContent = c.simbolo || '—';

            const preco = document.createElement('span');
            preco.className = 'cotacao__preco';
            preco.textContent = c.preco == null ? '—' : String(c.preco);

            const variacao = document.createElement('span');
            variacao.className = 'cotacao__var';
            variacao.textContent = c.variacao == null ? '' : (c.variacao > 0 ? '+' : '') + c.variacao + '%';

            const hora = document.createElement('span');
            hora.className = 'cotacao__hora';
            hora.textContent = c.cotizadoEm || '';

            item.append(simbolo, preco, variacao, hora);
            alvo.appendChild(item);
        });
    }

    // O valor da ação já era mostrado (badge GGPS3) e vem de `/actions/value/`.
    // A faixa de até cinco símbolos chega pelo snapshot ou por `/actions/cotacoes/`;
    // este caminho só pinta quando nenhum dos dois respondeu ainda.
    async function buscarValorAcao() {
        try {
            const resposta = await fetch('/actions/value/');
            if (!resposta.ok) throw new Error('HTTP ' + resposta.status);
            const preco = await resposta.json();
            if (janelaPainel.cotacoes) return;
            pintarCotacoes([{ simbolo: 'GGPS3', preco: 'R$ ' + numero(preco), variacao: null, atual: true }]);
        } catch (e) {
            if (janelaPainel.cotacoes) return;
            console.warn('[painel] cotação indisponível:', e);
            pintarCotacoes([]);
        }
    }

    // ---------------------------------------------------------------- estado
    const ESTADOS = {
        iniciando: ['esperando conexão…', ''],
        conectado: ['tempo real ativo', 'selo--ok'],
        desconectado: ['sem conexão', 'selo--erro'],
        reconectando: ['reconectando…', 'selo--alerta'],
        indisponivel: ['modo consulta', 'selo--alerta'],
    };

    function pintarEstado(nome) {
        const selo = $('seloConexao');
        if (!selo) return;
        const [texto, classe] = ESTADOS[nome] || [nome, ''];
        selo.textContent = '';
        const ponto = document.createElement('span');
        ponto.className = 'selo__ponto';
        const rotulo = document.createElement('span');
        rotulo.textContent = texto;
        selo.append(ponto, rotulo);
        selo.className = 'selo' + (classe ? ' ' + classe : '');
    }

    function pintarStatus(st) {
        const selo = $('seloQualidade');
        if (selo) {
            selo.textContent = '';
            const ponto = document.createElement('span');
            ponto.className = 'selo__ponto';
            const rotulo = document.createElement('span');
            if (st && st.degradado) {
                rotulo.textContent = 'dados desatualizados (' + (st.falhasConsecutivas || 0) + ')';
                selo.className = 'selo selo--erro';
            } else {
                rotulo.textContent = 'dados no ar';
                selo.className = 'selo selo--ok';
            }
            selo.append(ponto, rotulo);
        }
    }

    function atualizadoHá(iso) {
        // `atualizadoEm` sai do servidor sem fuso: TV e servidor estão no mesmo horário.
        if (!iso) return '—';
        const instante = Date.parse(String(iso).replace(' ', 'T'));
        if (Number.isNaN(instante)) return '—';
        const segundos = Math.max(0, Math.round((Date.now() - instante) / 1000));
        if (segundos < 60) return 'atualizado há ' + segundos + 's';
        const minutos = Math.round(segundos / 60);
        if (minutos < 60) return 'atualizado há ' + minutos + 'min';
        return 'atualizado há ' + Math.round(minutos / 60) + 'h';
    }

    function iniciarRelogio() {
        const relogio = $('relogio');
        const data = $('dataCabecalho');
        function tick() {
            const agora = new Date();
            if (relogio) relogio.textContent = agora.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
            if (data) data.textContent = agora.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'long' });
            const marca = $('seloAtualizacao');
            if (marca && janelaPainel.atualizadoEm) {
                const alvo = marca.querySelector('.selo__rotulo') || marca;
                alvo.textContent = atualizadoHá(janelaPainel.atualizadoEm);
            }
        }
        tick();
        setInterval(tick, 15000);
    }

    // ---------------------------------------------------------------- pintura
    let janelaPainel = {};
    let recebeuDados = false;

    function pintar(p) {
        recebeuDados = true;
        janelaPainel = Object.assign({}, janelaPainel, p || {});

        Object.keys(KPIs).forEach(function (chave) {
            if (chave in janelaPainel) pintarKpi(chave, KPIs[chave], janelaPainel[chave]);
        });

        if (p.top3Uni) {
            pintarLista('listaTop3Uni', p.top3Uni.uni, p.top3Uni.total, false);
        }
        if (p.top3Sup) {
            pintarLista('listaTop3Sup', p.top3Sup.sup, p.top3Sup.total, true);
        }
        if (p.gerentes) {
            const limite = (p.gerentes.grs || []).slice(0, 8);
            const totais = (p.gerentes.total || []).slice(0, 8);
            pintarLista('listaGerentes', limite, totais, true);
        }
        if (p.performance) pintarDesempenho(p.performance);
        if (p.dias || p.diasAnt) pintarGraficoDias(p.dias, p.diasAnt);
        if (p.unidades) pintarRodape(p);
        if (p.cotacoes) pintarCotacoes(p.cotacoes);

        const marca = $('seloAtualizacao');
        if (marca && janelaPainel.atualizadoEm) {
            const alvo = marca.querySelector('.selo__rotulo') || marca;
            alvo.textContent = atualizadoHá(janelaPainel.atualizadoEm);
        }
    }

    // ---------------------------------------------------------------- HTTP
    /* Sem socket, o painel se comporta como a versão antiga: uma requisição por
     * indicador. A regra de meta vem do servidor via dataset, para que os dois
     * caminhos cheguem no mesmo número. */
    const ROTAS = {
        totalMes: '/tarefas/total/',
        totalDia: '/tarefas/dia/',
        visitasMes: '/visitas/mes/',
        visitasDia: '/visitas/dia/',
        escalonadas: '/tarefas/escalonadas/',
        mesAnterior: '/tarefas/mes/anterior/',
        performance: '/get_performance/',
        top3Uni: '/top3_uni/',
        top3Sup: '/top3_sups/',
        gerentes: '/get_gerentes/',
        unidades: '/get_unidades/',
        dias: '/graph_days/',
        diasAnt: '/graph_days_ant/',
    };

    async function porRota(chave) {
        const resposta = await fetch(ROTAS[chave] + encodeURIComponent(painelOpt) + '/' + encodeURIComponent(painelGr));
        if (!resposta.ok) throw new Error(chave + ': HTTP ' + resposta.status);
        return resposta.json();
    }

    /* Cotação é igual para qualquer recorte e vem do cache de um processo compartilhado,
     * então não entra no mapa de indicadores: tem rota e formato próprios. */
    async function porCotacoes() {
        const resposta = await fetch('/actions/cotacoes/');
        if (!resposta.ok) throw new Error('cotações: HTTP ' + resposta.status);
        return resposta.json();
    }

    /* Sem nenhuma cifra carregada, a TV não pode ficar com cartões mudos: é o estado em
     * que o painel fica enquanto o warehouse está fora do ar. */
    function pintarSemDados() {
        ['listaTop3Uni', 'listaTop3Sup', 'listaGerentes'].forEach(function (id) {
            const ul = $(id);
            if (ul && !ul.children.length) {
                const vazio = document.createElement('li');
                vazio.className = 'lista__vazio';
                vazio.textContent = 'sem dados no momento';
                ul.appendChild(vazio);
            }
        });
        const rodape = $('rodapeUnidades');
        if (rodape && !rodape.children.length) {
            const rotulo = document.createElement('span');
            rotulo.className = 'rodape__rotulo';
            rotulo.textContent = 'Unidades';
            const vazio = document.createElement('span');
            vazio.className = 'rodape__vazio';
            vazio.textContent = 'sem dados no momento';
            rodape.append(rotulo, vazio);
        }
    }

    async function recarregarPorHttp() {
        const chaves = Object.keys(ROTAS);
        const resultados = await Promise.allSettled(chaves.map(porRota));
        const p = {};
        resultados.forEach(function (r, i) {
            if (r.status !== 'fulfilled') {
                console.warn('[painel] indicador indisponível:', chaves[i], r.reason);
                return;
            }
            const valor = r.value;
            // `/tarefas/escalonadas` embrulha em {"total": n}; o payload do socket não.
            p[chaves[i]] = (chaves[i] === 'escalonadas' && valor && typeof valor === 'object') ? valor.total : valor;
        });

        if (Object.keys(p).length === 0) {
            recebeuDados = false;
            pintarSemDados();
            return;
        }

        // Meta e gap só fazem sentido com a cifra de que derivam; sem ela o cartão
        // mostraria "0" como se fosse uma meta batida.
        if ('mesAnterior' in p) {
            p.metaMes = Math.round(Number(p.mesAnterior) * (1 + painelMeta / 100));
            const agora = new Date();
            const diasNoMes = new Date(agora.getFullYear(), agora.getMonth() + 1, 0).getDate();
            p.metaDia = Math.round(p.metaMes / Math.max(diasNoMes - agora.getDate(), 1));
            if ('totalMes' in p) p.gapMes = Number(p.totalMes) - p.metaMes;
            if ('totalDia' in p) p.gapDia = Number(p.totalDia) - p.metaDia;
        }
        try {
            p.cotacoes = await porCotacoes();
        } catch (e) {
            console.warn('[painel] cotações indisponíveis:', e);
        }
        p.atualizadoEm = new Date().toISOString();
        pintar(p);
    }

    // ---------------------------------------------------------------- entrada
    const painelOpt = document.body.dataset.opt || 'GR';
    const painelGr = document.body.dataset.gr || '';
    const painelMeta = Number(document.body.dataset.meta || 15);

    criarGraficos();
    iniciarRelogio();
    pintarEstado('iniciando');
    buscarValorAcao();

    const tempoReal = window.VistaTempoReal;
    if (tempoReal) {
        tempoReal.on('snapshot', pintar);
        tempoReal.on('atualizacao', pintar);
        tempoReal.on('status', pintarStatus);
        tempoReal.on('estado', function (nome) {
            pintarEstado(nome);
            if (nome === 'indisponivel') recarregarPorHttp();
        });
        tempoReal.conectar();
    } else {
        pintarEstado('indisponivel');
        recarregarPorHttp();
    }

    // Sem snapshot em alguns segundos, o socket provavelmente não vai chegar.
    setTimeout(function () {
        if (!recebeuDados) recarregarPorHttp();
    }, 8000);

    window.VistaPainel = { pintar: pintar, recarregarPorHttp: recarregarPorHttp };
})();
