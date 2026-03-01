let currentSource = 'legado';
let chartNatureza = null;
let chartFuncao = null;

window.onload = loadData;

function changeSource(src) {
    currentSource = src;
    document.getElementById('btn-legado').className = src === 'legado' ? 'active-btn text-xs' : 'inactive-btn text-xs';
    document.getElementById('btn-novo').className = src === 'novo' ? 'active-btn bg-green-600 text-xs ml-1' : 'inactive-btn text-xs ml-1';
    loadData();
}

async function loadData() {
    try {
        const res = await fetch(`/api/classificacao?source=${currentSource}`);
        const data = await res.json();
        
        renderChartNatureza(data.natureza);
        renderChartFuncao(data.funcao);
        
    } catch (err) {
        console.error(err);
    }
}

function renderChartNatureza(data) {
    const ctx = document.getElementById('chartNatureza').getContext('2d');
    if (chartNatureza) chartNatureza.destroy();

    chartNatureza = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.map(d => d.label),
            datasets: [{
                data: data.map(d => d.qtd),
                backgroundColor: [
                    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });
}

function renderChartFuncao(data) {
    const ctx = document.getElementById('chartFuncao').getContext('2d');
    if (chartFuncao) chartFuncao.destroy();

    chartFuncao = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.label),
            datasets: [{
                label: 'Quantidade de Obras',
                data: data.map(d => d.qtd),
                backgroundColor: '#10b981',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            }
        }
    });
}