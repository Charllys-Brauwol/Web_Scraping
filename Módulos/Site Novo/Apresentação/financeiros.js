// --- VARIÁVEIS DE ESTADO E CONTROLE ---
let currentSource = 'legado'; // Fonte de dados ativa ('legado' ou 'novo')
let chartUF = null;           // Instância do gráfico de barras por Estado
let chartCity = null;         // Instância do gráfico de barras por Município
let chartOrgao = null;        // Instância do gráfico de rosca por Órgão/Executor
let state = { uf: null, city: null }; // Objeto que rastreia a navegação atual (filtros)
let ufDataList = [];          // Cache dos dados de estados
let cityDataList = [];        // Cache dos dados de cidades

// Define que a função loadData será executada assim que a página terminar de carregar
window.onload = loadData;

/**
 * Altera a fonte de dados e reseta a navegação para o nível nacional
 * @param {string} src - A nova fonte ('legado' ou 'novo')
 */
function changeSource(src) {
    currentSource = src;
    
    const btnLegado = document.getElementById('btn-legado');
    const btnNovo = document.getElementById('btn-novo');
    
    // Atualiza a aparência dos botões (feedback visual de seleção)
    if (btnLegado) btnLegado.className = src === 'legado' 
        ? 'active-btn text-xs px-3 py-1 rounded shadow-sm bg-white font-bold text-blue-600 border' 
        : 'inactive-btn text-xs ml-1 px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
        
    if (btnNovo) btnNovo.className = src === 'novo' 
        ? 'active-btn text-xs ml-1 px-3 py-1 rounded shadow-sm bg-green-600 font-bold text-white border' 
        : 'inactive-btn text-xs ml-1 px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
    
    resetToCountry(); // Volta para a visão Brasil ao trocar a fonte
}

// === FUNÇÕES DE NAVEGAÇÃO (DRILL-DOWN) ===

// Reseta todos os filtros e volta para a visão Brasil
function resetToCountry() {
    state = { uf: null, city: null };
    loadData();
}

// Remove o filtro de cidade mas mantém o de Estado (UF)
function resetToUF() {
    state.city = null;
    loadData();
}

// Define o Estado selecionado e carrega os dados
function handleDrillDownUF(ufLabel) {
    state.uf = ufLabel;
    loadData();
}

// Define a Cidade selecionada e carrega os dados
function handleDrillDownCity(cityLabel) {
    state.city = cityLabel;
    loadData();
}

/**
 * Atualiza os indicadores de caminho (Breadcrumbs) no topo da página
 */
function updateBreadcrumbs() {
    const cUF = document.getElementById('crumb-uf');
    const cCity = document.getElementById('crumb-city');
    
    // Se houver UF selecionada, mostra o botão no caminho, senão esconde
    if (state.uf) { 
        cUF.classList.remove('hidden'); 
        document.getElementById('crumb-uf-text').innerText = state.uf; 
    } else {
        cUF.classList.add('hidden');
    }

    // Se houver Cidade selecionada, mostra o botão no caminho, senão esconde
    if (state.city) { 
        cCity.classList.remove('hidden'); 
        document.getElementById('crumb-city-text').innerText = state.city; 
    } else {
        cCity.classList.add('hidden');
    }
}

// === PROCESSAMENTO DE DADOS ===

/**
 * Faz a requisição para a API de finanças do Flask com base nos filtros atuais
 */
async function loadData() {
    updateBreadcrumbs(); // Atualiza o rastro de navegação visual

    // Prepara os parâmetros para a URL (Query String)
    const params = new URLSearchParams({
        source: currentSource,
        uf: state.uf || '',
        city: state.city || ''
    });

    try {
        // Busca os dados financeiros no servidor
        const res = await fetch(`/api/financeiro?${params}`);
        const data = await res.json();
        
        updateView(data); // Atualiza os componentes da tela com os novos dados
        
    } catch (err) {
        console.error("Erro ao carregar dados financeiros:", err);
    }
}

/**
 * Gerencia a visibilidade de gráficos e tabelas conforme o nível de navegação
 * @param {Object} data - Dados retornados pela API
 */
function updateView(data) {
    const cardUF = document.getElementById('cardUF');
    const cardCity = document.getElementById('cardCity');
    const worksSection = document.getElementById('works-section');
    const titleOrgao = document.getElementById('titleOrgao');

    // O gráfico de Órgãos é atualizado em todos os níveis
    renderChartOrgao(data.orgao || []);
    
    // Altera dinamicamente o título do gráfico de rosca
    if (state.city) titleOrgao.innerHTML = `<i class="fas fa-building text-emerald-500 mr-2"></i>Órgãos em ${state.city}`;
    else if (state.uf) titleOrgao.innerHTML = `<i class="fas fa-building text-emerald-500 mr-2"></i>Órgãos em ${state.uf}`;
    else titleOrgao.innerHTML = `<i class="fas fa-building text-emerald-500 mr-2"></i>Órgãos e Executores (Brasil)`;

    // LÓGICA DE VISIBILIDADE (DRILL-DOWN):
    
    // Nível 1: Visão Brasil (Sem UF selecionada)
    if (!state.uf) {
        cardUF.classList.remove('hidden'); // Mostra gráfico de estados
        cardCity.classList.add('hidden');  // Esconde gráfico de cidades
        worksSection.classList.add('hidden'); // Esconde lista de obras
        ufDataList = data.uf || [];
        renderChartUF(ufDataList);
    } 
    // Nível 2: Visão Estado (UF selecionada, sem Cidade)
    else if (state.uf && !state.city) {
        cardUF.classList.add('hidden');    // Esconde gráfico de estados
        cardCity.classList.remove('hidden'); // Mostra gráfico de cidades
        worksSection.classList.add('hidden');
        
        document.getElementById('titleCity').innerHTML = `<i class="fas fa-city text-blue-500 mr-2"></i>Top Municípios - ${state.uf}`;
        cityDataList = data.cidade || [];
        renderChartCity(cityDataList);
    }
    // Nível 3: Visão Cidade (Cidade selecionada)
    else if (state.city) {
        worksSection.classList.remove('hidden'); // Mostra a tabela detalhada de obras
        document.getElementById('works-title').innerHTML = `<i class="fas fa-file-invoice-dollar mr-2 text-blue-600"></i> Obras em ${state.city}`;
        renderWorksTable(data.works || []);
        
        // Rola a tela automaticamente para a tabela
        worksSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// === RENDERIZADORES DE GRÁFICOS (CHART.JS) ===

/**
 * Cria o gráfico de barras horizontais para os Estados
 */
function renderChartUF(data) {
    const ctx = document.getElementById('chartUF').getContext('2d');
    if (chartUF) chartUF.destroy(); // Limpa o gráfico anterior

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
            indexAxis: 'y', // Inverte para barras horizontais
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    ticks: {
                        // Formata os números do eixo X para Milhões (M) ou Bilhões (B)
                        callback: function(value) {
                            if(value >= 1000000000) return 'R$ ' + (value / 1000000000).toFixed(1) + 'B';
                            return 'R$ ' + (value / 1000000).toFixed(0) + 'M';
                        }
                    }
                }
            },
            // Clique em uma barra: entra no nível do Estado
            onClick: (evt, els) => {
                if (els.length > 0) {
                    const selectedLabel = data[els[0].index].label;
                    handleDrillDownUF(selectedLabel);
                }
            }
        }
    });
}

/**
 * Cria o gráfico de barras horizontais para os Municípios (Cidades)
 */
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
                backgroundColor: '#0ea5e9', // Cor diferente para cidades
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
            // Clique em uma barra: entra no nível da Cidade e mostra a tabela de obras
            onClick: (evt, els) => {
                if (els.length > 0) {
                    const selectedLabel = data[els[0].index].label;
                    handleDrillDownCity(selectedLabel);
                }
            }
        }
    });
}

/**
 * Cria o gráfico de rosca (Doughnut) para a distribuição por Órgão/Executor
 */
function renderChartOrgao(data) {
    const ctx = document.getElementById('chartOrgao').getContext('2d');
    if (chartOrgao) chartOrgao.destroy();

    chartOrgao = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(d => d.label.substring(0, 20) + '...'), // Corta nomes longos na legenda
            datasets: [{
                data: data.map(d => d.valor),
                backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6', '#64748b', '#cbd5e1'],
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
                        // Formata o valor monetário ao passar o mouse sobre a fatia
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

/**
 * Preenche a tabela final com a lista de obras e seus valores individuais
 * @param {Array} works - Lista de obras vindas da API
 */
function renderWorksTable(works) {
    const tbody = document.getElementById('works-body');
    
    // Tratamento caso não existam obras para a seleção
    if(!works || works.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="p-8 text-center text-slate-400">Nenhuma obra financeira encontrada.</td></tr>';
        return;
    }

    // Mapeia o array de obras em linhas de tabela HTML
    tbody.innerHTML = works.map(w => {
        // Gera link para os detalhes da obra caso o ID exista
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

/**
 * Função utilitária para formatar números brutos em moeda brasileira (R$)
 * @param {number} val - O valor numérico
 */
function formatMoney(val) {
    if (!val || val === '0') return 'R$ 0,00';
    return parseFloat(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}