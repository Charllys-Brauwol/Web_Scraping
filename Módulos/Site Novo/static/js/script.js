let fonteAtual = 'legado';
let estadoNav = { regiao: null, uf: null, cidade: null };
let graficoNav = null;
let dadosDetalhamento = []; 
let configOrdenacao = { chave: 'qtd', ordem: 'desc' };

window.onload = carregarDados;

function mudarFonte(fonte) {
    fonteAtual = fonte;
    document.getElementById('btn-legado').className = fonte === 'legado' ? 'active-btn text-xs px-3 py-1 rounded shadow-sm bg-white font-bold text-blue-600 border' : 'inactive-btn text-xs px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
    document.getElementById('btn-novo').className = fonte === 'novo' ? 'active-btn bg-green-600 text-xs ml-1 px-3 py-1 rounded shadow-sm font-bold text-white border' : 'inactive-btn text-xs ml-1 px-3 py-1 rounded text-slate-500 hover:bg-white hover:shadow-sm transition';
    voltarParaBrasil();
}

function voltarParaBrasil() { estadoNav = { regiao: null, uf: null, cidade: null }; carregarDados(); }
function voltarParaRegiao() { estadoNav.uf = null; estadoNav.cidade = null; carregarDados(); }

function navegarParaNivel(rotulo) {
    if (!estadoNav.regiao) { estadoNav.regiao = rotulo; carregarDados(); } 
    else if (!estadoNav.uf) { estadoNav.uf = rotulo; carregarDados(); } 
    else { 
        estadoNav.cidade = rotulo; 
        renderizarTabelaRegioes(); 
        carregarDados(); 
    }
}

async function carregarDados() {
    atualizarMigalhasPao();
    document.getElementById('total-qtd').innerText = '...';
    
    // Parâmetros mantidos em inglês para não quebrar a comunicação com a API em Python
    const parametros = new URLSearchParams({
        source: fonteAtual,
        region: estadoNav.regiao || '',
        uf: estadoNav.uf || '',
        city: estadoNav.cidade || ''
    });

    try {
        const resposta = await fetch(`/api/drilldown?${parametros}`);
        const dados = await resposta.json();
        
        document.getElementById('total-qtd').innerText = dados.totals.qtd.toLocaleString('pt-BR');
        document.getElementById('total-valor').innerText = formatarMoeda(dados.totals.valor);

        if (!estadoNav.cidade || dadosDetalhamento.length === 0) {
            dadosDetalhamento = dados.breakdown || [];
        }
        
        atualizarInterface(dados);
    } catch (erro) { console.error(erro); }
}

function atualizarInterface(dados) {
    const tituloGrafico = document.getElementById('chart-title');
    const tituloTabela = document.getElementById('table-title');
    const secaoObras = document.getElementById('works-section');

    // 1. Gráfico
    if (estadoNav.uf) {
        tituloGrafico.innerText = "Ranking (Qtd)";
        renderizarGrafico(dadosDetalhamento.slice(0, 15)); 
    } else {
        tituloGrafico.innerText = estadoNav.regiao ? `${estadoNav.regiao}` : "Regiões do Brasil";
        renderizarGrafico(dadosDetalhamento);
    }

    // 2. Tabela Meio
    tituloTabela.innerText = estadoNav.uf ? `Detalhes de ${estadoNav.uf}` : "Distribuição Geográfica";
    renderizarTabelaRegioes();

    // 3. Tabela Obras
    if (estadoNav.uf) {
        secaoObras.classList.remove('hidden');
        document.getElementById('works-subtitle').innerText = estadoNav.cidade 
            ? `Filtrando: ${estadoNav.cidade}` 
            : `Todas as obras: ${estadoNav.uf}`;
        renderizarTabelaObras(dados.works);
    } else {
        secaoObras.classList.add('hidden');
    }
}

function ordenarTabela(chave) {
    if (configOrdenacao.chave === chave) configOrdenacao.ordem = configOrdenacao.ordem === 'desc' ? 'asc' : 'desc';
    else { configOrdenacao.chave = chave; configOrdenacao.ordem = 'desc'; }
    renderizarTabelaRegioes();
}

function renderizarTabelaRegioes() {
    const corpoTabela = document.getElementById('table-body');
    dadosDetalhamento.sort((a, b) => {
        let valorA = a[configOrdenacao.chave];
        let valorB = b[configOrdenacao.chave];
        return configOrdenacao.ordem === 'asc' ? valorA - valorB : valorB - valorA;
    });

    corpoTabela.innerHTML = dadosDetalhamento.map(item => {
        const estaAtivo = estadoNav.cidade === item.label;
        const classeFundo = estaAtivo ? 'bg-blue-100 border-l-4 border-blue-600' : 'hover:bg-slate-50';
        return `
        <tr class="${classeFundo} cursor-pointer transition border-b border-slate-50" onclick="navegarParaNivel('${item.label}')">
            <td class="p-3 font-medium text-slate-700 truncate max-w-[150px]" title="${item.label}">${item.label}</td>
            <td class="p-3 text-right font-bold text-blue-600">${item.qtd}</td>
            <td class="p-3 text-right text-slate-500 font-mono text-xs">${formatarMoeda(item.valor)}</td>
        </tr>`
    }).join('');
}

function renderizarTabelaObras(obras) {
    const corpoTabelaObras = document.getElementById('works-body');
    document.getElementById('works-count').innerText = obras.length > 0 ? `${obras.length.toLocaleString()} obras` : 'Vazio';
    
    if(!obras || obras.length === 0) {
        corpoTabelaObras.innerHTML = '<tr><td colspan="6" class="p-8 text-center text-slate-400">Nenhuma obra encontrada.</td></tr>';
        return;
    }

    corpoTabelaObras.innerHTML = obras.map(obra => {
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

function renderizarGrafico(itens) {
    const contexto = document.getElementById('navChart').getContext('2d');
    if (graficoNav) graficoNav.destroy();
    
    graficoNav = new Chart(contexto, {
        type: 'bar',
        data: {
            labels: itens.map(i => i.label),
            datasets: [{
                label: 'Obras',
                data: itens.map(i => i.qtd),
                backgroundColor: '#3b82f6',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            onClick: (evento, elementos) => {
                if (elementos.length > 0) navegarParaNivel(itens[elementos[0].index].label);
            }
        }
    });
}

function atualizarMigalhasPao() {
    const migalhaRegiao = document.getElementById('crumb-region');
    const migalhaUF = document.getElementById('crumb-uf');
    
    if(estadoNav.regiao) { 
        migalhaRegiao.classList.remove('hidden'); 
        document.getElementById('crumb-region-text').innerText = estadoNav.regiao; 
    } else migalhaRegiao.classList.add('hidden');

    if(estadoNav.uf) { 
        migalhaUF.classList.remove('hidden'); 
        document.getElementById('crumb-uf-text').innerText = estadoNav.uf; 
    } else migalhaUF.classList.add('hidden');
}

function formatarMoeda(valor) {
    if (!valor) return 'R$ 0,00';
    return parseFloat(valor).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}