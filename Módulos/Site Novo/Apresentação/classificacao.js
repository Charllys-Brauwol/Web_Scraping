// --- VARIÁVEIS GLOBAIS ---
let currentSource = 'legado'; // Define a fonte inicial como 'legado'
let chartNatureza = null;     // Armazena a instância do gráfico de Pizza (Natureza)
let chartFuncao = null;       // Armazena a instância do gráfico de Barras (Função Social)

// Define que a função loadData será a primeira a ser executada ao carregar a página
window.onload = loadData;

/**
 * Altera a fonte de dados (Legado/Novo) e atualiza os gráficos
 * @param {string} src - A fonte escolhida
 */
function changeSource(src) {
    currentSource = src; // Atualiza a variável de controle
    // Altera as classes CSS dos botões para indicar qual está ativo (feedback visual)
    document.getElementById('btn-legado').className = src === 'legado' ? 'active-btn text-xs' : 'inactive-btn text-xs';
    document.getElementById('btn-novo').className = src === 'novo' ? 'active-btn bg-green-600 text-xs ml-1' : 'inactive-btn text-xs ml-1';
    loadData(); // Recarrega os dados com base na nova fonte
}

/**
 * Função assíncrona que busca as classificações no backend Flask
 */
async function loadData() {
    try {
        // Faz a requisição para a API de classificação passando a fonte como parâmetro
        const res = await fetch(`/api/classificacao?source=${currentSource}`);
        const data = await res.json(); // Converte a resposta em JSON
        
        // Chama as funções para renderizar os dois gráficos com os dados recebidos
        renderChartNatureza(data.natureza);
        renderChartFuncao(data.funcao);
        
    } catch (err) {
        // Exibe erro no console caso a comunicação com o servidor falhe
        console.error("Erro ao carregar classificações:", err);
    }
}

/**
 * Renderiza o gráfico de PIZZA para a Natureza da Obra
 * @param {Array} data - Lista de objetos com label e qtd
 */
function renderChartNatureza(data) {
    const ctx = document.getElementById('chartNatureza').getContext('2d');
    // Se o gráfico já existir, destrói a instância anterior para evitar bugs visuais
    if (chartNatureza) chartNatureza.destroy();

    chartNatureza = new Chart(ctx, {
        type: 'pie', // Tipo Pizza
        data: {
            labels: data.map(d => d.label), // Extrai os nomes (Ex: Reforma, Construção)
            datasets: [{
                data: data.map(d => d.qtd), // Extrai as quantidades
                backgroundColor: [
                    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b'
                ], // Cores variadas para cada fatia
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' } // Posiciona a legenda à direita do gráfico
            }
        }
    });
}

/**
 * Renderiza o gráfico de BARRAS HORIZONTAIS para a Função Social
 * @param {Array} data - Lista de objetos com label e qtd
 */
function renderChartFuncao(data) {
    const ctx = document.getElementById('chartFuncao').getContext('2d');
    // Destrói o gráfico anterior se ele já estiver na tela
    if (chartFuncao) chartFuncao.destroy();

    chartFuncao = new Chart(ctx, {
        type: 'bar', // Tipo Barras
        data: {
            labels: data.map(d => d.label), // Nomes (Ex: Educação, Saúde)
            datasets: [{
                label: 'Quantidade de Obras',
                data: data.map(d => d.qtd),
                backgroundColor: '#10b981', // Cor verde esmeralda
                borderRadius: 4 // Arredonda levemente as pontas das barras
            }]
        },
        options: {
            indexAxis: 'y', // Inverte os eixos para as barras ficarem deitadas (horizontais)
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false } // Esconde a legenda para simplificar a visualização
            }
        }
    });
}