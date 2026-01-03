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
from webdriver_manager.chrome import ChromeDriverManager # A SOLUÇÃO MÁGICA

# --- Configuração do Logger ---
data_atual = datetime.now().strftime("%Y-%m-%d")
log_filename = f'erros_automacao.{data_atual}.log'

log_handler = logging.FileHandler(log_filename, encoding='utf-8')
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
# Limpa handlers anteriores para evitar duplicação
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

print("--- Iniciando Script de Automação ---")

if not verificar_conexao_internet():
    print("ERRO CRÍTICO: Sem conexão com a internet.")
    sys.exit(1)

# Caminho do arquivo de entrada (MANTIDO O SEU CAMINHO ORIGINAL)
caminho_arquivo = r"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\pesquisaautomatica.txt"

try:
    with open(caminho_arquivo, "r", encoding="utf-8") as file:
        linhas = file.read().splitlines()
except FileNotFoundError:
    print(f"ERRO CRÍTICO: Arquivo não encontrado em {caminho_arquivo}")
    sys.exit(1)

if len(linhas) == 0 or len(linhas) % 2 != 0:
    print("ERRO: O arquivo deve conter pares de linhas (Órgão + Termo).")
    sys.exit(1)

print(f"Carregados {len(linhas)//2} itens para processar.")

for i in range(0, len(linhas), 2):
    orgao = linhas[i]
    termo = linhas[i + 1]

    driver = None

    try:
        print(f"\n>>> Processando: {orgao} -> {termo}")
        
        diretorio_destino = f"C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD\\Site_Legado\\{orgao}"
        
        if not os.path.exists(diretorio_destino):
            os.makedirs(diretorio_destino)

        # --- CONFIGURAÇÃO DO DRIVER (A CORREÇÃO) ---
        chrome_options = Options()
        # Ignora erros de SSL (Crucial para Serpro/Gov)
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        # Argumentos para estabilidade
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Configurações de download
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": diretorio_destino,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safeBrowse.enabled": True,
        })

        # Remove barra de automação
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # INSTALA E INICIA O DRIVER CORRETO AUTOMATICAMENTE
        servico = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=servico, options=chrome_options)
        driver.maximize_window()

        # --- NAVEGAÇÃO ---
        url = "https://dd-publico.serpro.gov.br/extensions/obras/obras.html"
        driver.get(url)

        # Espera carregamento inicial
        time.sleep(15)

        # 1. Clica no Órgão Superior
        print("Tentando clicar em Órgão Superior...")
        orgao_superior = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão Superior']"))
        )
        orgao_superior.click()
        time.sleep(2)

        # 2. Digita o termo
        print(f"Digitando termo: {termo}")
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        novo_campo_input.clear()
        novo_campo_input.send_keys(termo)
        time.sleep(1)
        novo_campo_input.send_keys(Keys.ENTER)
        time.sleep(3)

        # 3. Confirma
        print("Confirmando seleção...")
        botao = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        )
        botao.click()
        
        # Espera a tabela atualizar
        time.sleep(5)

        # 4. Exporta
        print("Clicando em exportar...")
        botao_exportar = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "btn-export-tbl-detalhes-obras"))
        )
        botao_exportar.click()

        print(f"SUCESSO: Download iniciado para {orgao}.")
        
        # Tempo para o download terminar
        time.sleep(20)

    except Exception as e:
        erro_msg = str(e)
        # Se for o erro de versão, ele vai aparecer aqui agora
        logger.error(f"Erro em {orgao}: {erro_msg}")
        print(f"!!! ERRO em {orgao}: {erro_msg}")

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    # Pausa entre iterações
    time.sleep(3)

print("\nProcesso finalizado.")