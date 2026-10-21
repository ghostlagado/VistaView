"""`dw_vista.dbo.DM_CR` — a cadeia de comando de uma estrutura.

Uma linha desta tabela diz quem é o gerente, o gerente regional e o diretor regional
responsáveis por uma estrutura. É daqui que sai o **recorte** do painel (`GER`, `GR`,
`DIR`): a coluna escolhida é comparada ao nome da regional que a TV está mostrando.

Essa escolha de coluna é a única parte do SQL antigo que era interpolada como texto, e
por isso ela é o ponto sensível do sistema. No ORM ela deixa de ser texto: `opts` só
devolve um nome de atributo, e `coluna_do_recorte` confirma que aquele nome existe no
mapeamento antes de devolver a coluna. Um recorte fora da lista devolve `None` — e os
chamadores tratam `None` como "recorte inválido" (HTTP 400) — então já não existe caminho
por onde uma entrada do URL chegue ao SQL.
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import ModeloBase
from utils.config import opts


class Cr(ModeloBase):
    __tablename__ = "DM_CR"
    _forasteira = True  # vive em `dw_vista.dbo` no SQL Server

    id_cr: Mapped[int] = mapped_column("Id_cr", Integer, primary_key=True)

    #: Nome de quem responde pela estrutura na visão de gerente (recorte `GER`).
    gerente: Mapped[str] = mapped_column("Gerente", String(120))

    #: Nome de quem responde pela regional (recorte `GR`) — o recorte padrão do painel.
    gerente_regional: Mapped[str] = mapped_column("GerenteRegional", String(120))

    #: Nome de quem responde pela diretoria regional (recorte `DIR`).
    diretor_regional: Mapped[str] = mapped_column("DiretorRegional", String(120))

    estruturas: Mapped[list["Estrutura"]] = relationship(  # noqa: F821
        "Estrutura",
        primaryjoin="Cr.id_cr == Estrutura.id_cr",
        foreign_keys="Estrutura.id_cr",
        viewonly=True,
    )

    @classmethod
    def coluna_do_recorte(cls, opt: str):
        """Coluna mapeada do recorte, ou `None` se `opt` não estiver na whitelist.

        A lista de recortes possíveis é `utils.config.opts` — regra de negócio que a
        auditoria congelou. Retornar o objeto-coluna em vez do nome preserva o vínculo:
        quem consulta nunca precisa montar SQL a partir de texto do usuário.

        Um recorte válido cuja coluna não existe no mapeamento é erro de programação, não
        entrada ruim: ele viraria `WHERE 0 = 1` e o painel mostraria zeros numa TV, onde
        ninguém percebe. Por isso levanta `LookupError` em vez de devolver `None`.
        """
        atributo = opts.get(opt)
        if atributo is None:
            return None
        coluna = getattr(cls, atributo, None)
        if coluna is None:
            raise LookupError(
                f"`opts[{opt!r}]` aponta para {atributo!r}, que não é coluna de {cls.__name__}."
            )
        return coluna
