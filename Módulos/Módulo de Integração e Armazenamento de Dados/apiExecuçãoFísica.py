import requests

idUnico = "27750.12-02"

url = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-fisica"

params = {
    "idUnico": idUnico,
    "pagina": 0,
    "tamanhoDaPagina": 10
}

headers = {
    "accept": "*/*"
}

response = requests.get(url, params=params, headers=headers)


if response.status_code == 200:
    dados = response.json()
    
    for item in dados.get("content", []):
        print(f"Id Unico: {item.get('idUnico', 'N/A')}")
        print(f"Percentual: {item.get('percentual', 'N/A')}")
        print(f"Data Situaço: {item.get('dataSituacao', 'N/A')}")
        print(f"Situação: {item.get('situacao', 'N/A')}")
        print(f"Observaçes: {item.get('observacoes', 'N/A')}")
        print(f"Em Operação: {item.get('emOperacao', 'N/A')}")
        print(f"Justificativa Em Operação: {item.get('justificativaEmOperacao', 'N/A')}")
        print(f"Cancelamentos Paralisações: {item.get('cancelamentosParalisacoes', 'N/A')}")
        print(f"Documentos: {item.get('documentos', 'N/A')}")
        print("-" * 40)
else:
    print(f"Erro {response.status_code}: {response.text}")
