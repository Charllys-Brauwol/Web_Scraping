import os
import glob
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from popular_bd import excel_to_database
import pandas as pd

def run_web_scraping(orgao, termo, db_params):
    # Obter o diretório do script
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Atualizar o diretório de destino
    diretorio_destino = os.path.join(script_directory, f"Arquivos_BD\\{orgao}")
    
    nome_do_arquivo = f"{orgao}.xlsx"  # Substitua pelo nome desejado e extensão

    # Verificar se a pasta de destino existe e criar se não existir
    if not os.path.exists(diretorio_destino):
        os.makedirs(diretorio_destino)

    # Configurar o WebDriver
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": diretorio_destino,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })

    driver = webdriver.Chrome(options=chrome_options)

    url = "https://obras.paineis.gov.br/extensions/painel-obras/painel-obras.html"
    driver.get(url)

    time.sleep(5)

    try:
        # Localizar e clicar no primeiro filtro
        seletor_do_campo = "fltr-orgao-sup"
        campo_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, seletor_do_campo))
        )
        campo_input.click()

        time.sleep(5)

        # Aguardar o campo de pesquisa aparecer
        novo_seletor_do_campo = "Pesquisar na caixa de listagem"
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{novo_seletor_do_campo}']"))
        )
        time.sleep(5)

        # Inserir texto da pesquisa
        texto_para_escrever = termo
        novo_campo_input.send_keys(texto_para_escrever)

        # Seleciona os itens
        novo_campo_input.send_keys(Keys.ENTER)

        time.sleep(5)

        # Confirma a seleção
        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(5)

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

        time.sleep(10)

        # Aguarda o download
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx.crdownload'))
        while arquivos_no_diretorio:
            time.sleep(1)
            arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx.crdownload'))

        # Identifica o arquivo mais recente
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx'))
        if arquivos_no_diretorio:
            arquivo_mais_recente = max(arquivos_no_diretorio, key=os.path.getctime)

        # Renomeia o arquivo de acordo com o termo do arquivo txt
        novo_nome_arquivo = f"{orgao}.xlsx"
        novo_caminho_do_arquivo = os.path.join(diretorio_destino, novo_nome_arquivo)
        os.rename(arquivo_mais_recente, novo_caminho_do_arquivo)

        # Chama a função que popula o banco de dados
        excel_to_database(novo_caminho_do_arquivo, orgao, db_params)

    except Exception as e:
        print(f"Erro na consulta para {orgao} - {termo}: {str(e)}")

    finally:
        # Certifique-se de fechar o navegador, mesmo em caso de exceção
        driver.quit()

    # Adicione um pequeno atraso entre as iterações, se necessário
    time.sleep(2)

# Ler a lista de órgãos e termos de pesquisa do arquivo de texto
with open("pesquisaautomatica.txt", "r", encoding="utf-8") as file:
    linhas = file.read().splitlines()

# Configurações de conexão com o banco de dados
db_params = {
    'host': 'aula-youtube.c5o6ysg0ci7d.us-east-2.rds.amazonaws.com',
    'database': 'postgres',
    'user': 'postgres',
    'password': 'cb2907cb',
    'port': '5432',  # Normalmente 5432 para PostgreSQL
}

# Certificar-se de que há um número par de linhas
if len(linhas) % 2 != 0:
    raise ValueError("O arquivo deve conter pares consecutivos de linhas, cada par representando um órgão e um termo de pesquisa.")

# Iterar sobre pares consecutivos de linhas
for i in range(0, len(linhas), 2):
    orgao = linhas[i]
    termo = linhas[i + 1]

    # Chama a função principal em um bloco try-except
    try:
        run_web_scraping(orgao, termo, db_params)
    except Exception as e:
        print(f"Erro geral para {orgao} - {termo}: {str(e)}")
