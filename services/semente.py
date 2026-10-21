"""Semente do espelho SQLite local (`instance/dw_vista_local.sqlite3`).

O painel em modo real (`MODO_DEMO=false`) faz consultas ORM de verdade. Sem `DB_URI` ele
lê do SQLite local, e um SQLite vazio mostraria zeros na TV — impossível de distinguir de
um recorte errado. Este módulo cria o schema e insere um conjunto pequeno, determinístico
e coerente de linhas nas quatro tabelas espelho, para que o caminho real possa ser visto e
testado sem nenhuma dependência de rede ou de SQL Server.

Três decisões deliberate:

1. **Só escreve em SQLite.** `semear()` recusa qualquer outra URI. O espelho é um banco
   de leitura: gravar nele — e sobretudo no warehouse real — nunca é efeito colateral
   aceitável de um comando de desenvolvimento.
2. **Nada chama isto no boot.** O `create_app` abre conexão e cria tabelas se preciso;
   popular é decisão explícita de quem roda `python -m services.semente`. Um painel que
   se auto-semeia esconderia que está mostrando dados inventados.
3. **Determinística.** A semente fixa do `random.Random` faz o mesmo comando produzir as
   mesmas cifras, o que deixa o SQLite local comparável entre máquinas e testável.

As datas são ancoradas no dia em que o comando roda, porque as janelas do painel são
"mês corrente", "mês anterior" e "hoje": uma semente congelada no tempo mostraria um mês
vazio para sempre.

    python -m services.semente            # cria o schema e popula
    python -m services.semente --limpar   # apaga as linhas e popula de novo
"""

import random
from calendar import monthrange
from datetime import date, datetime

from flask import Flask

from models import ENTIDADES, Cr, Estrutura, Recurso, Tarefa, aplicar_esquema
from models.tarefa import STATUS_ABERTAS, STATUS_CONCLUIDA
from utils.config import ARQUIVO_SQLITE, CHECKLISTS_VISITAS, SETTINGS
from utils.db import db

#: Fixa de propósito: trocar este número muda todas as cifras do painel local.
SEMENTE = 20261021

URI_LOCAL = f"sqlite:///{ARQUIVO_SQLITE}"

# Dois recortes regionais, para que o filtro de `GR` tenha o que excluir.
REGIONAIS = ("Parana Interior", "Sao Paulo Capital")
DIRETORES = {"Parana Interior": "Otavio Meneghetti", "Sao Paulo Capital": "Paulo Duarte"}

UNIDADES = (
    "Londrina", "Maringá", "Curitiba", "Cascavel", "Ponta Pora", "Campo Mourao",
    "Apucarana", "Cornelio Procópio", "Umuarama", "Foz do Iguacu", "Guarapuava",
    "Toledo",
)
GERENTES = (
    "Ana Paula Souza", "Carlos Eduardo Lima", "Marcos Vinicius Rocha",
    "Juliana Ferreira", "Rafael Antonio Nunes", "Beatriz Camargo",
    "Fernanda Prado", "Otavio Meneghetti", "Paulo Sergio Duarte",
)
SUPERVISORES = (
    "Tiago Moreira", "Aline Bassani", "Gustavo Ribeiro", "Denise Okada",
    "Anderson Prado", "Carla Meneghetti", "Rodrigo Alencar", "Juliana Ferraz",
)

NOMES_TAREFA = ("Revisao de rotina", "Auditoria de seguranca", "Checklist operacional",
                "Vistoria de campo", "Manutencao preventiva")

#: Checklists fora da whitelist: tarefa comum, não visita.
CHECKLISTS_OUTROS = (
    "b1d5f2a4-3c76-4e18-9a02-58f6c1d4e7b9",
    "e94a7c31-8d25-4b60-a3f1-72c05b9e6d18",
)


def _mes_anterior(hoje: date) -> tuple[int, int]:
    mes, ano = hoje.month - 1, hoje.year
    if mes == 0:
        mes, ano = 12, ano - 1
    return mes, ano


class SementeLocal:
    """Monta e grava o conteúdo do espelho SQLite.

    Instancia-se com uma sessão já aberta; o objeto só conhece as classes de `models/`,
    então o mesmo código funciona com qualquer banco que o SQLAlchemy aceite — é o
    `semear()` quem garante que só um SQLite entra nessa rota.
    """

    def __init__(self, sessao, hoje: date | None = None):
        self.sessao = sessao
        self.hoje = hoje or date.today()
        self.rnd = random.Random(SEMENTE)
        #: `ID` é sequencial porque o espelho não tem `AUTOINCREMENT` — é coluna do
        #: warehouse, não chave gerada por este banco.
        self.proximo_id = 1

    # ---------------------------------------------------------------- estrutura
    def _cadeias(self):
        """`DM_CR` + `DM_ESTRUTURA`: cada unidade tem uma linha de cada, por regional.

        Um id sequencial faz as pontes lógicas (`EstruturaId`, `Id_cr`) baterem sem
        depender de `ForeignKey` físico, exatamente como no warehouse de origem.
        """
        estruturas = []
        id_cr = id_est = 0
        for regional in REGIONAIS:
            for indice, unidade in enumerate(UNIDADES):
                id_cr += 1
                self.sessao.add(Cr(
                    id_cr=id_cr,
                    gerente=GERENTES[indice % len(GERENTES)],
                    gerente_regional=regional,
                    diretor_regional=DIRETORES[regional],
                ))
                id_est += 1
                estrutura = Estrutura(
                    id_estrutura=id_est, id_cr=id_cr, nivel_03=unidade)
                self.sessao.add(estrutura)
                estruturas.append(estrutura)
        return estruturas

    # ------------------------------------------------------------------ pessoas
    def _recursos(self):
        """`RECURSO`: um hash por supervisor, do formato usado pelo warehouse."""
        recursos = []
        for indice, nome in enumerate(SUPERVISORES, start=1):
            recurso = Recurso(codigo_hash=f"hash{indice:012d}", nome=nome)
            self.sessao.add(recurso)
            recursos.append(recurso)
        return recursos

    # ------------------------------------------------------------------ tarefas
    def _dias(self, ano: int, mes: int, ate: int):
        return [date(ano, mes, dia) for dia in range(1, ate + 1)]

    def _dia_a_dia(self, estruturas, recursos, ano, mes, ate_dia, por_dia):
        """Insere um dia de tarefas: hora dentro da jornada, status e visita sortidos."""
        for dia in self._dias(ano, mes, ate_dia):
            for _ in range(self.rnd.randint(*por_dia)):
                hora = self.rnd.randint(7, 19)
                minuto = self.rnd.randint(0, 59)
                # ~2/3 concluídas: o restante fica nos status abertos para alimentar as
                # escalonadas e o "fora do prazo" do gráfico de performance.
                concluida = self.rnd.random() < 0.68
                visita = self.rnd.random() < 0.2
                # `Escalonado > 0` tem de aparecer nos dois lados da conta: concluída e
                # escalonada é a barra "fora do prazo" do gráfico; aberta e escalonada é o
                # cartão de escalonadas. Com uma única probabilidade para as duas, o
                # segundo caso quase nunca acontecia e o painel ficaria com um zero mudo.
                escalonada = self.rnd.random() < (0.2 if concluida else 0.12)
                recurso = self.rnd.choice(recursos)
                self.sessao.add(Tarefa(
                    id=self.proximo_id,
                    nome=self.rnd.choice(NOMES_TAREFA),
                    checklist_id=(self.rnd.choice(CHECKLISTS_VISITAS) if visita
                                  else self.rnd.choice(CHECKLISTS_OUTROS)),
                    termino_real=datetime(dia.year, dia.month, dia.day, hora, minuto),
                    expirada=1 if self.rnd.random() < 0.04 else 0,
                    status=STATUS_CONCLUIDA if concluida
                    else self.rnd.choice(STATUS_ABERTAS),
                    escalonado=self.rnd.randint(1, 3) if escalonada else 0,
                    estrutura_id=self.rnd.choice(estruturas).id_estrutura,
                    finalizado_por_hash=recurso.codigo_hash,
                ))
                self.proximo_id += 1

    def executar(self):
        """Grava cadeias, recursos e os dois meses de tarefas que o painel compara."""
        estruturas = self._cadeias()
        recursos = self._recursos()

        mes_ant, ano_ant = _mes_anterior(self.hoje)
        # Mês anterior completo, e o corrente só até hoje — série alguma mostra o futuro.
        self._dia_a_dia(estruturas, recursos, ano_ant, mes_ant,
                        monthrange(ano_ant, mes_ant)[1], (14, 26))
        self._dia_a_dia(estruturas, recursos, self.hoje.year, self.hoje.month,
                        self.hoje.day, (14, 26))
        self.sessao.commit()

    def limpar(self):
        """Zera as quatro tabelas na ordem inversa da dependência lógica."""
        for entidade in reversed(ENTIDADES):
            self.sessao.query(entidade).delete()
        self.sessao.commit()


def abrir_sessao(uri: str):
    """App mínimo com `db` apontando para `uri`.

    Não usa `create_app`: popular o espelho não precisa de Socket.IO, cotações nem ciclo
    de atualização, e importar o app do painel criaria um greenlet por nada.
    """
    aplicacao = Flask(__name__)
    aplicacao.config["SQLALCHEMY_DATABASE_URI"] = uri
    db.init_app(aplicacao)
    return aplicacao


def semear(uri: str | None = None, limpar: bool = False, hoje: date | None = None) -> str:
    """Cria o schema (se faltar) e popula o espelho; devolve a URI usada."""
    uri = uri or SETTINGS.db_uri or URI_LOCAL
    if not uri.startswith("sqlite"):
        raise RuntimeError(
            f"A semente só escreve em SQLite; DB_URI={uri!r} aponta para outro banco. "
            "O warehouse real é leitura deste painel, nunca destino de INSERT."
        )
    # Sem prefixo de schema: é SQLite, e `dw_vista.dbo` não existe nesse banco.
    aplicar_esquema("")

    aplicacao = abrir_sessao(uri)
    with aplicacao.app_context():
        db.create_all()
        semente = SementeLocal(db.session, hoje)
        if limpar:
            semente.limpar()
        if semente.sessao.query(Tarefa).count() == 0:
            semente.executar()
            return f"{uri}: schema criado e populado."
        return f"{uri}: já tinha dados ({semente.sessao.query(Tarefa).count()} tarefas); nada inserido. Use --limpar."


if __name__ == "__main__":
    from sys import argv

    print(semear(limpar="--limpar" in argv))
