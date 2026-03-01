let currentSource = 'legado';
let chartUF = null;
let chartCity = null;
let chartOrgao = null;
let state = { uf: null, city: null };
let ufDataList = [];
let cityDataList = [];

window.onload = loadData;

function changeSource(src) {
    currentSource = src;
    
    const btnLegado = document.getElementById('btn-legado');
    const btnNovo = document.getElementById('btn-novo');
    
    if (btnLegado) btnLegado.className = src === 'legado' 
        ? 'active-btn text-xs px-3 py-1 rounded shadow-sm bg-white font-bold text-blue-600 border' 
        : 'inactive-btn text-xs ml-1 px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
        
    if (btnNovo) btnNovo.className = src === 'novo' 
        ? 'active-btn text-xs ml-1 px-3 py-1 rounded shadow-sm bg-green-600 font-bold text-white border' 
        : 'inactive-btn text-xs ml-1 px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
    
    resetToCountry();
}

// === CONTROLES DE NAVEGAÇÃO ===
function resetToCountry() {
    state = { uf: null, city: null };
    loadData();
}

function resetToUF() {
    state.city = null;
    loadData();
}

function handleDrillDownUF(ufLabel) {
    state.uf = ufLabel;
    loadData();
}

function handleDrillDownCity(cityLabel) {
    state.city = cityLabel;
    loadData();
}

function updateBreadcrumbs() {
    const cUF = document.getElementById('crumb-uf');
    const cCity = document.getElementById('crumb-city');
    
    if (state.uf) { 
        cUF.classList.remove('hidden'); 
        document.getElementById('crumb-uf-text').innerText = state.uf; 
    } else {
        cUF.classList.add('hidden');
    }

    if (state.city) { 
        cCity.classList.remove('hidden'); 
        document.getElementById('crumb-city-text').innerText = state.city; 
    } else {
        cCity.classList.add('hidden');
    }
}

// === CARREGAMENTO DE DADOS ===
async function loadData() {
    updateBreadcrumbs();

    const params = new URLSearchParams({
        source: currentSource,
        uf: state.uf || '',
        city: state.city || ''
    });

    try {
        const res = await fetch(`/api/financeiro?${params}`);
        const data = await res.json();
        
        updateView(data);
        
    } catch (err) {
        console.error(err);
    }
}

function updateView(data) {
    const cardUF = document.getElementById('cardUF');
    const cardCity = document.getElementById('cardCity');
    const worksSection = document.getElementById('works-section');
    const titleOrgao = document.getElementById('titleOrgao');

    // Sempre atualiza o gráfico de Órgãos (ele respeita o filtro de UF e Cidade via Backend)
    renderChartOrgao(data.orgao || []);
    
    // Altera o título do painel de órgãos dependendo de onde estamos
    if (state.city) titleOrgao.innerHTML = `<i class="fas fa-building text-emerald-500 mr-2"></i>Órgãos em ${state.city}`;
    else if (state.uf) titleOrgao.innerHTML = `<i class="fas fa-building text-emerald-500 mr-2"></i>Órgãos em ${state.uf}`;
    else titleOrgao.innerHTML = `<i class="fas fa-building text-emerald-500 mr-2"></i>Órgãos e Executores (Brasil)`;

    // Se NÃO tem UF selecionada -> Mostra Card UF, Esconde Card City e Obras
    if (!state.uf) {
        cardUF.classList.remove('hidden');
        cardCity.classList.add('hidden');
        worksSection.classList.add('hidden');
        ufDataList = data.uf || [];
        renderChartUF(ufDataList);
    } 
    // Se TEM UF mas NÃO TEM Cidade -> Esconde Card UF, Mostra Card City, Esconde Obras
    else if (state.uf && !state.city) {
        cardUF.classList.add('hidden');
        cardCity.classList.remove('hidden');
        worksSection.classList.add('hidden');
        
        document.getElementById('titleCity').innerHTML = `<i class="fas fa-city text-blue-500 mr-2"></i>Top Municípios - ${state.uf}`;
        cityDataList = data.cidade || [];
        renderChartCity(cityDataList);
    }
    // Se TEM Cidade -> Esconde Gráficos Geográficos, Mostra Tabela de Obras
    else if (state.city) {
        // Mantém o gráfico da cidade visível na tela para não ficar um buraco vazio
        worksSection.classList.remove('hidden');
        document.getElementById('works-title').innerHTML = `<i class="fas fa-file-invoice-dollar mr-2 text-blue-600"></i> Obras em ${state.city}`;
        renderWorksTable(data.works || []);
        
        // Rola a tela até a tabela suavemente
        worksSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// === RENDERIZADORES DE GRÁFICOS ===

function renderChartUF(data) {
    const ctx = document.getElementById('chartUF').getContext('2d');
    if (chartUF) chartUF.destroy();

    chartUF = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.label),
            datasets: [{
                label: 'Investimento (R$)',
                data: data.map(d => d.valor),
                backgroundColor: '#3b82f6',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    ticks: {
                        callback: function(value) {
                            if(value >= 1000000000) return 'R$ ' + (value / 1000000000).toFixed(1) + 'B';
                            return 'R$ ' + (value / 1000000).toFixed(0) + 'M';
                        }
                    }
                }
            },
            onClick: (evt, els) => {
                if (els.length > 0) {
                    const selectedLabel = data[els[0].index].label;
                    handleDrillDownUF(selectedLabel);
                }
            }
        }
    });
}

function renderChartCity(data) {
    const ctx = document.getElementById('chartCity').getContext('2d');
    if (chartCity) chartCity.destroy();

    chartCity = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.label),
            datasets: [{
                label: 'Investimento (R$)',
                data: data.map(d => d.valor),
                backgroundColor: '#0ea5e9', // Azul mais claro para cidade
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    ticks: {
                        callback: function(value) {
                            if(value >= 1000000000) return 'R$ ' + (value / 1000000000).toFixed(1) + 'B';
                            return 'R$ ' + (value / 1000000).toFixed(0) + 'M';
                        }
                    }
                }
            },
            onClick: (evt, els) => {
                if (els.length > 0) {
                    const selectedLabel = data[els[0].index].label;
                    handleDrillDownCity(selectedLabel);
                }
            }
        }
    });
}

function renderChartOrgao(data) {
    const ctx = document.getElementById('chartOrgao').getContext('2d');
    if (chartOrgao) chartOrgao.destroy();

    chartOrgao = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(d => d.label.substring(0, 20) + '...'), // Encurta nomes muito longos
            datasets: [{
                data: data.map(d => d.valor),
                backgroundColor: [
                    '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6', '#64748b', '#cbd5e1'
                ],
                borderWidth: 1,
                borderColor: '#ffffff'
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
                            return label + ': ' + formatMoney(value);
                        }
                    }
                }
            }
        }
    });
}

function renderWorksTable(works) {
    const tbody = document.getElementById('works-body');
    
    if(!works || works.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="p-8 text-center text-slate-400">Nenhuma obra financeira encontrada.</td></tr>';
        return;
    }

    tbody.innerHTML = works.map(w => {
        // Lógica de fallback para não dar erro se o ID não existir
        const idRender = w.id 
            ? `<a href="/obra/${w.id}" target="_blank" title="Ver detalhes completos da obra" class="text-blue-600 font-bold hover:underline"><i class="fas fa-external-link-alt mr-1"></i>${w.id}</a>` 
            : '-';

        return `
        <tr class="hover:bg-blue-50 border-b border-slate-100 transition">
            <td class="p-3 text-xs font-mono">${idRender}</td>
            <td class="p-3 text-xs font-medium text-slate-700 max-w-md truncate" title="${w.objeto}">${w.objeto || 'Sem Objeto'}</td>
            <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] bg-slate-100 border uppercase font-bold text-slate-500">${w.situacao}</span></td>
            <td class="p-3 text-right text-emerald-600 font-mono text-xs font-bold">${formatMoney(w.valor)}</td>
        </tr>
    `}).join('');
}

function formatMoney(val) {
    if (!val || val === '0') return 'R$ 0,00';
    return parseFloat(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}