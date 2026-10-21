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

    // ---------------------------------------------------------------- faixa de unidades
    /* Rodapé em movimento contínuo, sem a tag HTML antiga: um grupo de chips é repetido
     * em cópias idênticas e o CSS transla meia largura do trilho — com número par de
     * cópias, isso é exatamente um período, então não aparece emenda. Os números são
     * trocados no lugar, porque reconstruir o trilho a cada ciclo devolveria a faixa ao
     * início. */
    let faixaEstado = null;

    function montarGrupo(itens) {
        const grupo = document.createElement('div');
        grupo.className = 'faixa__grupo';
        const cifras = [];
        itens.forEach(function (item) {
            const chip = document.createElement('span');
            chip.className = 'rodape__item';
            chip.textContent = item.nome + ' ' + item.total;
            cifras.push(chip);
            grupo.appendChild(chip);
        });
        return { elemento: grupo, cifras: cifras };
    }

    function faixaParada(trilho, mensagem) {
        faixaEstado = null;
        trilho.style.removeProperty('--duracao');
        trilho.textContent = '';
        const grupo = document.createElement('div');
        grupo.className = 'faixa__grupo';
        const vazio = document.createElement('span');
        vazio.className = 'rodape__vazio';
        vazio.textContent = mensagem;
        grupo.appendChild(vazio);
        trilho.appendChild(grupo);
    }

    function dimensionarFaixa(faixa, trilho) {
        if (!faixaEstado) return;
        const periodo = faixaEstado.grupos[0].elemento.offsetWidth;
        const janela = faixa.clientWidth || document.documentElement.clientWidth;
        if (!periodo || !janela) return;

        const tudoVisivel = periodo <= janela;
        // Cópias em par quando a faixa anda: é o que faz translateX(-50%) cair na
        // borda de um período. Parada, uma cópia só basta.
        let alvo;
        if (tudoVisivel) {
            alvo = 1;
        } else {
            alvo = Math.max(2, Math.ceil(janela / periodo) + 1);
            if (alvo % 2) alvo += 1;
        }

        faixa.classList.toggle('faixa--parada', tudoVisivel);

        const grupos = faixaEstado.grupos;
        while (grupos.length < alvo) {
            const copia = montarGrupo(faixaEstado.itens);
            trilho.appendChild(copia.elemento);
            grupos.push(copia);
        }
        while (grupos.length > alvo) {
            trilho.removeChild(grupos.pop().elemento);
        }

        if (tudoVisivel) {
            trilho.style.removeProperty('--duracao');
            faixaEstado.duracao = null;
            return;
        }

        // Velocidade em função da própria faixa: ela já escala com a tela, e medir a
        // janela sairia zero numa aba em segundo plano.
        const velocidade = Math.max(26, Math.round(janela * 0.03));
        const duracao = (periodo * grupos.length / 2) / velocidade;
        // Só mexe na duração se ela mudou de verdade: ajustar a cada ciclo faria o
        // movimento saltar, porque a animação é medida em tempo, não em progresso.
        const anterior = faixaEstado.duracao;
        if (anterior === null || Math.abs(duracao - anterior) / anterior > 0.05) {
            trilho.style.setProperty('--duracao', duracao.toFixed(2) + 's');
            faixaEstado.duracao = duracao;
        }
    }

    function pintarRodape(p) {
        const faixa = $('faixaUnidades');
        const trilho = faixa ? faixa.querySelector('.faixa__trilho') : null;
        if (!trilho) return;

        const nomes = (p.unidades && p.unidades.uni) || [];
        const totais = (p.unidades && p.unidades.total) || [];
        if (nomes.length === 0) {
            faixaParada(trilho, 'sem unidades no recorte');
            return;
        }

        const itens = nomes.slice(0, 60).map(function (nome, i) {
            return { nome: nome || '—', total: numero(totais[i]) };
        });
        const assinatura = itens.map(function (i) { return i.nome; }).join('|');

        if (!faixaEstado || faixaEstado.assinatura !== assinatura) {
            trilho.textContent = '';
            faixaEstado = { assinatura: assinatura, itens: itens, grupos: [], duracao: null };
            const primeiro = montarGrupo(itens);
            trilho.appendChild(primeiro.elemento);
            faixaEstado.grupos.push(primeiro);
        } else {
            faixaEstado.grupos.forEach(function (grupo) {
                grupo.cifras.forEach(function (chip, i) {
                    chip.textContent = itens[i].nome + ' ' + itens[i].total;
                });
            });
        }
        dimensionarFaixa(faixa, trilho);
    }

    // ---------------------------------------------------------------- gráficos
    let graficoDias = null;
    let graficoDesempenho = null;

    function criarGraficos() {
        if (typeof Chart === 'undefined') return;
        Chart.defaults.color = CORES.suave;
        Chart.defaults.borderColor = CORES.grade;
        Chart.defaults.font.size = 13;
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
            // Na rota antiga `0` quer dizer "sem valor", não preço de centavo: sem cifra,
            // o cartão entra no estado indisponível, com traço.
            const valor = Number(preco);
            pintarCotacoes(valor ? [{ simbolo: 'GGPS3', preco: 'R$ ' + valor.toFixed(2).replace('.', ','), variacao: null, atual: true }]
                                 : [{ simbolo: 'GGPS3', preco: null, variacao: null, indisponivel: true }]);
        } catch (e) {
            if (janelaPainel.cotacoes) return;
            console.warn('[painel] cotação indisponível:', e);
            pintarCotacoes([]);
        }
    }

    // ---------------------------------------------------------------- estado
    /* Uma tag só na barra: o que importa para quem olha de longe é se o painel está
     * recebendo pelo socket. O estado vem da conexão real, não da disponibilidade da
     * interface. A cor do ponto ainda avisa, sem texto extra, quando o ciclo do
     * servidor está degradado. */
    const ESTADOS = {
        iniciando: ['Offline', 'selo--neutro'],
        conectado: ['Online', 'selo--on'],
        desconectado: ['Offline', 'selo--off'],
        reconectando: ['Offline', 'selo--off selo--alerta'],
        indisponivel: ['Offline', 'selo--off'],
    };

    let conexao = 'iniciando';
    let cicloDegradado = false;

    function pintarSeloConexao() {
        const selo = $('seloConexao');
        if (!selo) return;
        const [texto, classe] = ESTADOS[conexao] || ESTADOS.desconectado;
        const classes = ['selo', classe];
        if (conexao === 'conectado' && cicloDegradado) classes.push('selo--degradado');
        selo.className = classes.join(' ');
        selo.dataset.conexao = conexao;
        selo.textContent = '';

        const ponto = document.createElement('span');
        ponto.className = 'selo__ponto';
        const rotulo = document.createElement('span');
        rotulo.textContent = texto;
        selo.append(ponto, rotulo);
    }

    function pintarEstado(nome) {
        conexao = nome in ESTADOS ? nome : 'desconectado';
        pintarSeloConexao();
    }

    function pintarStatus(st) {
        cicloDegradado = !!(st && st.degradado);
        sincronizarRelogio(st && st.emitidoEm);
        pintarSeloConexao();
    }

    // ---------------------------------------------------------------- relógio
    /* Referência é o relógio do servidor: cada evento de status traz o instante em que
     * foi emitido e a página guarda apenas o deslocamento entre os dois relógios. Entre
     * um evento e outro a tela anda sozinha — nenhuma requisição a mais por segundos. */
    let deslocamentoMs = 0;

    function sincronizarRelogio(instante) {
        if (!instante) return;
        const ms = Date.parse(String(instante).replace(' ', 'T'));
        if (Number.isNaN(ms)) return;
        deslocamentoMs = ms - Date.now();
    }

    function iniciarRelogio() {
        const relogio = $('relogio');
        const data = $('dataCabecalho');
        function tick() {
            const agora = new Date(Date.now() + deslocamentoMs);
            if (relogio) {
                relogio.textContent = agora.toLocaleTimeString('pt-BR', {
                    hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit',
                });
            }
            if (data) {
                data.textContent = agora.toLocaleDateString('pt-BR', {
                    weekday: 'short', day: '2-digit', month: 'long',
                });
            }
        }
        tick();
        setInterval(tick, 1000);
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

    /* O cabeçalho HTTP já traz a hora do servidor em toda resposta que a página faz por
     * outro motivo: sem socket, é por ela que o relógio se alinha. Precisão de um
     * segundo é mais que suficiente para um painel visto de longe. */
    function alinharPeloCabecalho(resposta) {
        sincronizarRelogio(resposta.headers.get('Date'));
    }

    async function porRota(chave) {
        const resposta = await fetch(ROTAS[chave] + encodeURIComponent(painelOpt) + '/' + encodeURIComponent(painelGr));
        if (!resposta.ok) throw new Error(chave + ': HTTP ' + resposta.status);
        alinharPeloCabecalho(resposta);
        return resposta.json();
    }

    /* Cotação é igual para qualquer recorte e vem do cache de um processo compartilhado,
     * então não entra no mapa de indicadores: tem rota e formato próprios. */
    async function porCotacoes() {
        const resposta = await fetch('/actions/cotacoes/');
        if (!resposta.ok) throw new Error('cotações: HTTP ' + resposta.status);
        alinharPeloCabecalho(resposta);
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
        const trilho = document.querySelector('#faixaUnidades .faixa__trilho');
        if (trilho && !faixaEstado) faixaParada(trilho, 'sem dados no momento');
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

    // Troca de resolução na TV (ou janela em modo desenvolvimento) redimensiona a faixa.
    let ajuste = null;
    window.addEventListener('resize', function () {
        clearTimeout(ajuste);
        ajuste = setTimeout(function () {
            const faixa = $('faixaUnidades');
            if (faixa && faixaEstado) dimensionarFaixa(faixa, faixa.querySelector('.faixa__trilho'));
        }, 300);
    });

    window.VistaPainel = { pintar: pintar, recarregarPorHttp: recarregarPorHttp };
})();
