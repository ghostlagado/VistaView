import colorLib from 'https://cdn.jsdelivr.net/npm/@kurkle/color@0.3.2/+esm';

const ctx = document.getElementById('grafDia');
const piePerf = document.getElementById('piePerf');
var green = '#a7c957'
var red = '#e63946'

fetch(`/graph_days/${opt}/${gr}`)
.then(res=>{
    res.json()
    .then(res=>{
        fetch(`/graph_days_ant/${opt}/${gr}`)
        .then(ress=>{
            ress.json()
            .then(ress=>{
                new Chart(ctx, {
                    type: 'line',
                    data: {
                    labels: res['dia'],
                    
                    datasets: [{
                        data: ress['total'],
                        label: 'Mês Anterior',
                        fill: {
                            target: 'origin',
                        },
                        borderWidth: 1,
                        borderColor: red,
                    },{
                        data: res['total'],
                        label: 'Mês Atual',
                        fill: {
                            target: 'start',
                        },
                        borderWidth: 2,
                        borderColor: green,
                    }]
                    },
                    options: {
                    indexAxis: 'x', 
                    responsive: true,
                    scales: {
                        x: {
                            beginAtZero: false
                        }
                    },
                    plugins: {
                        title: {
                          display: true,
                          text: 'TOTAL REALIZADO POR DIA'
                        }
                    },
                }
                });
            })
        })  
    })
})

fetch(`/get_performance/${opt}/${gr}`)
.then(res=>{
    res.json()
    .then(res=>{
        for(var item in res['st']){
            var p = document.createElement('p')
            var total = res['total'][0] + res['total'][1]
            var perc = ((parseInt(res['total'][item])*100)/total).toFixed(2)
            if(res['st'][item] === 'NO PRAZO'){p.innerHTML = `<span class="fw-bold text-truncate" style="color: ${green};"><i class="bi bi-caret-up-fill"></i> ${parseInt(res['total'][item]).toLocaleString('pt-BR')} - ${perc}%</span>`}
            else{p.innerHTML = `<span class="fw-bold text-truncate" style="color: ${red};"><i class="bi bi-caret-down-fill"></i> ${parseInt(res['total'][item]).toLocaleString('pt-BR')}  - ${perc}%</span>`}
            document.getElementById('perfDd').appendChild(p)
        }

        new Chart(piePerf, {
            type: 'doughnut',
            data: {
                labels: res['st'],
                datasets: [{
                    data: res['total'],
                    borderWidth: 1,
                    backgroundColor: [red, green]
                }]
            },
            options: {
              responsive: true,
              plugins: {
                legend: {
                    display: false,
                },
              }
            },
        }) 
    })
})