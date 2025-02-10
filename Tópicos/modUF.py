import os
import datetime
import pandas as pd

# Configuração do diretório base
diretorio_base = r"D:\\Mestrado\\Orientador\\Código de Web Scraping\\Tópicos\\BD"

# Obtém a data atual
data_atual = datetime.datetime.today()

# Percorre todas as pastas dentro do diretório base
for orgao in os.listdir(diretorio_base):
    caminho_orgao = os.path.join(diretorio_base, orgao)

    if os.path.isdir(caminho_orgao):  # Verifica se é uma pasta
        for arquivo in os.listdir(caminho_orgao):
            caminho_arquivo = os.path.join(caminho_orgao, arquivo)

            if arquivo.endswith(".xlsx"):
                timestamp = os.path.getctime(caminho_arquivo)
                data_download = datetime.datetime.fromtimestamp(timestamp)

                # Verifica se o arquivo foi baixado nos últimos 3 dias
                if (data_atual - data_download).days > 3:
                    continue

                print(f"Processando arquivo: {arquivo}")
                try:
                    # Carregar planilha preservando os tipos de dados originais
                    df = pd.read_excel(caminho_arquivo, dtype=str)  # Lê tudo como string

                    # Verifica se a coluna "UF" existe no DataFrame
                    if "UF" in df.columns:
                        # Filtra apenas as cidades do Ceará (CE)
                        df_ce = df[df["UF"].str.upper() == "CE"].copy()

                        if not df_ce.empty:
                            # Salva o arquivo filtrado sobrescrevendo o original
                            with pd.ExcelWriter(caminho_arquivo, engine='openpyxl', mode='w') as writer:
                                df_ce.to_excel(writer, index=False)
                            print(f"Arquivo atualizado: {arquivo} (Apenas cidades do CE)")
                        else:
                            print(f"Nenhuma cidade do CE encontrada em {arquivo}")
                except Exception as e:
                    print(f"Erro ao processar {arquivo}: {e}")
