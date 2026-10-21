"""Base comum dos modelos do painel.

Estas classes não descrevem um banco que possuímos: são um **espelho de leitura** do
warehouse do GPS Vista (`TAREFA`, `RECURSO`, `dw_vista.dbo.DM_ESTRUTURA`,
`dw_vista.dbo.DM_CR`). Por isso:

- o nome real da coluna vai no primeiro argumento de `mapped_column`, e o nome Python é
  snake_case — o SQL gerado continua batendo com o do warehouse;
- nenhum `ForeignKey` físico é declarado. O `relationship` usa `primaryjoin` explícito e
  `viewonly=True`, porque o vínculo é lógico no banco de origem e o painel não escreve
  nada nele;
- as chaves primárias existem só para o mapeamento identificador do SQLAlchemy funcionar;
  nenhuma consulta do painel depende delas.

`db.Model` (Flask-SQLAlchemy) é o pai real: é assim que `db.session` enxerga as classes e
que `db.create_all()` cria o schema local do SQLite sem nenhum registro manual.

O prefixo `dw_vista.dbo` é aplicado em execução por `aplicar_esquema`. No SQL Server ele é
obrigatório (as tabelas de estrutura vivem em outro banco da mesma instância); no SQLite
ele é removido, porque lá não existe schema cruzado.
"""

from utils.db import db


class ModeloBase(db.Model):
    """Pai de toda entidade espelho. Abstrata: não gera tabela."""

    __abstract__ = True

    #: Verdadeiro para as tabelas que o warehouse mantém dentro de `dw_vista.dbo`.
    _forasteira = False


def resumo(entidade) -> str:
    """`Tarefa(ID=12)` — repr de depuração sem acionar carregamento extra."""
    chave = next(iter(entidade.__table__.primary_key.columns), None)
    valor = getattr(entidade, chave.key, None) if chave else None
    return f"{type(entidade).__name__}({chave.name}={valor!r})" if chave else type(entidade).__name__


def aplicar_esquema(esquema: str | None) -> None:
    """Põe (ou tira) o schema `dw_vista.dbo` nas tabelas de estrutura.

    Mexer no mapeamento depois da classe criada é seguro: o SQLAlchemy guarda o schema no
    objeto `Table` e compila o prefixo que estiver valendo naquele momento. É assim que o
    mesmo código roda nos dois bancos sem precisar de duas famílias de classes.
    """
    from models import ENTIDADES

    valor = esquema or None
    for entidade in ENTIDADES:
        if entidade._forasteira:
            entidade.__table__.schema = valor
