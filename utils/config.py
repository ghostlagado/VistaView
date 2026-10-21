"""Configuração central da aplicação.

Único ponto do projeto que lê variáveis de ambiente. `opts` e `CHECKLISTS_VISITAS`
são regras de negócio (whitelist de recorte e os checklists que contam como visita)
e continuam sendo constantes, não configuração de execução.
"""

from dataclasses import dataclass
from os import getenv, path
from secrets import token_hex

# Banco local do painel. Fica em `instance/`, diretório que o Flask já reserva para dados
# de máquina e que o .gitignore cobre: o espelho do warehouse é arquivo seu, nunca do
# repositório. É arquivo, não memória, porque o mesmo `python app.py` que abre a TV precisa
# achar as mesmas linhas na próxima vez — e um arquivo não exige servidor de banco nenhum.
ARQUIVO_SQLITE = path.abspath(
    path.join(path.dirname(path.dirname(__file__)), "instance", "dw_vista_local.sqlite3")
)

opts = {
    # O recorte é a coluna da cadeia de comando que diz quem manda. Os valores eram
    # `cr.Gerente` quando o SQL era texto; no ORM viram o **nome do atributo mapeado** em
    # `models.Cr`, e a lista continua sendo a única origem de coluna aceita numa consulta.
    'GER': 'gerente',
    'GR': 'gerente_regional',
    'DIR': 'diretor_regional',
}

CHECKLISTS_VISITAS = (
    '7c7d1611-01f5-4f6a-9652-4e24bb1ce07a',
    '21368b38-a8f5-4793-8317-aca40a9489a5',
    '71bb4fa9-6f30-45df-9461-4b01534fbc12',
    'd44ee96b-262e-4d6e-b4a6-861cf0663c3e',
    '460e6d74-a6fe-4128-bc84-3d0455d30f45',
)

_VERDADEIROS = {"1", "true", "yes", "on"}


def _flag(nome: str, padrao: bool = False) -> bool:
    return getenv(nome, str(padrao)).strip().lower() in _VERDADEIROS


def _inteiro(nome: str, padrao: int) -> int:
    try:
        return int(getenv(nome, padrao))
    except (TypeError, ValueError):
        return padrao


def _flutuador(nome: str, padrao: float) -> float:
    try:
        return float(getenv(nome, padrao))
    except (TypeError, ValueError):
        return padrao


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    debug: bool
    secret: str
    db_uri: str
    default_opt: str
    default_gr: str
    meta_percentual: float = 15.0
    atualizacao_segundos: int = 60
    demo: bool = False
    esquema: str = ""
    action_api: str = ""
    cotacoes_simbolos: str = "GGPS3"
    cotacoes_segundos: int = 300
    cotacoes_velho_min: int = 15

    @classmethod
    def from_env(cls) -> "Settings":
        demo = _flag("MODO_DEMO")
        uri = getenv("DB_URI", "").strip()
        # Sem DB_URI o painel lê do SQLite local: o app cria o schema, e
        # `python -m services.semente` é quem popula. O SQL Server só entra em jogo quando
        # alguém aponta a URI no ambiente — é assim que a mesma base de modelos serve o
        # desenvolvimento offline e o warehouse de origem.
        if not uri and not demo:
            uri = f"sqlite:///{ARQUIVO_SQLITE}"
        # `dw_vista.dbo` é o schema onde o warehouse real mantém as tabelas de estrutura.
        # No SQLite não existe schema cruzado, então ali o prefixo é ignorado de propósito.
        esquema = getenv("VISTA_ESQUEMA", "").strip() or (
            "dw_vista.dbo" if uri.startswith("mssql") else ""
        )
        return cls(
            host=getenv("HOST", "0.0.0.0"),
            port=_inteiro("PORT", 8092),
            debug=_flag("DEBUG"),
            # Demonstração não tem login nem dado sensível, então uma chave descartável
            # por processo basta — e evita a tentação de commitar uma SECRET de exemplo.
            # No modo real a chave explícita continua obrigatória: sem ela as sessões
            # mudam a cada restart e qualquer valor padrão no código seria segredo público.
            secret=getenv("SECRET", "") or (token_hex(32) if demo else ""),
            db_uri=uri,
            esquema=esquema,
            default_opt=getenv("DEFAULT_OPT", "GR"),
            default_gr=getenv("DEFAULT_GR", "Parana Interior"),
            meta_percentual=_flutuador("META_PERCENTUAL", 15.0),
            atualizacao_segundos=_inteiro("ATUALIZACAO_SEGUNDOS", 60),
            demo=demo,
            action_api=getenv("ACTION_API", "").strip(),
            cotacoes_simbolos=getenv("COTACOES_SIMBOLOS", "GGPS3"),
            cotacoes_segundos=_inteiro("COTACOES_SEGUNDOS", 300),
            cotacoes_velho_min=_inteiro("COTACOES_VELHO_MIN", 15),
        )

    def validar(self) -> None:
        """Falha rápido e com mensagem acionável em vez de um RuntimeError de framework."""
        problemas = []
        # `from_env` nunca devolve URI vazia fora da demonstração (o SQLite local é o
        # padrão), então esta regra pega o caminho programático: um Settings montado à mão
        # sem URI apontaria para lugar nenhum e o painel mostraria zeros calados.
        if not self.db_uri and not self.demo:
            problemas.append("DB_URI ausente: configure a URI SQLAlchemy do banco no .env.")
        # O que ainda vale conferir aqui é o driver. As duas fontes validadas são SQLite e
        # SQL Server: um nome diferente daria erro obscuro só na primeira consulta do
        # painel, e prometer suporte a um banco que ninguém compilou nos modelos seria pior.
        if self.db_uri and not self.db_uri.startswith(("sqlite", "mssql")):
            problemas.append(
                f"DB_URI usa o driver {self.db_uri.split('://', 1)[0]!r}, que o painel não "
                "conhece. As duas fontes suportadas são sqlite e mssql+pyodbc."
            )
        # O schema é um atributo do mapeamento, não do dialeto: com prefixo, o SQLite
        # também o imprimiria no SQL — e lá não existe schema cruzado, então cada
        # consulta quebraria. `from_env` nunca chega aqui com essa combinação.
        if self.esquema and self.db_uri.startswith("sqlite"):
            problemas.append(
                "VISTA_ESQUEMA exige um DB_URI de SQL Server: no SQLite o prefixo "
                "quebraria todas as consultas. Deixe VISTA_ESQUEMA em branco."
            )
        if not self.secret:
            problemas.append("SECRET ausente: defina a chave de sessão do Flask no .env.")
        if self.default_opt not in opts:
            problemas.append(
                f"DEFAULT_OPT={self.default_opt!r} inválida; use uma de {sorted(opts)}."
            )
        if self.meta_percentual < 0:
            problemas.append("META_PERCENTUAL precisa ser um percentual maior ou igual a zero.")
        if self.atualizacao_segundos < 15:
            problemas.append("ATUALIZACAO_SEGUNDOS precisa ser de pelo menos 15 segundos.")
        if len([s for s in self.cotacoes_simbolos.split(",") if s.strip()]) > 5:
            problemas.append(
                "COTACOES_SIMBOLOS aceita no máximo 5 ativos; o provedor cobra por requisição "
                "e um a mais estoura o limite."
            )
        if self.cotacoes_segundos < 60:
            problemas.append("COTACOES_SEGUNDOS precisa ser de pelo menos 60 segundos.")
        if self.cotacoes_velho_min < 1:
            problemas.append("COTACOES_VELHO_MIN precisa ser de pelo menos 1 minuto.")
        if problemas:
            raise RuntimeError("Configuração inválida:\n- " + "\n- ".join(problemas))


SETTINGS = Settings.from_env()

# Compatível com os imports existentes.
DEFAULT_GR = SETTINGS.default_gr
DEFAULT_OPT = SETTINGS.default_opt
