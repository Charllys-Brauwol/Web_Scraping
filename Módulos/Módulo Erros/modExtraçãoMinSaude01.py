import time
import sys
import requests
import logging
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuração do Logger ---
data_atual = datetime.now().strftime("%Y-%m-%d")
log_filename = f'erros_saude_automacao.{data_atual}.log'

log_handler = logging.FileHandler(log_filename, encoding='utf-8')
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(log_handler)

# --- Verificação de Internet ---
def verificar_conexao_internet(url="http://www.google.com", timeout=5):
    try:
        requests.head(url, timeout=timeout)
        return True
    except Exception:
        return False

# --- Início do Script Principal ---

print("--- Iniciando Script de Automação (SAÚDE/3 LINHAS) ---")

if not verificar_conexao_internet():
    print("ERRO CRÍTICO: Sem conexão com a internet.")
    sys.exit(1)

# Caminho do arquivo de entrada
caminho_arquivo = r"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\pesquisasaude.txt"

try:
    with open(caminho_arquivo, "r", encoding="utf-8") as file:
        linhas = file.read().splitlines()
except FileNotFoundError:
    print(f"ERRO CRÍTICO: Arquivo não encontrado em {caminho_arquivo}")
    sys.exit(1)

# Validação de trios (3 linhas por item)
if len(linhas) == 0 or len(linhas) % 3 != 0:
    print("ERRO: O arquivo deve conter grupos de 3 linhas (Órgão Sup. + Termo Sup. + Órgão).")
    sys.exit(1)

print(f"Carregados {len(linhas)//3} itens para processar.")

for i in range(0, len(linhas), 3):
    orgaosup = linhas[i]
    termoorgsup = linhas[i + 1]
    orgao_filtro_valor = linhas[i + 2]

    driver = None

    try:
        print(f"\n>>> Processando: {orgaosup} -> {orgao_filtro_valor}")
        
        diretorio_destino = f"C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD\\Site_Legado\\{orgaosup}"
        
        if not os.path.exists(diretorio_destino):
            os.makedirs(diretorio_destino)

        # --- CONFIGURAÇÃO DO DRIVER (CORRIGIDA) ---
        chrome_options = Options()
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": diretorio_destino,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safeBrowse.enabled": True,
        })
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Instalação automática do driver correto
        servico = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=servico, options=chrome_options)
        driver.maximize_window()

        # --- NAVEGAÇÃO ---
        url = "https://dd-publico.serpro.gov.br/extensions/obras/obras.html"
        driver.get(url)

        # Tempo de carregamento
        time.sleep(15)

        # --- PASSO 1: ÓRGÃO SUPERIOR ---
        print("1. Selecionando Órgão Superior...")
        orgao_superior = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão Superior']"))
        )
        orgao_superior.click()
        time.sleep(2)

        # Digita o termo do órgão superior
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        novo_campo_input.clear()
        novo_campo_input.send_keys(termoorgsup)
        time.sleep(1)
        novo_campo_input.send_keys(Keys.ENTER)
        time.sleep(3)

        # Confirma
        botao = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        )
        botao.click()
        time.sleep(3)

        # --- PASSO 2: ÓRGÃO ---
        print("2. Selecionando Órgão...")
        orgao_filtro = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão']"))
        )
        orgao_filtro.click()
        time.sleep(2)

        # Digita o termo do órgão
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        novo_campo_input.clear()
        novo_campo_input.send_keys(orgao_filtro_valor)
        time.sleep(1)
        novo_campo_input.send_keys(Keys.ENTER)
        time.sleep(3)

        # Confirma
        botao = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        )
        botao.click()
        time.sleep(5) # Espera tabela atualizar

        # --- EXPORTAÇÃO ---
        print("3. Exportando...")
        botao_exportar = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "btn-export-tbl-detalhes-obras"))
        )
        botao_exportar.click()

        print(f"SUCESSO: Download iniciado para {orgaosup} - {orgao_filtro_valor}.")
        
        # Tempo de download
        time.sleep(25)

    except Exception as e:
        erro_msg = str(e)
        logger.error(f"Erro em {orgaosup}: {erro_msg}")
        print(f"!!! ERRO em {orgaosup}: {erro_msg}")

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    time.sleep(3)

print("\nProcesso finalizado.")