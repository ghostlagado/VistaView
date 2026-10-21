"""`RECURSO` — a pessoa que fechou a tarefa.

Só duas colunas interessam ao painel: o hash que amarra a tarefa a quem a terminou
(`CODIGOHASH`, vindo de `TAREFA.FINALIZADOPORHASH`) e o nome exibido no ranking de
top 3 supervisores. O vínculo é por hash, não por id numérico, então a chave primária
deste espelho é uma string — é assim no warehouse e é assim aqui.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import ModeloBase


class Recurso(ModeloBase):
    __tablename__ = "RECURSO"
    _forasteira = False  # fica no banco principal, junto com TAREFA

    codigo_hash: Mapped[str] = mapped_column("CODIGOHASH", String(64), primary_key=True)

    #: Nome impresso no cartão "Top 3 supervisores".
    nome: Mapped[str] = mapped_column("Nome", String(120))
