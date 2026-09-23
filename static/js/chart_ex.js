import colorLib from 'https://cdn.jsdelivr.net/npm/@kurkle/color@0.3.2/+esm';

const ctx = document.getElementById('grafDia');
const piePerf = document.getElementById('piePerf');
var green = '#a7c957'
var red = '#e63946'

new Chart(ctx, {
    type: 'line',
    data: {
    labels: [1, 2],
    
    datasets: [{
        data: [2.000, 1.520],
        label: 'Mês Anterior',
        fill: {
            target: 'origin',
        },
        borderWidth: 1,
        borderColor: red,
    },{
        data: [3.500, 1.450],
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

new Chart(piePerf, {
    type: 'doughnut',
    data: {
        labels: ['Dentro do Prazo', 'Fora do Prazo'],
        datasets: [{
            data: [115.48900, 13.256],
            borderWidth: 1,
            backgroundColor: [green, red]
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