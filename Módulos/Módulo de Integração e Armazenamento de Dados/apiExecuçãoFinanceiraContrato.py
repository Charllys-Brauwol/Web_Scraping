import requests

#Consulta execução financeira


# ID de exemplo (você pode trocar por outro)

id_projeto = "92689.12-48"

# Endpoint correto da API
url = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira/contrato"

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
        print(f"Id Projeto Investimento: {item.get('idProjetoInvestimento', 'N/A')}")
        print(f"Número do Contrato: {item.get('numeroContrato', 'N/A')}")
        print(f"Vigência Início: {item.get('vigenciaInicio', 'N/A')}")
        print(f"Vigência Fim: {item.get('vigenciaFim', 'N/A')}")
        print(f"Data Assinatura: {item.get('dataAssinatura', 'N/A')}")
        print(f"Data Publicação: {item.get('dataPublicacao', 'N/A')}")
        print(f"Objeto: {item.get('objeto', 'N/A')}")
        print(f"Processo: {item.get('processo', 'N/A')}")
        print(f"Receita Despesa: {item.get('receitaDespesa', 'N/A')}")
        print(f"Código Orgão: {item.get('codigoOrgao', 'N/A')}")
        print(f"Nome Orgão: {item.get('orgaoNome', 'N/A')}")
        print(f"CNPJ Fornecedor: {item.get('fornecedorCnpjCpfIdgener', 'N/A')}")
        print(f"Nome Fornecedor: {item.get('fornecedorNome', 'N/A')}")
        print(f"Categoria: {item.get('categoria', 'N/A')}")
        print(f"Número do Licitante: {item.get('licitacaoNumero', 'N/A')}")
        print(f"Valor Global: {item.get('valorGlobal', 'N/A')}")
        print(f"Valor Acumulado: {item.get('valorAcumulado', 'N/A')}")
        print(f"Código do Contrato: {item.get('codigoContrato', 'N/A')}")
        print(f"Fora de Vigência: {item.get('foraVigencia', 'N/A')}")
        print(f"nrCtrlePncpCompra: {item.get('nrCtrlePncpCompra', 'N/A')}")
        print("-" * 40)
else:
    print(f"Erro {response.status_code}: {response.text}")
