// --- VARIÁVEIS GLOBAIS DE CONTROLE ---
let currentSource = 'legado'; // Define se a busca inicial é em 'legado' ou 'novo'
let chartAno = null;    // Armazena a instância do gráfico de linha (Início vs Fim)
let chartStatus = null; // Armazena a instância do gráfico de rosca (Situação)
let chartAtraso = null; // Armazena a instância do gráfico de pizza (Atrasos)
let globalAtrasoData = []; // Cache para salvar os dados de atraso vindos da API e usar no clique

// Define que ao terminar de carregar a janela, a função loadData será executada
window.onload = loadData;

/**
 * Altera a fonte de dados (Botões Legado/Novo) e reseta a interface
 * @param {string} src - 'legado' ou 'novo'
 */
function changeSource(src) {
    currentSource = src; // Atualiza a fonte atual
    
    const btnLegado = document.getElementById('btn-legado');
    const btnNovo = document.getElementById('btn-novo');
    
    // Lógica visual: Troca as classes CSS para destacar o botão ativo e apagar o inativo
    if (btnLegado) btnLegado.className = src === 'legado' 
        ? 'active-btn text-xs px-3 py-1 rounded shadow-sm bg-white font-bold text-blue-600 border' 
        : 'inactive-btn text-xs ml-1 px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
        
    if (btnNovo) btnNovo.className = src === 'novo' 
        ? 'active-btn text-xs ml-1 px-3 py-1 rounded shadow-sm bg-green-600 font-bold text-white border' 
        : 'inactive-btn text-xs ml-1 px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
    
    // Esconde a tabela de detalhes de obras (caso estivesse aberta) para limpar a tela
    document.getElementById('works-section').classList.add('hidden');
    loadData(); // Recarrega os dados da nova fonte
}

/**
 * Função assíncrona que busca os dados temporais no backend Flask
 */
async function loadData() {
    try {
        // Faz a requisição para a rota /api/temporal que você criou no Python
        const res = await fetch(`/api/temporal?source=${currentSource}`);
        const data = await res.json(); // Converte a resposta em objeto JSON

        const inicio = data.anos_inicio || []; // Lista de obras por ano de início
        const fim = data.anos_fim || [];       // Lista de obras por ano de conclusão
        const situacao = data.situacao || []; // Lista de contagem por status (execução, paralisada, etc)
        
        // Salva os dados de atraso (que contém as listas de obras) na variável global
        globalAtrasoData = data.atraso || [];

        // Chama as funções de desenho dos gráficos
        renderChartAno(inicio, fim);
        renderChartStatus(situacao);
        
        const cardAtraso = document.getElementById('cardAtraso');
        
        // O gráfico de atraso (pizza) só faz sentido na fonte 'novo' por ter datas mais precisas
        if (currentSource === 'novo' && globalAtrasoData.length > 0) {
            cardAtraso.classList.remove('hidden'); // Mostra o card do gráfico de pizza
            renderChartAtraso(globalAtrasoData);
        } else {
            cardAtraso.classList.add('hidden'); // Esconde se for legado ou não tiver dados
            document.getElementById('works-section').classList.add('hidden');
        }
        
    } catch (err) {
        console.error("Erro ao carregar dados:", err); // Loga erro no console se o fetch falhar
    }
}

/**
 * Renderiza o gráfico de LINHAS comparando obras iniciadas vs finalizadas por ano
 */
function renderChartAno(inicioData, fimData) {
    const canvas = document.getElementById('chartAno');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (chartAno) chartAno.destroy(); // Destrói o gráfico anterior para não sobrepor

    // Extrai e limpa os anos das duas listas
    const yearsInicio = inicioData.map(d => parseInt(d.ano)).filter(y => !isNaN(y) && y > 1900);
    const yearsFim = fimData.map(d => parseInt(d.ano)).filter(y => !isNaN(y) && y > 1900);

    // Cria um Set para ter anos únicos de ambas as listas e ordena do menor para o maior
    const allYears = new Set([...yearsInicio, ...yearsFim]);
    const sortedYears = Array.from(allYears).sort((a, b) => a - b);

    // Mapeia os dados para garantir que cada ano tenha um valor (ou 0 se não houver obra)
    const dataInicio = sortedYears.map(year => {
        const found = inicioData.find(d => parseInt(d.ano) === year);
        return found ? found.qtd : 0;
    });

    const dataFim = sortedYears.map(year => {
        const found = fimData.find(d => parseInt(d.ano) === year);
        return found ? found.qtd : 0;
    });

    // Cria o gráfico usando a biblioteca Chart.js
    chartAno = new Chart(ctx, {
        type: 'line',
        data: {
            labels: sortedYears, // Eixo X (Anos)
            datasets: [
                {
                    label: 'Obras Iniciadas',
                    data: dataInicio,
                    borderColor: '#3b82f6', // Azul
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    tension: 0.3, // Curvatura da linha
                    fill: true
                },
                {
                    label: 'Obras Finalizadas',
                    data: dataFim,
                    borderColor: '#10b981', // Verde
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
            interaction: { mode: 'index', intersect: false }, // Mostra tooltips das duas linhas ao passar o mouse
            scales: { y: { beginAtZero: true } }
        }
    });
}

/**
 * Renderiza o gráfico de ROSCA mostrando a distribuição de situações (Status)
 */
function renderChartStatus(data) {
    const canvas = document.getElementById('chartStatus');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (chartStatus) chartStatus.destroy();
    if (!data || data.length === 0) return;

    // Limita a exibição: Mostra os 6 principais status e agrupa o restante em "Outros"
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
            plugins: { legend: { position: 'right' } } // Legenda posicionada à direita
        }
    });
}

/**
 * Renderiza o gráfico de PIZZA de atrasos e configura o evento de CLIQUE
 */
function renderChartAtraso(data) {
    const canvas = document.getElementById('chartAtraso');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (chartAtraso) chartAtraso.destroy();

    const labels = data.map(d => d.label);
    const values = data.map(d => d.qtd);

    // Define cores fixas para cada categoria de atraso
    const colors = labels.map(l => {
        if (l.includes('Atrasadas')) return '#ef4444'; // Vermelho
        if (l.includes('No Prazo')) return '#3b82f6';  // Azul
        if (l.includes('Concluídas')) return '#10b981'; // Verde
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
            plugins: { legend: { position: 'right' } },
            // INTERAÇÃO: Ao clicar em uma fatia da pizza, carrega a tabela de detalhes
            onClick: (evt, els) => {
                if (els.length > 0) {
                    const index = els[0].index; // Pega o índice da fatia clicada
                    const clickedLabel = labels[index]; // Pega o nome (Ex: 'Atrasadas')
                    const categoryData = globalAtrasoData.find(d => d.label === clickedLabel); // Busca os dados salvos
                    if (categoryData) {
                        renderAtrasoTable(categoryData); // Renderiza a tabela de obras dessa categoria
                    }
                }
            }
        }
    });
}

/**
 * Renderiza a tabela detalhada de obras após clicar no gráfico de pizza
 * @param {Object} category - Objeto contendo o label, qtd e a lista de obras
 */
function renderAtrasoTable(category) {
    const section = document.getElementById('works-section');
    const tbody = document.getElementById('works-body');
    const title = document.getElementById('works-title');
    
    section.classList.remove('hidden'); // Torna a seção da tabela visível
    
    // Define a cor do ícone no título da tabela conforme a categoria
    let iconColor = 'text-blue-600';
    if(category.label === 'Atrasadas') iconColor = 'text-red-600';
    if(category.label === 'Concluídas') iconColor = 'text-emerald-600';

    title.innerHTML = `<i class="fas fa-list mr-2 ${iconColor}"></i> Obras: ${category.label} (${category.qtd})`;
    
    // Se não houver obras na lista, mostra mensagem de vazio
    if (!category.obras || category.obras.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="p-8 text-center text-slate-400">Nenhum detalhe disponível.</td></tr>';
        return;
    }

    // Mapeia a lista de obras para gerar as linhas (tr) da tabela HTML
    tbody.innerHTML = category.obras.map(w => {
        // Cria o link para a página detalhada da obra (ID)
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
    
    // Faz a tela descer suavemente até a tabela para o usuário ver os dados
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Auxiliar para formatar números em moeda brasileira (R$)
 */
function formatMoney(val) {
    if (!val || val === '0') return 'R$ 0,00';
    return parseFloat(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}