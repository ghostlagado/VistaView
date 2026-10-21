/*
 * Renderizador do painel para TV.
 *
 * Desenha o payload de `painel()` da fonte ativa (`IndicadoresWarehouse` ou
 * `IndicadoresDemonstracao`) — a mesma forma que o Socket.IO entrega
 * e que o caminho HTTP individual entrega. Não refaz gráficos nem listas do zero: atualiza
 * os objetos já criados, para que a tela não pisca a cada ciclo.
 */
(function () {
    const $ = function (id) { return document.getElementById(id); };

    // Mesma escada de cor do painel.css: o gráfico não pode ter paleta própria.
    const CORES = {
        verde: '#3ecf8e',
        vermelho: '#f0555f',
        ambar: '#e7b04a',
        azul: '#4fa3f7',
        marca: '#14b8a6',
        texto: '#e9f1fa',
        suave: '#94a8bc',
        mudo: '#62778d',
        grade: 'rgba(226,238,250,.07)',
        superficie: '#131c26',
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

    /* Gap é desvio, e desvio sem sinal lê-se como grandeza. O número continua o mesmo do
     * payload; só o sinal aparece na tela. */
    function numeroAssinado(valor) {
        const n = Number(valor);
        if (Number.isNaN(n) || valor === null || valor === undefined) return '—';
        return (n > 0 ? '+' : n < 0 ? '-' : '') + numero(Math.abs(n));
    }

    function percentualDe(parte, todo) {
        if (!Number(todo)) return null;
        return Math.round((Number(parte || 0) * 100) / Number(todo));
    }

    /* Preço de ação tem moeda e duas casas — o número cru do provedor não diz R$ nem
     * centavo. String já vem formatada de `/actions/value/`, e passa como está. */
    function formatarPreco(preco) {
        if (preco === null || preco === undefined || preco === '') return '—';
        if (typeof preco === 'string') return preco;
        const n = Number(preco);
        if (Number.isNaN(n)) return '—';
        return 'R$ ' + n.toFixed(2).replace('.', ',');
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

    /* A nota responde o que o número sozinho deixa no ar. Tudo sai de cifra que já está
     * no payload — nenhuma conta nova, nenhum dado que o servidor não mandou. */
    function notaDe(chave, p) {
        const metaMes = Number(p.metaMes || 0);
        const metaDia = Number(p.metaDia || 0);
        switch (chave) {
            case 'totalMes': return metaMes ? percentualDe(p.totalMes, metaMes) + '% da meta' : '';
            case 'totalDia': return metaDia ? percentualDe(p.totalDia, metaDia) + '% da meta de hoje' : '';
            case 'visitasMes': return p.totalMes ? percentualDe(p.visitasMes, p.totalMes) + '% das tarefas' : '';
            case 'visitasDia': return p.totalDia ? percentualDe(p.visitasDia, p.totalDia) + '% das tarefas' : '';
            case 'metaMes': return p.mesAnterior != null ? 'mês anterior ' + numero(p.mesAnterior) : '';
            case 'metaDia': return metaMes ? 'meta do mês ' + numero(metaMes) : '';
            case 'gapMes': return metaMes ? 'contra a meta ' + numero(metaMes) : '';
            case 'gapDia': return metaDia ? 'contra a meta ' + numero(metaDia) : '';
            case 'escalonadas': return p.totalMes ? percentualDe(p.escalonadas, p.totalMes) + '% do total do mês' : '';
            default: return '';
        }
    }

    function pintarKpi(chave, id, valor, painel) {
        const cartao = $(id);
        if (!cartao) return;
        const alvo = cartao.querySelector('.kpi__valor') || cartao;
        alvo.textContent = chave.startsWith('gap') ? numeroAssinado(valor) : numero(valor);
        const nota = cartao.querySelector('.kpi__nota');
        if (nota) nota.textContent = notaDe(chave, painel || {});
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

        // A barra é relativa ao maior valor da própria lista: o que se quer ler é a
        // distância entre os primeiros, não a distância até um teto arbitrário.
        const maior = Math.max.apply(null, totais.map(Number).concat([1]));

        nomes.forEach(function (nome, i) {
            const li = document.createElement('li');
            li.className = 'lista__item' + (i === 0 ? ' lista__item--primeiro' : '');

            const posicao = document.createElement('span');
            posicao.className = 'lista__posicao';
            posicao.textContent = String(i + 1);

            const rotulo = document.createElement('span');
            rotulo.className = 'lista__nome';
            rotulo.textContent = abreviar ? nomeCurto(nome) : (nome || '—');
            rotulo.title = nome || '';

            const valor = document.createElement('span');
            valor.className = 'lista__valor';
            valor.textContent = numero(totais[i]);

            const barra = document.createElement('span');
            barra.className = 'lista__barra';
            barra.style.width = Math.round((Number(totais[i]) || 0) * 100 / maior) + '%';

            li.append(posicao, rotulo, valor, barra);
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

            const nome = document.createElement('span');
            nome.className = 'rodape__nome';
            nome.textContent = item.nome;

            // A cifra em destaque, o nome em suporte: na faixa é o número que se persegue.
            const total = document.createElement('span');
            total.className = 'rodape__total';
            total.textContent = item.total;

            chip.append(nome, total);
            cifras.push(total);
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
                grupo.cifras.forEach(function (cifra, i) {
                    cifra.textContent = itens[i].total;
                });
            });
        }
        dimensionarFaixa(faixa, trilho);
    }

    // ---------------------------------------------------------------- gráficos
    let graficoDias = null;
    let graficoDesempenho = null;

    /* Um tooltip só para os dois gráficos: superfície elevada, borda de um pixel, número
     * em tabular — a mesma linguagem dos cartões. */
    const TOOLTIP = {
        backgroundColor: CORES.superficie,
        borderColor: 'rgba(226,238,250,.14)',
        borderWidth: 1,
        titleColor: CORES.texto,
        bodyColor: CORES.suave,
        padding: 10,
        cornerRadius: 8,
        usePointStyle: true,
        boxWidth: 8,
        boxHeight: 8,
        boxPadding: 4,
        callbacks: {
            label: function (item) {
                const rotulo = item.dataset.label ? item.dataset.label + ': ' : '';
                const valor = typeof item.parsed === 'object' ? item.parsed.y : item.parsed;
                return '  ' + rotulo + numero(valor);
            },
        },
    };

    /* Verde é prazo cumprido, vermelho é atraso: as outras cores do painel não comunicam
     * estado. O rótulo chega do banco em caixa alta e a tela o apresenta em caixa de frase. */
    function corDePrazo(rotulo) {
        const t = String(rotulo || '').trim().toUpperCase();
        return t.indexOf('NO PRAZO') === 0 ? CORES.verde : CORES.vermelho;
    }

    function caixaDeFrase(rotulo) {
        const t = String(rotulo || '').trim().toLowerCase();
        return t ? t.charAt(0).toUpperCase() + t.slice(1) : '—';
    }

    function criarGraficos() {
        if (typeof Chart === 'undefined') return;
        Chart.defaults.color = CORES.suave;
        Chart.defaults.borderColor = CORES.grade;
        Chart.defaults.font.family = 'Inter, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
        Chart.defaults.font.size = 13;
        Chart.defaults.animation = false;

        const dias = $('grafDias');
        if (dias) {
            // A área do mês atual desce a zero: sem ela as duas linhas se cruzam e a de
            // trás some, que é justamente o que se quer comparar.
            const area = dias.getContext('2d').createLinearGradient(0, 0, 0, dias.clientHeight || 400);
            area.addColorStop(0, 'rgba(79,163,247,.26)');
            area.addColorStop(1, 'rgba(79,163,247,0)');

            graficoDias = new Chart(dias, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        { label: 'Mês anterior', data: [], borderColor: CORES.mudo, borderWidth: 1.5,
                          borderDash: [5, 4], tension: .35, pointRadius: 0, pointHoverRadius: 3, fill: false },
                        { label: 'Mês atual', data: [], borderColor: CORES.azul, borderWidth: 2.5,
                          tension: .35, pointRadius: 0, pointHoverRadius: 4, pointBackgroundColor: CORES.azul,
                          pointBorderColor: CORES.superficie, pointBorderWidth: 2, fill: true, backgroundColor: area },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: {
                            position: 'top', align: 'end',
                            labels: { usePointStyle: false, boxWidth: 18, boxHeight: 2,
                                      padding: 18, color: CORES.suave },
                        },
                        tooltip: TOOLTIP,
                    },
                    scales: {
                        x: {
                            grid: { display: false }, border: { color: CORES.grade },
                            ticks: { color: CORES.mudo, maxRotation: 0, autoSkipPadding: 10 },
                            title: { display: true, text: 'Dia do mês', color: CORES.mudo, font: { size: 11 } },
                        },
                        y: {
                            beginAtZero: true, grid: { color: CORES.grade, drawTicks: false },
                            border: { display: false },
                            ticks: { color: CORES.mudo, padding: 8, precision: 0, maxTicksLimit: 7 },
                        },
                    },
                },
            });
        }

        const desempenho = $('grafDesempenho');
        if (desempenho) {
            // Sem rótulo dentro do anel: o total mora no furo (`.desc__centro`), e a
            // legenda ao lado carrega valor e percentual.
            graficoDesempenho = new Chart(desempenho, {
                type: 'doughnut',
                data: { labels: [], datasets: [{ data: [], borderWidth: 0, spacing: 2, backgroundColor: [] }] },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '74%',
                    plugins: { legend: { display: false }, tooltip: TOOLTIP },
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
        const rotulos = (perf && perf.st) || [];
        const valores = (perf && perf.total) || [];
        const total = valores.reduce(function (a, b) { return a + Number(b || 0); }, 0);
        const legenda = $('descLegenda');

        if (graficoDesempenho) {
            graficoDesempenho.data.labels = rotulos;
            graficoDesempenho.data.datasets[0].data = valores;
            graficoDesempenho.data.datasets[0].backgroundColor = rotulos.map(corDePrazo);
            graficoDesempenho.update('none');
        }

        const centro = $('descTotal');
        if (centro) centro.textContent = total ? numero(total) : '—';

        if (!legenda) return;
        legenda.textContent = '';

        rotulos.forEach(function (rotulo, i) {
            const valor = Number(valores[i] || 0);
            const linha = document.createElement('div');
            linha.className = 'desc__linha';

            const ponto = document.createElement('span');
            ponto.className = 'desc__ponto';
            ponto.style.color = corDePrazo(rotulo);

            const nome = document.createElement('span');
            nome.className = 'desc__titulo';
            nome.textContent = caixaDeFrase(rotulo);

            const cifra = document.createElement('span');
            cifra.className = 'desc__cifra';
            cifra.textContent = numero(valor) + ' · ' + (total ? ((valor * 100) / total).toFixed(1) : '0.0') + '%';

            linha.append(ponto, nome, cifra);
            legenda.appendChild(linha);
        });
    }

    // ---------------------------------------------------------------- cotações
    // Fase 7 alimenta esta lista; enquanto não há provedor, o cartão fica discreto.
    function peCotacoes(lista) {
        const pe = document.createElement('div');
        pe.className = 'cotacoes__pe';
        const comPreco = lista.filter(function (c) { return !c.indisponivel; });
        const parte = [];
        if (lista[0] && lista[0].provedor) parte.push(lista[0].provedor);
        parte.push(comPreco.length + '/' + lista.length + ' ativos');
        if (lista[0] && lista[0].buscadoEm) {
            const d = new Date(lista[0].buscadoEm);
            if (!Number.isNaN(d.getTime())) {
                parte.push('coletado ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }));
            }
        }
        pe.textContent = parte.join(' · ');
        return pe;
    }

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
            preco.textContent = formatarPreco(c.preco);

            const variacao = document.createElement('span');
            variacao.className = 'cotacao__var';
            variacao.textContent = c.variacao == null ? ''
                : (c.variacao > 0 ? '+' : '') + Number(c.variacao).toFixed(2).replace('.', ',') + '%';

            const hora = document.createElement('span');
            hora.className = 'cotacao__hora';
            hora.textContent = c.cotizadoEm || '';

            item.append(simbolo, preco, variacao, hora);
            alvo.appendChild(item);
        });

        alvo.appendChild(peCotacoes(lista));
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
            pintarCotacoes(valor ? [{ simbolo: 'GGPS3', preco: valor, variacao: null, atual: true }]
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
            if (chave in janelaPainel) pintarKpi(chave, KPIs[chave], janelaPainel[chave], janelaPainel);
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
