import requests

idUnico = "27750.12-02"

url = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-fisica/arquivos-da-intervencao"

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
    print(f"Observações: {item.get('observacoes', 'N/A')}")

    arquivos = item.get('listaArquivos', [])
    if arquivos:
        print("Arquivos:")
        for arq in arquivos:
            print(f"  - Nome: {arq.get('name', 'Sem nome')}")
            print(f"    Tipo: {arq.get('type', 'Desconhecido')}")
            print(f"    Tamanho (bytes): {len(arq.get('byteArray', ''))}")
    else:
        print("Arquivos: Nenhum arquivo encontrado.")
    
    print("-" * 40)

else:
    print(f"Erro {response.status_code}: {response.text}")
