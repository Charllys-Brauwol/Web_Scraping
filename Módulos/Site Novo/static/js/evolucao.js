let currentSource = 'legado';
let chartAno = null;
let chartStatus = null;
let chartAtraso = null;
let globalAtrasoData = []; // Salva os dados para a tabela

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
    
    // Esconde a tabela de detalhe se trocar de fonte
    document.getElementById('works-section').classList.add('hidden');
    loadData();
}

async function loadData() {
    try {
        const res = await fetch(`/api/temporal?source=${currentSource}`);
        const data = await res.json();

        const inicio = data.anos_inicio || [];
        const fim = data.anos_fim || [];
        const situacao = data.situacao || [];
        
        // Guarda na variável global para o clique
        globalAtrasoData = data.atraso || [];

        renderChartAno(inicio, fim);
        renderChartStatus(situacao);
        
        const cardAtraso = document.getElementById('cardAtraso');
        
        if (currentSource === 'novo' && globalAtrasoData.length > 0) {
            cardAtraso.classList.remove('hidden');
            renderChartAtraso(globalAtrasoData);
        } else {
            cardAtraso.classList.add('hidden');
            document.getElementById('works-section').classList.add('hidden');
        }
        
    } catch (err) {
        console.error("Erro ao carregar dados:", err);
    }
}

function renderChartAno(inicioData, fimData) {
    const canvas = document.getElementById('chartAno');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (chartAno) chartAno.destroy();

    const yearsInicio = inicioData.map(d => parseInt(d.ano)).filter(y => !isNaN(y) && y > 1900);
    const yearsFim = fimData.map(d => parseInt(d.ano)).filter(y => !isNaN(y) && y > 1900);

    const allYears = new Set([...yearsInicio, ...yearsFim]);
    const sortedYears = Array.from(allYears).sort((a, b) => a - b);

    const dataInicio = sortedYears.map(year => {
        const found = inicioData.find(d => parseInt(d.ano) === year);
        return found ? found.qtd : 0;
    });

    const dataFim = sortedYears.map(year => {
        const found = fimData.find(d => parseInt(d.ano) === year);
        return found ? found.qtd : 0;
    });

    chartAno = new Chart(ctx, {
        type: 'line',
        data: {
            labels: sortedYears,
            datasets: [
                {
                    label: 'Obras Iniciadas',
                    data: dataInicio,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Obras Finalizadas',
                    data: dataFim,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: { y: { beginAtZero: true } }
        }
    });
}

function renderChartStatus(data) {
    const canvas = document.getElementById('chartStatus');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (chartStatus) chartStatus.destroy();
    if (!data || data.length === 0) return;

    let displayData = [...data]; 
    if (data.length > 6) {
        const top = data.slice(0, 6);
        const others = data.slice(6).reduce((acc, curr) => acc + curr.qtd, 0);
        displayData = [...top, {sit: 'Outros', qtd: others}];
    }

    chartStatus = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: displayData.map(d => d.sit || d.label), 
            datasets: [{
                data: displayData.map(d => d.qtd),
                backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6', '#64748b', '#cbd5e1'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right' } }
        }
    });
}

// === LÓGICA DE CLIQUE E TABELA DE ATRASOS ===
function renderChartAtraso(data) {
    const canvas = document.getElementById('chartAtraso');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (chartAtraso) chartAtraso.destroy();

    const labels = data.map(d => d.label);
    const values = data.map(d => d.qtd);

    const colors = labels.map(l => {
        if (l.includes('Atrasadas')) return '#ef4444'; 
        if (l.includes('No Prazo')) return '#3b82f6'; 
        if (l.includes('Concluídas')) return '#10b981'; 
        return '#cbd5e1'; 
    });

    chartAtraso = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 1,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' }
            },
            // AQUI É ONDE O CLIQUE ACONTECE
            onClick: (evt, els) => {
                if (els.length > 0) {
                    const index = els[0].index;
                    const clickedLabel = labels[index];
                    const categoryData = globalAtrasoData.find(d => d.label === clickedLabel);
                    if (categoryData) {
                        renderAtrasoTable(categoryData);
                    }
                }
            }
        }
    });
}

function renderAtrasoTable(category) {
    const section = document.getElementById('works-section');
    const tbody = document.getElementById('works-body');
    const title = document.getElementById('works-title');
    
    // Mostra a sessão
    section.classList.remove('hidden');
    
    // Atualiza o Título e as cores dependendo do tipo
    let iconColor = 'text-blue-600';
    if(category.label === 'Atrasadas') iconColor = 'text-red-600';
    if(category.label === 'Concluídas') iconColor = 'text-emerald-600';

    title.innerHTML = `<i class="fas fa-list mr-2 ${iconColor}"></i> Obras: ${category.label} (${category.qtd})`;
    
    if (!category.obras || category.obras.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="p-8 text-center text-slate-400">Nenhum detalhe disponível.</td></tr>';
        return;
    }

    // Monta as linhas da tabela transformando o ID em Link
    tbody.innerHTML = category.obras.map(w => {
        const idRender = w.id 
            ? `<a href="/obra/${w.id}" target="_blank" title="Ver detalhes completos da obra" class="text-blue-600 font-bold hover:underline"><i class="fas fa-external-link-alt mr-1"></i>${w.id}</a>` 
            : '-';

        return `
        <tr class="hover:bg-yellow-50 border-b border-slate-100 transition">
            <td class="p-3 text-xs font-mono">${idRender}</td>
            <td class="p-3 text-xs font-medium text-slate-700 max-w-md truncate" title="${w.objeto}">${w.objeto || 'Sem Objeto'}</td>
            <td class="p-3 text-xs text-slate-600">${w.cidade || '-'}</td>
            <td class="p-3 text-xs text-slate-500">
                <span class="font-bold uppercase text-[10px] bg-slate-100 border px-2 py-0.5 rounded mr-1">${w.situacao}</span>
                <br>Data Prevista: <span class="text-slate-800 font-semibold">${w.data_fim}</span>
            </td>
            <td class="p-3 text-right text-emerald-600 font-mono text-xs font-bold">${formatMoney(w.valor)}</td>
        </tr>
    `}).join('');
    
    // Rola a tela até a tabela suavemente
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function formatMoney(val) {
    if (!val || val === '0') return 'R$ 0,00';
    return parseFloat(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}