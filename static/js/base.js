var porcentagemMeta = 15
var meta = porcentagemMeta/100
var date = new Date()
var strDate = `${date.toLocaleDateString('pt-BR')} - ${date.getHours()}:${date.getMinutes()}`
var dia = null
var metaDiaria = null
var metaAtual = null
var meta = null
var totalMes = null
const act = null
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
    const res = await fetch(`/total_de_tarefas/${opt}/${gr}`,{method:'get'})
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
    const res = await fetch(`/escalonadas/${opt}/${gr}`,{method:'get'})
    const js = await res.json()
    document.getElementById('escalonadas').textContent = js
    if(parseInt(js) === 0){
        document.getElementById('esc').classList.add('bd-green')
    }
    else if(parseInt(js) > 0){
        document.getElementById('esc').classList.add('bd-red')
    }
}

async function visitasMes(){
    const res = await fetch(`/visitas_mes/${opt}/${gr}`,{method:'get'})
    const js = await res.json()
    document.getElementById('vm').textContent = js
    if(js === 0){
        document.getElementById('vsm').classList.add('bd-red')
    }else{
        document.getElementById('vsm').classList.add('bd-green')
    }
}

async function visitasDia(){
    const res = await fetch(`/visitas_dia/${opt}/${gr}`,{method:'get'})
    const js = await res.json()
    document.getElementById('vh').textContent = js
    if(js === 0){
        document.getElementById('vsd').classList.add('bd-red')
    }else{
        document.getElementById('vsd').classList.add('bd-green')
    }
}

async function visitasMesAnt(){
    const res = await fetch(`/tarefas_mes_ant/${opt}/${gr}`)
    const js = await res.json()

    metaAtual = await js + meta * js
    dia = new Date().getDate()
    metaDiaria = metaAtual/(30-dia)
    
    document.getElementById('metaMes').textContent = Math.round(metaAtual).toLocaleString('pt-BR')
    document.getElementById('metaDia').textContent = Math.round(metaDiaria).toLocaleString('pt-BR')
}

async function tarefasDias(){
    const res = await fetch(`/tarefas_dia/${opt}/${gr}`)
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
    const res = await fetch('/get_act_value')
    const js = await res.json()
    try{
        document.getElementById('valorAct').textContent = `R$ ${js}`
    }catch{
        document.getElementById('valorAct').textContent = `R$ 0`
    }
}

async function start() {
    await getAct()
    await visitasMesAnt()
    await totalTarefas()
    await tarefasDias()
    await top3Unidades()
    await getUnidades()
    await getEscalonadas()
    await visitasMes()
    await visitasDia()
    await visitasMesAnt()
    await top3Sups()
    await getGerentes()
}

start()