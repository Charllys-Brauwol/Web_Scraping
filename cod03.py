import requests
from urllib3.exceptions import InsecureRequestWarning

# Desabilitar os avisos de verificação de certificado SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Configurar o diretório e o nome do arquivo desejado
diretorio_destino = "C:\\Users\\charl\\Downloads\\Sec" 
nome_do_arquivo = "sec.xlsx"  # Substitua pelo nome desejado e extensão

# URL para a exportação de dados
url_exportacao = "https://obras.paineis.gov.br/extensions/painel-obras/export-csv"

# Parâmetros para a exportação
params = {
    'orgaoSup': 'SEC',  # Substitua pelo valor correto
}

# Enviar solicitação POST para a exportação de dados
response = requests.post(url_exportacao, data=params, verify=False)

# Verificar se a solicitação foi bem-sucedida (código 200)
if response.status_code == 200:
    # Salvar o conteúdo da resposta no arquivo desejado
    caminho_arquivo = os.path.join(diretorio_destino, nome_do_arquivo)
    with open(caminho_arquivo, 'wb') as f:
        f.write(response.content)
    print(f"Arquivo baixado com sucesso em {caminho_arquivo}")
else:
    print(f"Falha ao baixar o arquivo. Código de status: {response.status_code}")
