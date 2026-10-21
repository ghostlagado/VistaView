"""Regras e cálculos dos indicadores do GPS Vista, em ORM.

O módulo já foi o lugar onde as consultas moravam como texto T-SQL copiado das rotas.
Agora as consultas são construídas com o SQLAlchemy a partir dos modelos de `models/`, e
isso tem três consequências práticas:

1. **A mesma consulta roda em dois bancos.** `extract('month', ...)` vira `DATEPART` no
   SQL Server e `STRFTIME` no SQLite; `limit(1)` vira `TOP 1` ou `LIMIT 1`; os nomes de
   coluna saem do mapeamento. Nada aqui precisa saber em qual banco está.
2. **Não existe SQL montado por texto.** O recorte (`GER`/`GR`/`DIR`) era interpolado no
   `WHERE`; hoje `Cr.coluna_do_recorte` devolve a coluna mapeada, e um valor fora da
   whitelist não produz string nenhuma.
3. **As regras de negócio ficaram nomeadas.** `Expirada = 0`, `Status = 85` e os cinco
   checklists aparecem como `Tarefa.expirada == 0`, `STATUS_CONCLUIDA` e
   `Tarefa.checklist_id.in_(CHECKLISTS_VISITAS)` — a lista do que cada indicador conta
   está na docstring de cada método.

O hint `WITH(NOLOCK)` do warehouse original não desapareceu: ele é aplicado só no dialeto
`mssql` (ver `_com_hint`), porque no SQLite ele não existe e no SQL Server ele continua
significando "leitura que não espera lock".

A superfície pública não mudou: as mesmas 13 folhas, com as mesmas assinaturas e os
mesmos formatos de retorno, porque `routes/` e o tempo real as consomem por nome.
"""

from calendar import monthrange
from datetime import datetime as dt

from sqlalchemy import case, extract, func, select

from models import Cr, Estrutura, Recurso, Tarefa
from models.tarefa import STATUS_ABERTAS, STATUS_CONCLUIDA
from utils.config import CHECKLISTS_VISITAS, SETTINGS
from utils.db import db

#: As quatro tabelas que o SQL Server deve ler sem esperar lock, como na consulta original.
_ENTIDADES_COM_NOLOCK = (Tarefa, Estrutura, Cr, Recurso)


def _com_hint(consulta):
    """Aplica `WITH(NOLOCK)` apenas no dialeto SQL Server.

    No SQLite o hint seria sintaxe inválida, e é exatamente por isso que ele vive aqui em
    vez de dentro de cada consulta: uma decisão de dialeto, tomada uma vez.
    """
    for entidade in _ENTIDADES_COM_NOLOCK:
        consulta = consulta.with_hint(entidade, "WITH(NOLOCK)", "mssql")
    return consulta


def coluna_de_filtro(opt):
    """Whitelist do recorte, delegada ao modelo. `None` para um `opt` fora da lista."""
    return Cr.coluna_do_recorte(opt)


def _janela_mes_agora(agora=None):
    """Ano e mês em curso — a janela de quase todos os números do painel."""
    agora = agora or dt.now()
    return {"month": agora.month, "year": agora.year}


def _janela_mes_anterior(agora=None):
    """Mês anterior com a virada de ano: janeiro referencia dezembro do ano passado."""
    agora = agora or dt.now()
    mes = agora.month - 1
    ano = agora.year
    if mes == 0:
        mes, ano = 12, ano - 1
    return {"month": mes, "year": ano}


class IndicadoresWarehouse:
    """Serviço que lê o painel do warehouse (SQL Server) ou do SQLite local.

    Uma instância por aplicação, guardada em `app.config["VISTA_FONTE"]`. A sessão é
    procurada no momento da consulta — nunca guardada no construtor — porque o painel é
    recalculado dentro de um `app_context` aberto pelo ciclo de tempo real, e uma sessão
    presa a outro contexto quebraria o greenlet.
    """

    def __init__(self, sessao=None):
        #: `None` significa "usa a sessão do Flask-SQLAlchemy do app corrente".
        self._sessao = sessao

    #: A whitelist mora no modelo; a fonte só a expõe para que `montar_painel` e as rotas
    #: tratem warehouse e demonstração pelo mesmo contrato.
    coluna_de_filtro = staticmethod(coluna_de_filtro)

    @property
    def sessao(self):
        return self._sessao if self._sessao is not None else db.session

    # -- blocos reaproveitados por todas as consultas --------------------------
    def _de_tarefas(self):
        """`FROM Tarefa JOIN DM_ESTRUTURA JOIN DM_CR`, com o hint de leitura.

        O join é sempre por relação declarada (`Tarefa.estrutura`, `Estrutura.cr`), então
        a condição `ON` mora num lugar só: `models/`.
        """
        return _com_hint(
            select().select_from(Tarefa).join(Tarefa.estrutura).join(Estrutura.cr)
        )

    def _do_recorte(self, consulta, campo, gr):
        """Aplica o recorte e a regra que nunca falta: tarefa expirada não conta."""
        return consulta.where(campo == gr, Tarefa.expirada == 0)

    def _no_mes(self, consulta, janela):
        return consulta.where(
            extract("month", Tarefa.termino_real) == janela["month"],
            extract("year", Tarefa.termino_real) == janela["year"],
        )

    def _no_dia(self, consulta, agora):
        return consulta.where(extract("day", Tarefa.termino_real) == agora.day)

    def _de_visita(self, consulta):
        """Os cinco checklists que caracterizam uma visita — sempre por bind, nunca texto."""
        return consulta.where(Tarefa.checklist_id.in_(CHECKLISTS_VISITAS))

    def _concluida(self, consulta):
        return consulta.where(Tarefa.status == STATUS_CONCLUIDA)

    # ------------------------------------------------------------------ VISITAS
    def visitas_mes(self, campo, gr, agora=None):
        """Visitas concluídas do mês corrente.

        Filtra por recorte, checklist de visita, mês/ano, não expirada e concluída.
        """
        consulta = self._de_tarefas()
        consulta = self._do_recorte(consulta, campo, gr)
        consulta = self._no_mes(consulta, _janela_mes_agora(agora))
        consulta = self._de_visita(consulta)
        consulta = self._concluida(consulta)
        consulta = consulta.add_columns(func.count(Tarefa.nome).label("TOTAL"))
        return self.sessao.execute(consulta).scalar()

    def visitas_dia(self, campo, gr, agora=None):
        """Visitas concluídas de hoje. O `limit(1)` é o `TOP 1` da consulta original."""
        agora = agora or dt.now()
        consulta = self._de_tarefas()
        consulta = self._do_recorte(consulta, campo, gr)
        consulta = self._no_mes(consulta, _janela_mes_agora(agora))
        consulta = self._no_dia(consulta, agora)
        consulta = self._de_visita(consulta)
        consulta = self._concluida(consulta)
        consulta = consulta.add_columns(func.count(Tarefa.nome).label("TOTAL")).limit(1)
        return self.sessao.execute(consulta).scalar()

    # ------------------------------------------------------------------ TAREFAS
    def tarefas_total(self, campo, gr, agora=None):
        """Tarefas concluídas do mês — o número grande do painel."""
        consulta = self._de_tarefas()
        consulta = self._do_recorte(consulta, campo, gr)
        consulta = self._no_mes(consulta, _janela_mes_agora(agora))
        consulta = self._concluida(consulta)
        consulta = consulta.add_columns(func.count(Tarefa.nome).label("TOTAL"))
        return self.sessao.execute(consulta).scalar()

    def tarefas_mes_anterior(self, campo, gr, agora=None):
        """Base da meta: as concluídas do mês anterior."""
        consulta = self._de_tarefas()
        consulta = self._do_recorte(consulta, campo, gr)
        consulta = self._no_mes(consulta, _janela_mes_anterior(agora))
        consulta = self._concluida(consulta)
        consulta = consulta.add_columns(func.count(Tarefa.nome).label("TOTAL")).limit(1)
        return self.sessao.execute(consulta).scalar()

    def tarefas_dia(self, campo, gr, agora=None):
        """Concluídas de hoje, para o ritmo diário da meta."""
        agora = agora or dt.now()
        consulta = self._de_tarefas()
        consulta = self._do_recorte(consulta, campo, gr)
        consulta = self._no_mes(consulta, _janela_mes_agora(agora))
        consulta = self._no_dia(consulta, agora)
        consulta = self._concluida(consulta)
        consulta = consulta.add_columns(func.count(Tarefa.nome).label("TOTAL")).limit(1)
        return self.sessao.execute(consulta).scalar()

    def escalonadas(self, campo, gr):
        """Tarefas que subiram de nível e ainda estão abertas.

        Sem janela de data — é o estoque do momento, não o fluxo do mês. E o contador é
        `COUNT(cr.GERENTE)`, como na consulta original: conta linhas que têm gerente
        vinculado, o que não é o mesmo que contar tarefas.
        """
        consulta = self._do_recorte(self._de_tarefas(), campo, gr).where(
            Tarefa.escalonado > 0, Tarefa.status.in_(STATUS_ABERTAS)
        )
        return self.sessao.execute(
            consulta.add_columns(func.count(Cr.gerente).label("TOTAL"))
        ).scalar()

    def performance(self, campo, gr, agora=None):
        """Divide as tarefas do mês entre no prazo e fora do prazo.

        Não filtra por status: aqui entram todas as não expiradas do mês, concluídas ou
        não — é o que faz o par de barras fechar com o total do período. A rotulagem por
        `Escalonado` era um `CASE` no texto; vira `case()` do SQLAlchemy, que compila
        `CASE WHEN` nos dois bancos.
        """
        rotulo = case(
            (Tarefa.escalonado == 0, "NO PRAZO"),
            (Tarefa.escalonado > 0, "FORA DO PRAZO"),
        ).label("ST")
        consulta = self._no_mes(
            self._do_recorte(self._de_tarefas(), campo, gr), _janela_mes_agora(agora)
        )
        consulta = (
            consulta.add_columns(rotulo, func.count(Tarefa.id).label("TOTAL"))
            .group_by(Tarefa.escalonado)
            .order_by(Tarefa.escalonado)
        )
        linhas = self.sessao.execute(consulta).mappings().all()

        # A ordem e as duas chaves são as da rota original: o gráfico lê posição, não nome.
        st = {"FORA DO PRAZO": 0, "NO PRAZO": 0}
        for linha in linhas:
            if linha["ST"] in st:
                st[linha["ST"]] += int(linha["TOTAL"])

        return {"st": list(st.keys()), "total": list(st.values())}

    # ----------------------------------------------------------------- RANKINGS
    def top3_sups(self, campo, gr, agora=None):
        """Os três supervisores que mais fecharam visitas no mês."""
        # O join com o fechador entra por relação (`Tarefa.finalizador`), então o hint de
        # `RECURSO` já declarado em `_ENTIDADES_COM_NOLOCK` pega a tabela sem outro called.
        consulta = (
            self._de_visita(
                self._concluida(
                    self._no_mes(self._do_recorte(self._de_tarefas(), campo, gr),
                                 _janela_mes_agora(agora))
                )
            )
            .join(Tarefa.finalizador)
            .add_columns(Recurso.nome.label("Nome"), func.count(Recurso.nome).label("TOTAL"))
            .group_by(Recurso.nome)
            .order_by(func.count(Recurso.nome).desc())
            .limit(3)
        )
        linhas = self.sessao.execute(consulta).mappings().all()
        return {"sup": [l["Nome"] for l in linhas], "total": [l["TOTAL"] for l in linhas]}

    def _por_unidade(self, campo, gr, top, agora=None):
        """Tarefas concluídas por unidade; `top=True` é o ranking, `False` é a faixa."""
        consulta = self._concluida(
            self._no_mes(self._do_recorte(self._de_tarefas(), campo, gr), _janela_mes_agora(agora))
        )
        consulta = consulta.add_columns(
            Estrutura.nivel_03.label("UNIDADE"), func.count(Tarefa.id).label("TOTAL")
        ).group_by(Estrutura.nivel_03).order_by(func.count(Tarefa.id).desc())
        if top:
            consulta = consulta.limit(3)
        linhas = self.sessao.execute(consulta).mappings().all()
        return {"uni": [l["UNIDADE"] for l in linhas], "total": [l["TOTAL"] for l in linhas]}

    def top3_unidades(self, campo, gr, agora=None):
        return self._por_unidade(campo, gr, top=True, agora=agora)

    def unidades(self, campo, gr, agora=None):
        return self._por_unidade(campo, gr, top=False, agora=agora)

    def gerentes(self, campo, gr, agora=None):
        """Volume do mês por gerente da estrutura. Sem filtro de status, como na original."""
        consulta = self._no_mes(
            self._do_recorte(self._de_tarefas(), campo, gr), _janela_mes_agora(agora)
        )
        consulta = consulta.add_columns(
            Cr.gerente.label("GERENTE"), func.count(Tarefa.id).label("TOTAL")
        ).group_by(Cr.gerente).order_by(func.count(Tarefa.id).desc())
        linhas = self.sessao.execute(consulta).mappings().all()
        return {"grs": [l["GERENTE"] for l in linhas], "total": [l["TOTAL"] for l in linhas]}

    # -------------------------------------------------------------- SÉRIE DIÁRIA
    def _por_dia(self, campo, gr, janela, ate_dia=None):
        """Uma barra por dia do mês; `ate_dia` corta a série no dia correspondente."""
        consulta = self._no_mes(
            self._do_recorte(self._de_tarefas(), campo, gr), janela
        )
        if ate_dia is not None:
            consulta = consulta.where(extract("day", Tarefa.termino_real) <= ate_dia)
        dia = extract("day", Tarefa.termino_real).label("DIA")
        consulta = (
            consulta.add_columns(dia, func.count(Tarefa.id).label("TOTAL"))
            .group_by(dia)
            .order_by(dia)
        )
        linhas = self.sessao.execute(consulta).mappings().all()
        return {"dia": [l["DIA"] for l in linhas], "total": [l["TOTAL"] for l in linhas]}

    def graph_days(self, campo, gr, agora=None):
        return self._por_dia(campo, gr, _janela_mes_agora(agora))

    def graph_days_ant(self, campo, gr, agora=None):
        """Mês anterior cortado até o mesmo dia de hoje — comparação justa entre barras."""
        agora = agora or dt.now()
        return self._por_dia(campo, gr, _janela_mes_anterior(agora), ate_dia=agora.day)

    # ---------------------------------------------------------------- AGREGADO
    def painel(self, opt, gr, agora=None, meta_percentual=None):
        """Painel completo lido desta fonte."""
        return montar_painel(self, opt, gr, agora, meta_percentual)


def montar_painel(fonte, opt, gr, agora=None, meta_percentual=None):
    """Agrega as cifras do painel a partir de uma `fonte` de indicadores.

    A fonte é qualquer objeto com as mesmas folhas deste módulo — `IndicadoresWarehouse`
    ou a demonstração sintética. A regra de meta mora aqui, uma vez só, para que HTTP,
    Socket.IO e o modo demo cheguem no mesmo número.
    """
    campo = fonte.coluna_de_filtro(opt)
    if campo is None:
        raise ValueError(f"recorte inválido: {opt!r}")

    agora = agora or dt.now()
    if meta_percentual is None:
        meta_percentual = SETTINGS.meta_percentual

    def inteiro(valor):
        return int(valor or 0)

    total_mes = inteiro(fonte.tarefas_total(campo, gr, agora))
    total_dia = inteiro(fonte.tarefas_dia(campo, gr, agora))
    mes_anterior = inteiro(fonte.tarefas_mes_anterior(campo, gr, agora))

    meta_mes = round(mes_anterior * (1 + meta_percentual / 100))
    dias_no_mes = monthrange(agora.year, agora.month)[1]
    meta_dia = round(meta_mes / max(dias_no_mes - agora.day, 1))

    return {
        "atualizadoEm": agora.isoformat(timespec="seconds"),
        "recorte": {"opt": opt, "gr": gr},
        "totalMes": total_mes,
        "totalDia": total_dia,
        "visitasMes": inteiro(fonte.visitas_mes(campo, gr, agora)),
        "visitasDia": inteiro(fonte.visitas_dia(campo, gr, agora)),
        "escalonadas": inteiro(fonte.escalonadas(campo, gr)),
        "mesAnterior": mes_anterior,
        "metaMes": meta_mes,
        "metaDia": meta_dia,
        "gapMes": total_mes - meta_mes,
        "gapDia": total_dia - meta_dia,
        "performance": fonte.performance(campo, gr, agora),
        "top3Uni": fonte.top3_unidades(campo, gr, agora),
        "top3Sup": fonte.top3_sups(campo, gr, agora),
        "gerentes": fonte.gerentes(campo, gr, agora),
        "unidades": fonte.unidades(campo, gr, agora),
        "dias": fonte.graph_days(campo, gr, agora),
        "diasAnt": fonte.graph_days_ant(campo, gr, agora),
    }


#: Fonte real única do app: a mesma instância que `create_app` guarda em
#: `app.config["VISTA_FONTE"]` quando ninguém pediu demonstração. Não existe atalho de
#: módulo para `painel` — quem consulta pega a fonte, e é ela que responde.
INDICADORES = IndicadoresWarehouse()
