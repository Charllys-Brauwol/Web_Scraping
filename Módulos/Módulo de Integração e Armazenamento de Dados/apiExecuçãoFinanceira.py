import requests

#Consulta execução financeira


# ID de exemplo (você pode trocar por outro)

id_projeto = "42210.24-81"

# Endpoint correto da API
url = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira"

# Parâmetros da requisição
params = {
    "idProjetoInvestimento": id_projeto,
    "pagina": 0,
    "tamanhoDaPagina": 10
}

# Cabeçalhos (não é obrigatório, mas pode ser útil)
headers = {
    "accept": "*/*"
}

# Fazendo a requisição GET
response = requests.get(url, params=params, headers=headers)

# Verificando o status da resposta
if response.status_code == 200:
    dados = response.json()
    
    # Exibindo os dados financeiros
    for item in dados.get("content", []):
        print(f"Esfera Orcamentaria: {item.get('nomeEsferaOrcamentaria', 'N/A')}")
        print(f"Tipo Empenho: {item.get('nomeTipoEmpenho', 'N/A')}")
        print(f"Fonte Recurso: {item.get('fonteRecurso', 'N/A')}")
        print(f"Natureza Despesa: {item.get('naturezaDespesa', 'N/A')}")
        print(f"Numero Processo: {item.get('numeroProcesso', 'N/A')}")
        print(f"Descricao Empenho: {item.get('descricaoEmpenho', 'N/A')}")
        print(f"Plano Interno: {item.get('planoInterno', 'N/A')}")
        print(f"Resultado Primario: {item.get('resultadoPrimario', 'N/A')}")
        print(f"Tipo Credito: {item.get('tipoCredito', 'N/A')}")
        print(f"ug Emitente: {item.get('ugEmitente', 'N/A')}")
        print(f"Codigo Amparo Legal: {item.get('codigoAmparoLegal', 'N/A')}")
        print(f"Informacoes Complementares: {item.get('informacoesComplementares', 'N/A')}")
        print(f"Nome Favorecido: {item.get('nomeFavorecido', 'N/A')}")
        print(f"Unidade Orcamentaria: {item.get('unidadeOrcamentaria', 'N/A')}")
        print(f"ug Responsavel: {item.get('ugResponsavel', 'N/A')}")
        print(f"Plano Orcamentario: {item.get('planoOrcamentario', 'N/A')}")
        print(f"Autor Emenda: {item.get('autorEmenda', 'N/A')}")
        print(f"Numero Nota Empenho Gerada: {item.get('numeroNotaEmpenhoGerada', 'N/A')}")
        print(f"Local Entrega: {item.get('localEntrega', 'N/A')}")
        print(f"Valor Empenho: {item.get('valorEmpenho', 'N/A')}")
        print(f"Nr Ptres: {item.get('nrPtres', 'N/A')}")
        print(f"Id Projeto Investimento: {item.get('idProjetoInvestimento', 'N/A')}")
        print("-" * 40)
else:
    print(f"Erro {response.status_code}: {response.text}")
