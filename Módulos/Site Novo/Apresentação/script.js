// --- VARIÁVEIS DE ESTADO GLOBAL ---
let fonteAtual = 'legado'; // Controla se estamos vendo dados de ministérios (legado) ou novos (APIs)
let estadoNav = { regiao: null, uf: null, cidade: null }; // Objeto que guarda onde o usuário está "navegando" no momento
let graficoNav = null; // Guarda a instância do gráfico Chart.js para que possa ser destruído/atualizado
let dadosDetalhamento = []; // Armazena a lista de regiões/estados/cidades que aparece na tabela do meio
let configOrdenacao = { chave: 'qtd', ordem: 'desc' }; // Controla qual coluna da tabela está ordenada e em qual direção

// Define que a função carregarDados será a primeira a rodar quando a página abrir
window.onload = carregarDados;

/**
 * Altera a fonte de dados entre 'legado' e 'novo' e reseta a navegação para o nível Brasil
 * @param {string} fonte - O nome da fonte selecionada
 */
function mudarFonte(fonte) {
    fonteAtual = fonte; // Atualiza a variável global
    // Altera as classes CSS dos botões para dar feedback visual de qual está ativo
    document.getElementById('btn-legado').className = fonte === 'legado' ? 'active-btn text-xs px-3 py-1 rounded shadow-sm bg-white font-bold text-blue-600 border' : 'inactive-btn text-xs px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
    document.getElementById('btn-novo').className = fonte === 'novo' ? 'active-btn bg-green-600 text-xs ml-1 px-3 py-1 rounded shadow-sm font-bold text-white border' : 'inactive-btn text-xs ml-1 px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
    voltarParaBrasil(); // Ao mudar a fonte, sempre volta para a visão geral do país
}

// Funções de navegação para resetar os níveis do objeto estadoNav
function voltarParaBrasil() { estadoNav = { regiao: null, uf: null, cidade: null }; carregarDados(); }
function voltarParaRegiao() { estadoNav.uf = null; estadoNav.cidade = null; carregarDados(); }

/**
 * Gerencia a descida de nível (Ex: Clicou em 'Nordeste', vai para os estados do Nordeste)
 * @param {string} rotulo - O nome do local clicado (Região, UF ou Cidade)
 */
function navegarParaNivel(rotulo) {
    if (!estadoNav.regiao) { estadoNav.regiao = rotulo; carregarDados(); } // Se não tinha região, define a região
    else if (!estadoNav.uf) { estadoNav.uf = rotulo; carregarDados(); } // Se já tinha região, define a UF
    else { 
        estadoNav.cidade = rotulo; // Se já tinha UF, define a cidade
        renderizarTabelaRegioes(); // Re-renderiza a tabela para destacar a linha selecionada
        carregarDados(); // Carrega as obras específicas dessa cidade
    }
}

/**
 * Faz a requisição AJAX (fetch) para o backend Python e traz os dados JSON
 */
async function carregarDados() {
    atualizarMigalhasPao(); // Atualiza o texto (Ex: BRASIL > NORDESTE) no topo
    document.getElementById('total-qtd').innerText = '...'; // Coloca um carregando visual
    
    // Cria os parâmetros de URL para enviar ao Flask (Ex: ?source=legado&region=Norte)
    const parametros = new URLSearchParams({
        source: fonteAtual,
        region: estadoNav.regiao || '',
        uf: estadoNav.uf || '',
        city: estadoNav.cidade || ''
    });

    try {
        // Faz a chamada para a rota de Drilldown que você criou no Python
        const resposta = await fetch(`/api/drilldown?${parametros}`);
        const dados = await resposta.json();
        
        // Atualiza os números grandes (KPIs) no topo da página
        document.getElementById('total-qtd').innerText = dados.totals.qtd.toLocaleString('pt-BR');
        document.getElementById('total-valor').innerText = formatarMoeda(dados.totals.valor);

        // Se o usuário não selecionou uma cidade, os dados da tabela do meio vêm do breakdown (lista de locais)
        if (!estadoNav.cidade || dadosDetalhamento.length === 0) {
            dadosDetalhamento = dados.breakdown || [];
        }
        
        atualizarInterface(dados); // Chama a função que desenha os elementos na tela
    } catch (erro) { console.error("Erro ao carregar dados:", erro); }
}

/**
 * Distribui os dados recebidos para o gráfico e para as tabelas
 * @param {Object} dados - O JSON retornado pela API
 */
function atualizarInterface(dados) {
    const tituloGrafico = document.getElementById('chart-title');
    const tituloTabela = document.getElementById('table-title');
    const secaoObras = document.getElementById('works-section');

    // 1. Atualização do Gráfico
    if (estadoNav.uf) {
        tituloGrafico.innerText = "Ranking (Qtd)"; // Muda o título quando estamos em um estado
        renderizarGrafico(dadosDetalhamento.slice(0, 15)); // Mostra as 15 cidades com mais obras
    } else {
        tituloGrafico.innerText = estadoNav.regiao ? `${estadoNav.regiao}` : "Regiões do Brasil";
        renderizarGrafico(dadosDetalhamento); // Mostra as regiões ou estados
    }

    // 2. Atualização da Tabela do Meio (Distribuição Geográfica)
    tituloTabela.innerText = estadoNav.uf ? `Detalhes de ${estadoNav.uf}` : "Distribuição Geográfica";
    renderizarTabelaRegioes();

    // 3. Atualização da Tabela de Obras (Lista detalhada no fim da página)
    if (estadoNav.uf) {
        secaoObras.classList.remove('hidden'); // Mostra a seção se houver um estado selecionado
        document.getElementById('works-subtitle').innerText = estadoNav.cidade 
            ? `Filtrando: ${estadoNav.cidade}` 
            : `Todas as obras: ${estadoNav.uf}`;
        renderizarTabelaObras(dados.works); // Renderiza a lista de IDs e Objetos das obras
    } else {
        secaoObras.classList.add('hidden'); // Esconde a seção se estiver na visão nacional/regional
    }
}

/**
 * Controla qual coluna a tabela será ordenada (Qtd ou Valor)
 * @param {string} chave - A chave do objeto (Ex: 'valor')
 */
function ordenarTabela(chave) {
    // Se clicar na mesma chave, inverte a ordem (ASC/DESC), senão define como DESC
    if (configOrdenacao.chave === chave) configOrdenacao.ordem = configOrdenacao.ordem === 'desc' ? 'asc' : 'desc';
    else { configOrdenacao.chave = chave; configOrdenacao.ordem = 'desc'; }
    renderizarTabelaRegioes(); // Atualiza o desenho da tabela com a nova ordem
}

/**
 * Renderiza as linhas da tabela central (Distribuição Geográfica)
 */
function renderizarTabelaRegioes() {
    const corpoTabela = document.getElementById('table-body');
    // Aplica a ordenação configurada no array de dados
    dadosDetalhamento.sort((a, b) => {
        let valorA = a[configOrdenacao.chave];
        let valorB = b[configOrdenacao.chave];
        return configOrdenacao.ordem === 'asc' ? valorA - valorB : valorB - valorA;
    });

    // Gera o HTML das linhas mapeando o array de dados
    corpoTabela.innerHTML = dadosDetalhamento.map(item => {
        const estaAtivo = estadoNav.cidade === item.label; // Verifica se esta linha é a cidade selecionada
        const classeFundo = estaAtivo ? 'bg-blue-100 border-l-4 border-blue-600' : 'hover:bg-slate-50';
        return `
        <tr class="${classeFundo} cursor-pointer transition border-b border-slate-50" onclick="navegarParaNivel('${item.label}')">
            <td class="p-3 font-medium text-slate-700 truncate max-w-[150px]" title="${item.label}">${item.label}</td>
            <td class="p-3 text-right font-bold text-blue-600">${item.qtd}</td>
            <td class="p-3 text-right text-slate-500 font-mono text-xs">${formatarMoeda(item.valor)}</td>
        </tr>`
    }).join(''); // O .join('') transforma o array de strings em uma única string HTML
}

/**
 * Renderiza a lista final de obras (Fundo da página) com links para os detalhes
 * @param {Array} obras - Lista de obras vindas da API
 */
function renderizarTabelaObras(obras) {
    const corpoTabelaObras = document.getElementById('works-body');
    document.getElementById('works-count').innerText = obras.length > 0 ? `${obras.length.toLocaleString()} obras` : 'Vazio';
    
    if(!obras || obras.length === 0) {
        corpoTabelaObras.innerHTML = '<tr><td colspan="6" class="p-8 text-center text-slate-400">Nenhuma obra encontrada.</td></tr>';
        return;
    }

    corpoTabelaObras.innerHTML = obras.map(obra => {
        // Se houver ID, cria o link que abre a página de detalhes (Ex: /obra/123)
        const idRenderizado = obra.id 
            ? `<a href="/obra/${obra.id}" target="_blank" title="Ver detalhes completos da obra" class="text-blue-600 font-bold hover:underline"><i class="fas fa-external-link-alt mr-1"></i>${obra.id}</a>` 
            : '-';

        return `
        <tr class="hover:bg-yellow-50 border-b border-slate-100 transition">
            <td class="p-3 text-xs font-mono">${idRenderizado}</td>
            <td class="p-3 text-xs font-medium text-slate-700 max-w-md truncate" title="${obra.objeto}">${obra.objeto}</td>
            <td class="p-3 text-xs text-slate-600">${obra.cidade || estadoNav.uf}</td>
            <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] bg-slate-100 border uppercase font-bold text-slate-500">${obra.situacao}</span></td>
            <td class="p-3 text-right text-emerald-600 font-mono text-xs font-bold">${formatarMoeda(obra.valor)}</td>
        </tr>
    `}).join('');
}

/**
 * Cria ou atualiza o gráfico de barras laterais (Chart.js)
 * @param {Array} itens - Dados de rótulos e valores para o gráfico
 */
function renderizarGrafico(itens) {
    const contexto = document.getElementById('navChart').getContext('2d');
    
    // Se o gráfico já existe, ele precisa ser destruído para evitar sobreposição de dados
    if (graficoNav) graficoNav.destroy();
    
    // Instancia um novo gráfico de barras horizontais
    graficoNav = new Chart(contexto, {
        type: 'bar',
        data: {
            labels: itens.map(i => i.label),
            datasets: [{
                label: 'Obras',
                data: itens.map(i => i.qtd),
                backgroundColor: '#3b82f6', // Cor azul do Tailwind
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y', // Transforma em barras horizontais
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } }, // Esconde a legenda para ganhar espaço
            // Adiciona evento de clique nas barras para navegar para o próximo nível
            onClick: (evento, elementos) => {
                if (elementos.length > 0) navegarParaNivel(itens[elementos[0].index].label);
            }
        }
    });
}

/**
 * Atualiza o caminho de navegação (Breadcrumbs) no topo da página
 */
function atualizarMigalhasPao() {
    const migalhaRegiao = document.getElementById('crumb-region');
    const migalhaUF = document.getElementById('crumb-uf');
    
    // Mostra ou esconde as partes do caminho baseado no estadoNav
    if(estadoNav.regiao) { 
        migalhaRegiao.classList.remove('hidden'); 
        document.getElementById('crumb-region-text').innerText = estadoNav.regiao; 
    } else migalhaRegiao.classList.add('hidden');

    if(estadoNav.uf) { 
        migalhaUF.classList.remove('hidden'); 
        document.getElementById('crumb-uf-text').innerText = estadoNav.uf; 
    } else migalhaUF.classList.add('hidden');
}

/**
 * Formata um número bruto em moeda Real (BRL)
 * @param {number} valor - O valor numérico
 */
function formatarMoeda(valor) {
    if (!valor) return 'R$ 0,00';
    return parseFloat(valor).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}