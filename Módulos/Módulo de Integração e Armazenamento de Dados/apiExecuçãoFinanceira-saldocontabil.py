import requests

#Consulta Saldo Contábil Obrasgov


# ID de exemplo (você pode trocar por outro)
ugEmitente = "158133"

# Endpoint correto da API
url = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira/saldo-contabil"

# Parâmetros da requisição
params = {
    "ugEmitente": ugEmitente,
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
        print(f"Ug Emitente: {item.get('ugEmitente', 'N/A')}")
        print(f"Nr Nota de Empenho: {item.get('nrNotaEmpenho', 'N/A')}")
        print(f"Valor Transferido Exercicio Anterior: {item.get('vlTransferidoExercicioAnterior', 'N/A')}")
        print(f"Vl Transferido: {item.get('vlTransferido', 'N/A')}")
        print(f"Vl Restos A Pagar: {item.get('vlRestosAPagar', 'N/A')}")
        print(f"Vl Reinscrito Rp: {item.get('vlReinscritoRp', 'N/A')}")
        print(f"Vl Reforcado: {item.get('vlReforcado', 'N/A')}")
        print(f"Vl Recebido Transferido: {item.get('vlRecebidoTransferido', 'N/A')}")
        print(f"Vl Recebido Exercicio Anterior: {item.get('vlRecebidoExercicioAnterior', 'N/A')}")
        print(f"Vl Pago: {item.get('vlPago', 'N/A')}")
        print(f"Vl Liquidado A Pagar: {item.get('vlLiquidadoAPagar', 'N/A')}")
        print(f"Vl Inscrito Rp: {item.get('vlInscritoRp', 'N/A')}")
        print(f"Vl Incluido: {item.get('vlIncluido', 'N/A')}")
        print(f"Unidade Orcamentaria: {item.get('unidadeOrcamentaria', 'N/A')}")
        print(f"Vl Em Liquidacao: {item.get('vlEmLiquidacao', 'N/A')}")
        print(f"Vl Cancelado Exercicio Anterior: {item.get('vlCanceladoExercicioAnterior', 'N/A')}")
        print(f"Vl Anulado Cancelado: {item.get('vlAnuladoCancelado', 'N/A')}")
        print(f"Vl A Liquidar: {item.get('vlALiquidar', 'N/A')}")
        print("-" * 40)
else:
    print(f"Erro {response.status_code}: {response.text}")
