let currentSource = 'legado';
let chartStatus = null;
let chartExecucao = null;
let state = { uf: null };

window.onload = loadData;

function changeSource(src) {
    currentSource = src;
    const btnLegado = document.getElementById('btn-legado');
    const btnNovo = document.getElementById('btn-novo');
    
    if (btnLegado) btnLegado.className = src === 'legado' ? 'active-btn text-xs px-3 py-1 rounded shadow-sm bg-white font-bold text-blue-600 border' : 'inactive-btn text-xs ml-1 px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
    if (btnNovo) btnNovo.className = src === 'novo' ? 'active-btn text-xs ml-1 px-3 py-1 rounded shadow-sm bg-green-600 font-bold text-white border' : 'inactive-btn text-xs ml-1 px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
    
    resetToCountry();
}

function resetToCountry() {
    state = { uf: null };
    loadData();
}

function handleDrillDown(ufLabel) {
    // Permite clicar na barra tanto no legado quanto no novo
    state.uf = ufLabel;
    loadData();
}

function updateBreadcrumbs() {
    const cUF = document.getElementById('crumb-uf');
    if (state.uf) {
        cUF.classList.remove('hidden');
        document.getElementById('crumb-uf-text').innerText = state.uf;
    } else {
        cUF.classList.add('hidden');
    }
}

async function loadData() {
    updateBreadcrumbs();
    
    try {
        const params = new URLSearchParams({ 
            source: currentSource, 
            uf: state.uf || '' 
        });
        
        const res = await fetch(`/api/situacao?${params}`);
        const data = await res.json();
        
        renderChartStatus(data.status);
        
        const cardExecucao = document.getElementById('cardExecucao');
        const worksSection = document.getElementById('works-section');

        if (data.level === 'uf') {
            cardExecucao.classList.remove('hidden');
            worksSection.classList.add('hidden');
            renderChartExecucao(data.execucao || []);
        } else {
            cardExecucao.classList.add('hidden');
            worksSection.classList.remove('hidden');
            renderWorksTable(data.works || []);
            worksSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
    } catch (err) {
        console.error("Erro na API de Situação:", err);
    }
}

function renderChartStatus(data) {
    const canvas = document.getElementById('chartStatus');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (chartStatus) chartStatus.destroy();
    if (!data || data.length === 0) return;

    let displayData = [...data];
    if (data.length > 8) {
        const top = data.slice(0, 8);
        const others = data.slice(8).reduce((acc, curr) => acc + curr.qtd, 0);
        displayData = [...top, {label: 'Outros', qtd: others}];
    }

    chartStatus = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: displayData.map(d => d.label),
            datasets: [{
                data: displayData.map(d => d.qtd),
                backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b', '#cbd5e1', '#f472b6', '#a8a29e'],
                borderWidth: 2, 
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true, 
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            let value = context.raw || 0;
                            let total = context.chart._metasets[context.datasetIndex].total;
                            let percentage = total > 0 ? ((value * 100) / total).toFixed(1) + "%" : "0%";
                            return ` ${label}: ${value} obras (${percentage})`;
                        }
                    }
                }
            }
        }
    });
}

function renderChartExecucao(data) {
    const canvas = document.getElementById('chartExecucao');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (chartExecucao) chartExecucao.destroy();
    if (!data || data.length === 0) return;

    chartExecucao = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.label),
            datasets: [{
                label: 'Média de Execução Física (%)',
                data: data.map(d => d.fisico),
                backgroundColor: '#10b981',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true, 
            maintainAspectRatio: false,
            scales: { 
                y: { 
                    beginAtZero: true, 
                    max: 100, 
                    ticks: { callback: val => val + '%' } 
                } 
            },
            onClick: (evt, els) => {
                if (els.length > 0) {
                    handleDrillDown(data[els[0].index].label);
                }
            }
        }
    });
}

function renderWorksTable(works) {
    const tbody = document.getElementById('works-body');
    document.getElementById('works-title').innerHTML = `<i class="fas fa-list-ol mr-2 text-blue-600"></i> Obras Físicas: ${state.uf}`;
    
    if(!works || works.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="p-8 text-center text-slate-400">Nenhuma obra com execução física encontrada para este Estado.</td></tr>';
        return;
    }

    tbody.innerHTML = works.map(w => {
        const fisico = parseFloat(w.fisico) || 0;
        const valueStr = fisico.toFixed(1) + '%';
        
        let barColor = 'bg-blue-500';
        if (fisico >= 80) barColor = 'bg-emerald-500';
        else if (fisico < 30) barColor = 'bg-red-500';

        // Lógica de fallback para não dar erro se o ID não existir
        const idRender = w.id 
            ? `<a href="/obra/${w.id}" target="_blank" title="Ver detalhes completos da obra" class="text-blue-600 font-bold hover:underline"><i class="fas fa-external-link-alt mr-1"></i>${w.id}</a>` 
            : '-';

        return `
        <tr class="hover:bg-slate-50 transition border-b border-slate-100">
            <td class="p-3 text-xs font-mono">${idRender}</td>
            <td class="p-3 text-xs font-medium text-slate-700 max-w-md truncate" title="${w.objeto}">${w.objeto || 'Sem Objeto'}</td>
            <td class="p-3 text-xs text-slate-600 font-semibold">${w.especie || 'Não Informado'}</td>
            <td class="p-3 text-xs text-slate-600">${w.cidade}</td>
            <td class="p-3 text-right">
                <div class="flex items-center justify-end">
                    <span class="font-bold text-slate-700 text-xs mr-3 w-12">${valueStr}</span>
                    <div class="w-24 bg-slate-200 rounded-full h-2">
                        <div class="${barColor} h-2 rounded-full" style="width: ${Math.min(fisico, 100)}%"></div>
                    </div>
                </div>
            </td>
        </tr>`;
    }).join('');
}