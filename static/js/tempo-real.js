/*
 * Camada de tempo real do painel.
 *
 * Um único socket por página, um único conjunto de listeners, e um objeto global
 * `VistaTempoReal` para o restante do front-end assinar. O módulo não toca no DOM:
 * quem desenha a tela é `painel.js`.
 */
(function () {
    const EVENTOS = {
        snapshot: 'dashboard:snapshot',
        atualizacao: 'dashboard:update',
        status: 'dashboard:status',
        solicitar: 'dashboard:solicitar',
    };

    const ouvintes = new Map();
    let socket = null;
    let estado = 'iniciando';
    let painel = {};
    let status = null;

    function notificar(evento, dados) {
        const lista = ouvintes.get(evento);
        if (!lista) return;
        lista.forEach(function (fn) {
            try { fn(dados); }
            catch (e) { console.error('[tempo-real] ouvinte de "' + evento + '" falhou:', e); }
        });
    }

    function on(evento, fn) {
        if (!ouvintes.has(evento)) ouvintes.set(evento, new Set());
        const conjunto = ouvintes.get(evento);
        conjunto.add(fn);
        return function () { conjunto.delete(fn); };
    }

    function mudarEstado(novo) {
        if (estado === novo) return;
        estado = novo;
        notificar('estado', novo);
    }

    // A TV fica sem operador: se o Socket.IO desistir de reconectar, recarrega a página
    // para voltar ao caminho HTTP em vez de congelar com números antigos na tela.
    const RECARGA_DEPOIS_DE_MS = 5 * 60 * 1000;
    let recarga = null;

    function aoPerderConexao() {
        if (recarga) return;
        recarga = setTimeout(function () {
            recarga = null;
            window.location.reload();
        }, RECARGA_DEPOIS_DE_MS);
    }

    function aoReconectar() {
        if (!recarga) return;
        clearTimeout(recarga);
        recarga = null;
    }

    function conectar() {
        if (socket) return socket;
        if (typeof io === 'undefined') {
            mudarEstado('indisponivel');
            return null;
        }

        socket = io({ transports: ['websocket', 'polling'] });

        socket.on('connect', function () {
            aoReconectar();
            mudarEstado('conectado');
        });
        socket.on('disconnect', function () {
            mudarEstado('desconectado');
            aoPerderConexao();
        });
        socket.on('reconnect', function () { aoReconectar(); });
        socket.on('reconnect_attempt', function () { mudarEstado('reconectando'); });
        socket.on('connect_error', function () {
            mudarEstado('desconectado');
            aoPerderConexao();
        });

        socket.on(EVENTOS.snapshot, function (dados) {
            painel = Object.assign({}, dados);
            notificar('snapshot', painel);
        });
        socket.on(EVENTOS.atualizacao, function (dados) {
            painel = Object.assign(painel, dados);
            notificar('atualizacao', dados);
        });
        socket.on(EVENTOS.status, function (dados) {
            status = dados;
            notificar('status', dados);
        });

        return socket;
    }

    window.VistaTempoReal = {
        EVENTOS: EVENTOS,
        on: on,
        conectar: conectar,
        solicitar: function () {
            if (socket) socket.emit(EVENTOS.solicitar);
        },
        estado: function () { return estado; },
        painel: function () { return painel; },
        status: function () { return status; },
    };
})();
