var PORCENTAGEM_META = 15
var meta = PORCENTAGEM_META/100
var date = new Date()
var strDate = `${date.toLocaleDateString('pt-BR')} - ${date.getHours()}:${date.getMinutes()}`
var dia = null
var metaDiaria = null
var metaAtual = null
var totalMes = null
document.getElementById('date').textContent = strDate

const gr = sessionStorage.getItem('GR')
const opt = sessionStorage.getItem('OPT')

function nomeMin(str) {
    var nomeCompleto = str;
    var nome = nomeCompleto.split(" ")[0];
    var qtdnome = nomeCompleto.split(" ").length;
    var sobrenome = nomeCompleto.split(" ")[qtdnome-1]; 
    return `${nome} ${sobrenome}`
}

async function totalTarefas() {
    const res = await fetch(`/tarefas/total/${opt}/${gr}`,{method:'get'})
    const js = await res.json()
    totalMes = js
    document.getElementById('tm').textContent = js.toLocaleString('pt-BR')
    if(parseInt(js) >= parseInt(metaAtual)){
        document.getElementById('ttm').classList.add('bd-green')
    }else{
        document.getElementById('ttm').classList.add('bd-red')
    }
    var faltaMes = parseInt(js) - parseInt(metaAtual)
    document.getElementById('gpm').textContent = faltaMes.toLocaleString('pt-BR')
    if(faltaMes >= 0){document.getElementById('gm').classList.add('bd-green')}
    else{document.getElementById('gm').classList.add('bd-red')}    
}

async function top3Unidades() {
    const res = await fetch(`/top3_uni/${opt}/${gr}`)
    const js = await res.json()
    for(item in js['uni']){
        var nome = js['uni'][item] 
        var tt = js['total'][item]
        var perc = ((parseInt(tt)*100)/totalMes).toFixed(1)
        var color = 'success'
        if(perc <= 5){color = 'danger'}

        var li = document.createElement('li','list-group-item')
        li.style.fontSize = '16px'
        li.classList.add('list-group-item')
        li.classList.add('d-flex')
        li.classList.add('flex-column')
        li.classList.add('justify-contente-between')
        li.style.lineHeight = .8

        li.innerHTML = `
        <p class="fw-bold text-truncate">${nome}</p>
        <div class="d-flex justify-content-between align-items-start">
            <p class="">Total: ${tt.toLocaleString('pt-BR')}</p>
            <span class="badge rounded-pill fw-bold text-bg-${color}">${perc} %</span>
        <div> 
        `
        document.getElementById('listUni').appendChild(li)
    }
}

async function getUnidades() {
    const res = await fetch(`/get_unidades/${opt}/${gr}`)
    const js = await res.json()
    for(item in js['uni']){
        var nome = js['uni'][item] 
        var tt = js['total'][item]
        var perc = ((parseInt(tt)*100)/totalMes).toFixed(2)
        var color = '#a7c957'
        var icon = '<i class="bi bi-caret-up-fill"></i>'
        if(perc <= 5){
            color = '#e63946'
            icon =  '<i class="bi bi-caret-down-fill"></i>'
        }

        var sp = document.createElement('span')
        sp.classList.add('badge')
        sp.classList.add('rounded-pill')
        sp.style.background = '#333'
        sp.style.fontSize = '14px'
        sp.innerHTML = `<span>${nome} <span class="fw-bold" style="color: ${color};">${icon} ${perc}%</span></span>`

        var sp2 = document.createElement('span')
        sp2.classList.add('badge')
        sp2.classList.add('rounded-pill')
        sp2.classList.add('text-bg-success')
        sp2.style.fontSize = '14px'
        sp2.textContent = 'Boas Festas 🍒🎅🏻'

        document.getElementById('mq').appendChild(sp)
        document.getElementById('mq').appendChild(sp2)
    }
}

async function getEscalonadas(){
    const res = await fetch(`/tarefas/escalonadas/${opt}/${gr}`,{method:'get'})
    const js = await res.json()
    const total = js['total']
    document.getElementById('escalonadas').textContent = total
    if(parseInt(total) === 0){
        document.getElementById('esc').classList.add('bd-green')
    }
    else if(parseInt(total) > 0){
        document.getElementById('esc').classList.add('bd-red')
    }
}

async function visitasMes(){
    const res = await fetch(`/visitas/mes/${opt}/${gr}`,{method:'get'})
    const js = await res.json()
    document.getElementById('vm').textContent = js
    if(js === 0){
        document.getElementById('vsm').classList.add('bd-red')
    }else{
        document.getElementById('vsm').classList.add('bd-green')
    }
}

async function visitasDia(){
    const res = await fetch(`/visitas/dia/${opt}/${gr}`,{method:'get'})
    const js = await res.json()
    document.getElementById('vh').textContent = js
    if(js === 0){
        document.getElementById('vsd').classList.add('bd-red')
    }else{
        document.getElementById('vsd').classList.add('bd-green')
    }
}

async function visitasMesAnt(){
    const res = await fetch(`/tarefas/mes/anterior/${opt}/${gr}`)
    const js = await res.json()

    metaAtual = js + meta * js
    dia = new Date().getDate()
    // Dias restantes no mês do ano corrente; evita divisão por zero no último dia.
    const diasNoMes = new Date(date.getFullYear(), date.getMonth()+1, 0).getDate()
    metaDiaria = metaAtual/Math.max(diasNoMes - dia, 1)

    document.getElementById('metaMes').textContent = Math.round(metaAtual).toLocaleString('pt-BR')
    document.getElementById('metaDia').textContent = Math.round(metaDiaria).toLocaleString('pt-BR')
}

async function tarefasDias(){
    const res = await fetch(`/tarefas/dia/${opt}/${gr}`)
    const js = await res.json()
    var falta = parseInt(js) - parseInt(metaDiaria)


    document.getElementById('relDia').textContent = js.toLocaleString('pt-BR')
    if(parseInt(js) >= parseInt(metaDiaria)){
        document.getElementById('ttd').classList.add('bd-green')
    }else{
        document.getElementById('ttd').classList.add('bd-red')
    }

    document.getElementById('gpd').textContent = falta.toLocaleString('pt-BR')
    if(falta >= 0){document.getElementById('gd').classList.add('bd-green')}
    else{document.getElementById('gd').classList.add('bd-red')}
}

async function top3Sups(){
    const res = await fetch(`/top3_sups/${opt}/${gr}`)
    const js = await res.json()
    for(item in js['sup']){
        var nome = js['sup'][item] 
        var tt = js['total'][item]

        var li = document.createElement('li','list-group-item')
        li.style.fontSize = '16px'
        li.classList.add('list-group-item')
        li.classList.add('text-truncate')
        li.classList.add('fw-bold')
        li.textContent = `${nomeMin(nome)} - ${tt}`
        document.getElementById('listSup').appendChild(li)
    }
}

async function getGerentes(){
    const res = await fetch(`/get_gerentes/${opt}/${gr}`)
    const js = await res.json()
    for(cont in js['grs']){
        var ger = js['grs'][cont]
        var li = document.createElement('li')
        li.classList.add('list-group-item')
        li.classList.add('d-flex')
        li.classList.add('justify-content-between')
        li.classList.add('align-items-start')
        li.innerHTML = `
        <div class="ms-2 me-auto">
            <div class="fw-bold text-truncate">
                ${nomeMin(ger)}
            </div>
        </div>
        <span class="badge text-bg-light rounded-pill" style="font-size: 14px;">
            ${(js['total'][cont]).toLocaleString('pt-BR')}
        </span>`
        document.getElementById('gers').appendChild(li)
    }
}

async function getAct(){
    try {
        const res = await fetch('/actions/value/')
        const js = await res.json()
        document.getElementById('valorAct').textContent = `R$ ${js}`
    } catch {
        document.getElementById('valorAct').textContent = `R$ --`
    }
}

// Uma falha em um indicador não pode derrubar os demais cards do dashboard.
async function runStep(fn) {
    try { await fn() }
    catch (e) { console.error(`[vista-view] falha em ${fn.name}:`, e) }
}

async function start() {
    await runStep(getAct)
    await runStep(visitasMesAnt)
    await runStep(totalTarefas)
    await runStep(tarefasDias)
    await runStep(top3Unidades)
    await runStep(getUnidades)
    await runStep(getEscalonadas)
    await runStep(visitasMes)
    await runStep(visitasDia)
    await runStep(top3Sups)
    await runStep(getGerentes)
}

start()