"""`dw_vista.dbo.DM_ESTRUTURA` — o onde da tarefa.

É a tabela que liga uma tarefa à cadeia de comando (via `Id_cr`) e ao nome da unidade
que aparece nos rankings do painel (`Nivel_03`). O painel usa exatamente três colunas
delas: a chave, a ponte para `DM_CR` e o nível organizacional exibido.

`Nivel_01`…`Nivel_05` existem no warehouse, mas não são mapeadas: copiar coluna que
nenhuma consulta lê só aumenta a superfície de mudança quando o DBA alterar a origem.
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import ModeloBase


class Estrutura(ModeloBase):
    __tablename__ = "DM_ESTRUTURA"
    _forasteira = True  # vive em `dw_vista.dbo` no SQL Server

    id_estrutura: Mapped[int] = mapped_column("Id_estrutura", Integer, primary_key=True)

    #: Ponte lógica para `DM_CR`. Sem `ForeignKey` físico: é leitura do warehouse alheio.
    id_cr: Mapped[int] = mapped_column("Id_cr", Integer)

    #: Nome da unidade (Londrina, Maringá, ...) — o rótulo dos rankings por unidade.
    nivel_03: Mapped[str] = mapped_column("Nivel_03", String(120))

    #: Um passo da jornada `Tarefa → Estrutura → Cr`; `viewonly` porque nada aqui escreve.
    cr: Mapped["Cr"] = relationship(  # noqa: F821
        "Cr",
        primaryjoin="Estrutura.id_cr == Cr.id_cr",
        foreign_keys="Estrutura.id_cr",
        viewonly=True,
    )
