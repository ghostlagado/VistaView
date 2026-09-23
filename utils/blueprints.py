from routes import (
    acoes, general, 
    visitas, tarefas
)

bps = {
    general.general_bp: "/",
    acoes.actions_bp: "/actions",
    visitas.visitas_bp: "/visitas",
    tarefas.tarefas_bp: "/tarefas"
}