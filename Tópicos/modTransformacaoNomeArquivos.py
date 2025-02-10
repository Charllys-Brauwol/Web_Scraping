import os
import datetime
import pandas as pd

# Caminho principal onde os arquivos foram baixados
diretorio_base = r"D:\\Mestrado\\Orientador\\Código de Web Scraping\\Tópicos\\BD"

# Obtém a data atual
data_atual = datetime.datetime.today()

# Lista de colunas a serem excluídas
colunas_excluir = [
    "Código Transação Obra", "Origem", "Nº Instrumento", "Órgão Superior", "Órgão", 
    "Objeto", "Título", "Situação Atual", "Endereço", "Link"
]

# Percorre todas as pastas dentro do diretório base
for orgao in os.listdir(diretorio_base):
    caminho_orgao = os.path.join(diretorio_base, orgao)

    # Verifica se é uma pasta
    if os.path.isdir(caminho_orgao):
        # Percorre os arquivos dentro da pasta
        for arquivo in os.listdir(caminho_orgao):
            caminho_antigo = os.path.join(caminho_orgao, arquivo)

            # Verifica se o arquivo tem a extensão .xlsx
            if arquivo.endswith(".xlsx"):
                nome_base, extensao = os.path.splitext(arquivo)

                # Obtém a data de criação/modificação do arquivo (data do download)
                timestamp = os.path.getctime(caminho_antigo)  # Data de criação
                data_download = datetime.datetime.fromtimestamp(timestamp)

                # Verifica se o arquivo foi baixado nos últimos 3 dias
                if (data_atual - data_download).days > 3:
                    continue  # Se for mais antigo que 3 dias, pula para o próximo arquivo

                # Verifica se o arquivo já está no formato correto "YYYY-MM-DD.xlsx"
                try:
                    datetime.datetime.strptime(nome_base, "%Y-%m-%d")
                    print(f"O arquivo {arquivo} já está no formato correto. Nenhuma alteração feita.")
                except ValueError:
                    # O nome não está no formato correto, então será renomeado
                    novo_nome = f"{data_download.strftime('%Y-%m-%d')}{extensao}"
                    caminho_novo = os.path.join(caminho_orgao, novo_nome)

                    # Renomeia o arquivo .xlsx
                    os.rename(caminho_antigo, caminho_novo)
                    print(f"Arquivo renomeado: {arquivo} -> {novo_nome}")

                    # Atualiza o caminho para o arquivo renomeado
                    caminho_antigo = caminho_novo

                # Converte o arquivo .xlsx para .csv
                try:
                    # Lê o arquivo Excel
                    df = pd.read_excel(caminho_antigo)

                    # Exclui as colunas especificadas, se existirem
                    df.drop(columns=[col for col in colunas_excluir if col in df.columns], inplace=True)

                    # Define o caminho do novo arquivo .csv
                    novo_nome_csv = nome_base + ".csv"
                    caminho_csv = os.path.join(caminho_orgao, novo_nome_csv)

                    # Salva o arquivo em formato .csv
                    df.to_csv(caminho_csv, index=False)
                    print(f"Arquivo convertido para CSV: {caminho_antigo} -> {novo_nome_csv}")

                except Exception as e:
                    print(f"Erro ao converter {arquivo} para CSV: {e}")
