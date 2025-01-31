import os
import glob
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import pandas as pd
from geopy.geocoders import Nominatim


def get_coordinates(city_name, state_name="Ceará", country_name="Brasil"):
    geolocator = Nominatim(user_agent="geocoding_app")
    try:
        city_name = city_name.strip()
        location = geolocator.geocode(f"{city_name}, {state_name}, {country_name}")
        if location:
            latitude = round(location.latitude, 6)
            longitude = round(location.longitude, 6)
            if (-90 <= latitude <= 90) and (-180 <= longitude <= 180):
                return latitude, longitude
            else:
                print(
                    f"Coordenadas inválidas para {city_name}: {latitude}, {longitude}"
                )
                return None, None
        else:
            print(
                f"Não foi possível encontrar as coordenadas para a cidade: {city_name}"
            )
            return None, None
    except Exception as e:
        print(f"Erro ao buscar coordenadas para {city_name}: {e}")
        return None, None


# Ler a lista de órgãos e termos de pesquisa do arquivo de texto
with open("pesquisacidadeeeducacao.txt", "r", encoding="utf-8") as file:
    linhas = file.read().splitlines()

# Certificar-se de que há um número par de linhas
if len(linhas) % 3 != 0:
    raise ValueError("O arquivo deve conter trios consecutivos de linhas, cada trio representando um órgão, termo e situação.")

# Iterar sobre trios consecutivos de linhas
for i in range(0, len(linhas), 3):
    orgaosup = linhas[i]
    termoorgsup = linhas[i + 1]
    termosituacao = linhas[i + 2]

    # Diretório e o nome do arquivo desejado
    diretorio_destino = f"C:\\Users\\charl\\Downloads\\Arquivos_BD\\{orgaosup}" 
    nome_do_arquivo_csv = f"{orgaosup}.csv"

        # Configurar o WebDriver
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": diretorio_destino,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })

    try:
        driver = webdriver.Chrome(options=chrome_options)

        url = "https://obras.paineis.gov.br/extensions/painel-obras/painel-obras.html"
        driver.get(url)

        time.sleep(5)

        # Localizar e clicar no primeiro filtro
        seletor_do_campo = "fltr-orgao-sup"
        campo_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, seletor_do_campo))
        )
        campo_input.click()

        # Aguardar o campo de pesquisa aparecer
        novo_seletor_do_campo = "Pesquisar na caixa de listagem"
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{novo_seletor_do_campo}']"))
        )

        # Inserir texto da pesquisa
        novo_campo_input.send_keys(termoorgsup)
        novo_campo_input.send_keys(Keys.ENTER)
        time.sleep(5)

        # Confirma a seleção
        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(10)

        # Localizar e clicar no segundo filtro
        seletor_do_campo = "fltr-situacao-atual"
        campo_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, seletor_do_campo))
        )
        campo_input.click()

        # Inserir texto da pesquisa para o segundo filtro
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{novo_seletor_do_campo}']"))
        )
        novo_campo_input.send_keys(termosituacao)
        novo_campo_input.send_keys(Keys.ENTER)
        time.sleep(5)

        # Confirma a seleção
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(10)

        # Identifica todos os arquivos no diretório e os exclui
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*'))
        for arquivo in arquivos_no_diretorio:
            os.remove(arquivo)

        # Seleciona o botão de download da planilha
        seletor_do_link = "a[title='Exportar dados da tabela Detalhes das Obras']"
        link_exportacao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_link))
        )
        link_exportacao.click()

        time.sleep(15)

        # Aguarda o download
        arquivos_no_diretorio = glob.glob(
            os.path.join(diretorio_destino, "*.xlsx.crdownload")
        )
        while arquivos_no_diretorio:
            time.sleep(1)
            arquivos_no_diretorio = glob.glob(
                os.path.join(diretorio_destino, "*.xlsx.crdownload")
            )

        # Identifica o arquivo mais recente
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, "*.xlsx"))
        if arquivos_no_diretorio:
            arquivo_mais_recente = max(arquivos_no_diretorio, key=os.path.getctime)

        df = pd.read_excel(arquivo_mais_recente)
        print("Colunas do arquivo original:", df.columns)

        if "UF" in df.columns and "Município" in df.columns:
            df_ce = df[df["UF"] == "CE"]
            for index, row in df_ce.iterrows():
                municipio = row["Município"]
                cidade, estado = municipio.split("/")
                cidade = cidade.strip()
                estado = estado.strip()
                print(f"Obtendo coordenadas para: {cidade} - {estado}")
                latitude, longitude = get_coordinates(cidade, estado)
                if latitude is not None and longitude is not None:
                    df_ce.at[index, "Latitude"] = latitude
                    df_ce.at[index, "Longitude"] = longitude

            if not df_ce.empty:
                novo_caminho_do_arquivo_csv = os.path.join(
                    diretorio_destino, nome_do_arquivo_csv
                )
                df_ce.to_csv(
                    novo_caminho_do_arquivo_csv,
                    index=False,
                    sep=";",  # Usa ponto e vírgula como separador
                    encoding="utf-8-sig",
                )
                print(
                    f"Arquivo CSV gerado com sucesso: {novo_caminho_do_arquivo_csv}"
                )
            else:
                print(f"Nenhuma linha com UF='CE' encontrada para {orgaosup}.")
        else:
            print("As colunas 'UF' ou 'Município' não foram encontradas no arquivo.")
    except Exception as e:
        print(
            f"Erro na consulta para {orgaosup} - {termoorgsup}: {str(e)}"
        )
    finally:
        driver.quit()
    time.sleep(2)
