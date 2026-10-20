"""Configuração central da aplicação.

Único ponto do projeto que lê variáveis de ambiente. `opts` e `CHECKLISTS_VISITAS`
são regras de negócio (whitelist de recorte e os checklists que contam como visita)
e continuam sendo constantes, não configuração de execução.
"""

from dataclasses import dataclass
from os import getenv

opts = {
    'GER': 'cr.Gerente',
    'GR': 'cr.GerenteRegional',
    'DIR': 'cr.DiretorRegional'
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
    action_api: str = ""
    cotacoes_simbolos: str = "GGPS3"
    cotacoes_segundos: int = 300
    cotacoes_velho_min: int = 15

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            host=getenv("HOST", "0.0.0.0"),
            port=_inteiro("PORT", 8092),
            debug=_flag("DEBUG"),
            secret=getenv("SECRET", ""),
            db_uri=getenv("DB_URI", ""),
            default_opt=getenv("DEFAULT_OPT", "GR"),
            default_gr=getenv("DEFAULT_GR", "Parana Interior"),
            meta_percentual=_flutuador("META_PERCENTUAL", 15.0),
            atualizacao_segundos=_inteiro("ATUALIZACAO_SEGUNDOS", 60),
            demo=_flag("MODO_DEMO"),
            action_api=getenv("ACTION_API", "").strip(),
            cotacoes_simbolos=getenv("COTACOES_SIMBOLOS", "GGPS3"),
            cotacoes_segundos=_inteiro("COTACOES_SEGUNDOS", 300),
            cotacoes_velho_min=_inteiro("COTACOES_VELHO_MIN", 15),
        )

    def validar(self) -> None:
        """Falha rápido e com mensagem acionável em vez de um RuntimeError de framework."""
        problemas = []
        if not self.db_uri and not self.demo:
            # Em demonstração nenhuma consulta chega ao banco, então a URI não é exigida.
            problemas.append("DB_URI ausente: configure a URI SQLAlchemy do dw_vista no .env.")
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
