"""Espelho de leitura do warehouse do GPS Vista.

Quatro entidades, nenhuma escrita:

- `Tarefa` — a linha que gera os números;
- `Recurso` — quem fechou a tarefa (ranking de supervisores);
- `Estrutura` — onde ela aconteceu (unidade e cadeia de comando);
- `Cr` — a cadeia de comando, de onde sai a coluna do recorte (`GER`/`GR`/`DIR`).

Importar este pacote registra as classes no `db.Model` do Flask-SQLAlchemy, então
`db.create_all()` encontra as tabelas sem nenhum registro manual — é o que permite criar
o SQLite local do zero. Em `app.py` o import acontece cedo por causa disso.

    from models import Tarefa, Cr, aplicar_esquema
"""

from models.base import ModeloBase, aplicar_esquema, resumo
from models.cr import Cr
from models.estrutura import Estrutura
from models.recurso import Recurso
from models.tarefa import STATUS_ABERTAS, STATUS_CONCLUIDA, Tarefa

#: Todas as entidades mapeadas, na ordem de dependência do `create_all`.
ENTIDADES: tuple[type, ...] = (Cr, Estrutura, Recurso, Tarefa)

__all__ = [
    "Cr",
    "ENTIDADES",
    "Estrutura",
    "ModeloBase",
    "Recurso",
    "STATUS_ABERTAS",
    "STATUS_CONCLUIDA",
    "Tarefa",
    "aplicar_esquema",
    "resumo",
]
