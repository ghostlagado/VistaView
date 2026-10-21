"""`TAREFA` — a linha que gera todos os números do painel.

Cada linha é uma tarefa escalonada para uma estrutura. O painel nunca mostra uma tarefa
singular: conta, agrupa por unidade/supervisor/gerente/dia e compara com o mês anterior.
As regras que decidem o que entra na conta moravam no `WHERE` das rotas; aqui elas viram
nomes, para que a regra fique uma vez só e seja legível:

- `Status = 85` é a única condição de "concluída" que conta em total, visita e ranking;
- `Status IN (25, 10, 70)` são os estados abertos que a rota de escalonadas consultava —
  os três códigos foram preservados da auditoria e nenhum deles ganhou nome inventado,
  porque o significado exato de cada um não está documentado na origem;
- `Expirada = 0` descarta tarefa vencida em qualquer conta;
- `Escalonado > 0` separa "fora do prazo" de "no prazo" no gráfico de performance;
- `ChecklistId` entre os cinco da whitelist é o que faz a tarefa contar como visita.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import ModeloBase
from utils.config import CHECKLISTS_VISITAS

#: Concluída: o único código de status que as rotas sempre contaram.
STATUS_CONCLUIDA = 85

#: Os códigos de status que a rota original tratava como "ainda aberta".
STATUS_ABERTAS: tuple[int, ...] = (25, 10, 70)


class Tarefa(ModeloBase):
    __tablename__ = "Tarefa"
    _forasteira = False

    id: Mapped[int] = mapped_column("ID", Integer, primary_key=True)

    #: Nome da tarefa — é `COUNT(T.NOME)` que as rotas sempre contaram.
    nome: Mapped[str] = mapped_column("NOME", String(200))

    #: Identificador do checklist executado; decide se a tarefa conta como visita.
    checklist_id: Mapped[str] = mapped_column("ChecklistId", String(36))

    #: Fim efetivo. Todas as janelas do painel (dia, mês, mês anterior) olham esta coluna.
    termino_real: Mapped[datetime] = mapped_column("TerminoReal", DateTime)

    #: `0` = não expirada. A regra de nunca contar expirada é a única que atravessa o
    #: painel inteiro, e aparece nas consultas como `Tarefa.expirada == 0`.
    expirada: Mapped[int] = mapped_column("Expirada", Integer, default=0)

    status: Mapped[int] = mapped_column("Status", Integer)

    #: Maior que zero quando a tarefa subiu de nível: "fora do prazo" no gráfico.
    escalonado: Mapped[int] = mapped_column("Escalonado", Integer, default=0)

    #: Ponte lógica para `DM_ESTRUTURA.Id_estrutura`.
    estrutura_id: Mapped[int] = mapped_column("EstruturaId", Integer)

    #: Ponte lógica para `RECURSO.CODIGOHASH` — quem fechou a tarefa.
    finalizado_por_hash: Mapped[str] = mapped_column("FinalizadoPorHash", String(64))

    estrutura: Mapped["Estrutura"] = relationship(  # noqa: F821
        "Estrutura",
        primaryjoin="Tarefa.estrutura_id == Estrutura.id_estrutura",
        foreign_keys="Tarefa.estrutura_id",
        viewonly=True,
    )

    finalizador: Mapped["Recurso"] = relationship(  # noqa: F821
        "Recurso",
        primaryjoin="Tarefa.finalizado_por_hash == Recurso.codigo_hash",
        foreign_keys="Tarefa.finalizado_por_hash",
        viewonly=True,
    )

    # -- regras de negócio, uma vez só -----------------------------------------
    @property
    def concluida(self) -> bool:
        return self.status == STATUS_CONCLUIDA

    @property
    def aberta(self) -> bool:
        return self.status in STATUS_ABERTAS

    @property
    def em_dia(self) -> bool:
        return self.escalonado == 0

    @property
    def eh_visita(self) -> bool:
        return self.checklist_id in CHECKLISTS_VISITAS
