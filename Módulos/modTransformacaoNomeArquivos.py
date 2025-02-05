import os
import datetime

# Caminho principal onde os arquivos foram baixados
diretorio_base = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD"

# Obtém a data atual
data_atual = datetime.datetime.today()

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
                    continue  # Pula para o próximo arquivo
                except ValueError:
                    pass  # O nome não está no formato correto, então será renomeado

                # Define o novo nome baseado apenas na data do download
                novo_nome = f"{data_download.strftime('%Y-%m-%d')}{extensao}"
                caminho_novo = os.path.join(caminho_orgao, novo_nome)

                # Renomeia o arquivo
                os.rename(caminho_antigo, caminho_novo)
                print(f"Arquivo renomeado: {arquivo} -> {novo_nome}")
