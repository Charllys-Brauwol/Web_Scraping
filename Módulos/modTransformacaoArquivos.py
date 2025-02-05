import os
import datetime
import pandas as pd
from geopy.geocoders import Nominatim

# Configuração do diretório base
diretorio_base = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD"

# Obtém a data atual
data_atual = datetime.datetime.today()

# Inicializa o geocodificador
geolocator = Nominatim(user_agent="geo_correction")

# Função para validar a latitude/longitude
def validar_coordenada(valor):
    try:
        valor = float(str(valor).replace(",", "."))  # Converte para float e corrige vírgula para ponto
        return -90 <= valor <= 90  # Latitude varia entre -90 e 90
    except ValueError:
        return False

# Função para obter coordenadas pelo nome do município
def obter_coordenadas(municipio_estado):
    try:
        localizacao = geolocator.geocode(municipio_estado)
        if localizacao:
            return round(localizacao.latitude, 6), round(localizacao.longitude, 6)  # Formato correto com 6 casas decimais
    except Exception as e:
        print(f"Erro ao buscar coordenadas de {municipio_estado}: {e}")
    return None, None

# Função para extrair o ano de uma data
def extrair_ano(data):
    try:
        if isinstance(data, str):
            data = pd.to_datetime(data, errors="coerce")  # Converte para formato de data
        if pd.notna(data):  # Se a conversão foi bem-sucedida
            return str(data.year)  # Retorna o ano como string
    except Exception:
        pass
    return "-"

# Percorre todas as pastas dentro do diretório base
for orgao in os.listdir(diretorio_base):
    caminho_orgao = os.path.join(diretorio_base, orgao)

    if os.path.isdir(caminho_orgao):  # Verifica se é uma pasta
        for arquivo in os.listdir(caminho_orgao):
            caminho_arquivo = os.path.join(caminho_orgao, arquivo)

            if arquivo.endswith(".xlsx"):
                timestamp = os.path.getctime(caminho_arquivo)
                data_download = datetime.datetime.fromtimestamp(timestamp)

                # Verifica se o arquivo foi baixado nos últimos 2 dias
                if (data_atual - data_download).days > 2:
                    continue

                print(f"Lendo arquivo: {arquivo}")

                try:
                    # Carregar planilha preservando os tipos de dados originais
                    df = pd.read_excel(caminho_arquivo, dtype=str)  # Lê tudo como string para evitar formatação incorreta

                    alterado = False  # Variável para verificar se houve mudanças

                    # Verifica e corrige Latitude/Longitude
                    if "Latitude" in df.columns and "Longitude" in df.columns and "Município" in df.columns:
                        for i, row in df.iterrows():
                            latitude = row["Latitude"]
                            longitude = row["Longitude"]

                            if not (validar_coordenada(latitude) and validar_coordenada(longitude)):
                                municipio_estado = row["Município"]

                                if "/" in municipio_estado:
                                    lat, lon = obter_coordenadas(municipio_estado)
                                    if lat and lon:
                                        df.at[i, "Latitude"] = str(lat).replace(",", ".")
                                        df.at[i, "Longitude"] = str(lon).replace(",", ".")
                                        print(f"Corrigido: {municipio_estado} -> ({lat}, {lon})")
                                        alterado = True
                        
                    # Substituir campos vazios por "-"
                    df.fillna("-", inplace=True)  # Substitui valores NaN por "-"
                    df.replace("", "-", inplace=True)  # Substitui células vazias por "-"

                    # Corrigir "Ano Início Obra" e "Ano Fim Obra" usando as colunas de Data
                    if "Ano Início Obra" in df.columns and "Data Início" in df.columns:
                        for i, row in df.iterrows():
                            if row["Ano Início Obra"] == "-":
                                ano_inicio = extrair_ano(row["Data Início"])
                                if ano_inicio != "-":
                                    df.at[i, "Ano Início Obra"] = ano_inicio
                                    alterado = True

                    if "Ano Fim Obra" in df.columns and "Data Fim" in df.columns:
                        for i, row in df.iterrows():
                            if row["Ano Fim Obra"] == "-":
                                ano_fim = extrair_ano(row["Data Fim"])
                                if ano_fim != "-":
                                    df.at[i, "Ano Fim Obra"] = ano_fim
                                    alterado = True

                    # Salvar apenas se houve alterações
                    if alterado:
                        with pd.ExcelWriter(caminho_arquivo, engine='openpyxl', mode='w') as writer:
                            df.to_excel(writer, index=False)
                        print(f"Arquivo atualizado: {arquivo}")

                except Exception as e:
                    print(f"Erro ao processar {arquivo}: {e}")
