// O evento DOMContentLoaded garante que o script só rode após o HTML estar pronto
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Faz a chamada para a API que você criou no Flask passando o ID global da obra
        const res = await fetch(`/api/obra/${OBRA_ID}`);
        const data = await res.json();

        // Esconde o elemento de "Carregando" inicial
        document.getElementById('loading').classList.add('hidden');
        
        // Se a API retornar que a obra não existe, exibe uma mensagem de erro estilizada
        if (!data.encontrado) {
            document.body.innerHTML = `
                <div class="text-center py-20 text-red-500 text-xl font-bold">
                    <i class="fas fa-exclamation-triangle block text-4xl mb-4"></i>
                    Obra não encontrada no banco de dados.
                </div>`;
            return;
        }

        // Se encontrou, mostra o container principal de conteúdo
        document.getElementById('content').classList.remove('hidden');

        // Função utilitária interna para formatar números no padrão de moeda Brasileira (R$)
        const formatBRL = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor);

        // --- SEÇÃO: INFORMAÇÕES BÁSICAS ---
        document.getElementById('txt-nome').innerText = data.basico.nome;
        document.getElementById('txt-local').innerHTML = `<i class="fas fa-map-marker-alt mr-1 text-red-500"></i> ${data.basico.localizacao}`;
        document.getElementById('txt-executor').innerText = data.basico.executor;
        document.getElementById('txt-financiador').innerText = data.basico.financiador;
        
        // Lógica de Cores para o Badge de Situação (Status)
        let sit = data.cronograma.situacao;
        let bClass = "bg-blue-100 text-blue-700"; // Padrão: Azul
        if(sit.toLowerCase().includes('conclu')) bClass = "bg-emerald-100 text-emerald-700"; // Concluída: Verde
        if(sit.toLowerCase().includes('parali')) bClass = "bg-red-100 text-red-700";     // Paralisada: Vermelho
        
        const badge = document.getElementById('badge-situacao');
        badge.innerText = sit;
        badge.className = `px-4 py-2 rounded-full text-sm font-bold ${bClass}`;

        // --- SEÇÃO: EXECUÇÃO (BARRAS DE PROGRESSO) ---
        // Atualiza o texto e a largura da barra de execução física
        document.getElementById('lbl-fisico').innerText = data.execucao.perc_fisico + "%";
        document.getElementById('bar-fisico').style.width = Math.min(data.execucao.perc_fisico, 100) + "%";
        
        // Atualiza o texto e a largura da barra de execução financeira
        document.getElementById('lbl-finan').innerText = data.execucao.perc_financeiro + "%";
        document.getElementById('bar-finan').style.width = Math.min(data.execucao.perc_financeiro, 100) + "%";

        // Preenche os valores financeiros principais
        document.getElementById('txt-v-previsto').innerText = formatBRL(data.execucao.valor_previsto);
        document.getElementById('txt-v-empenhado').innerText = formatBRL(data.execucao.valor_empenhado);
        document.getElementById('txt-v-desembolso').innerText = formatBRL(data.execucao.valor_desembolsado);

        // --- SEÇÃO: DETALHES TÉCNICOS ---
        document.getElementById('txt-dt-inicio').innerText = data.cronograma.data_inicio;
        document.getElementById('txt-dt-fim').innerText = data.cronograma.data_fim;
        document.getElementById('txt-funcao').innerText = data.impacto.funcao;
        document.getElementById('txt-publico').innerText = data.impacto.publico_beneficiado;
        document.getElementById('txt-modalidade').innerText = data.investimento.modalidade;
        document.getElementById('txt-fornecedor').innerText = data.investimento.contrato_fornecedor;

        // --- SEÇÃO: TABELA DE GASTOS (PAD) ---
        const tbody = document.getElementById('table-gastos');
        let chartLabels = []; // Nomes das categorias para o gráfico
        let chartData = [];   // Valores das categorias para o gráfico
        let grupos = {};      // Objeto auxiliar para somar gastos por natureza (ex: Material, Serviço)

        // Limpa e preenche a tabela de gastos linha por linha
        data.gastos.forEach(g => {
            // Agrupamento para o gráfico de pizza
            if(!grupos[g.natureza]) grupos[g.natureza] = 0;
            grupos[g.natureza] += g.total;

            // Insere a linha na tabela HTML
            tbody.innerHTML += `
                <tr class="hover:bg-slate-50">
                    <td class="p-3 font-medium text-slate-700">${g.item}</td>
                    <td class="p-3"><span class="bg-slate-200 text-slate-600 px-2 py-1 rounded text-xs">${g.natureza}</span></td>
                    <td class="p-3">${g.fornecedor}</td>
                    <td class="p-3 text-right">${g.qtd}</td>
                    <td class="p-3 text-right">${formatBRL(g.preco_un)}</td>
                    <td class="p-3 text-right font-bold text-slate-700">${formatBRL(g.total)}</td>
                </tr>
            `;
        });

        // --- GRÁFICO DE DESPESAS (DOUGHNUT) ---
        // Prepara os dados que foram agrupados no loop anterior
        for(let key in grupos){
            chartLabels.push(key);
            chartData.push(grupos[key]);
        }

        // Renderiza o gráfico de rosca mostrando a distribuição do dinheiro
        new Chart(document.getElementById('chartDespesas').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: chartLabels,
                datasets: [{
                    data: chartData,
                    backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
                    borderWidth: 2, borderColor: '#fff'
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' } // Legenda lateral
                }
            }
        });

    } catch (err) {
        // Captura erros de rede ou de processamento
        console.error("Erro ao renderizar detalhes da obra:", err);
    }
});