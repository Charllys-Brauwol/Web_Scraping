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
import random

# --- Configuração de Log e Erros ---
data_atual = datetime.now().strftime("%Y-%m-%d")
log_filename = f"erros_filtros_adicionais.{data_atual}.log"

log_handler = logging.FileHandler(log_filename, encoding="utf-8")
log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
logger.addHandler(log_handler)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error(
        "Ocorreu um erro não tratado:", exc_info=(exc_type, exc_value, exc_traceback)
    )
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception

def verificar_conexao_internet(url="http://www.google.com", timeout=5):
    try:
        requests.head(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        return False
    except requests.Timeout:
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao verificar conexão: {e}")
        return False

if not verificar_conexao_internet():
    logger.error("Sem conexão com a internet. O script será encerrado.")
    print("ERRO: Sem conexão com a internet. Verifique o arquivo de log para mais detalhes.")
    sys.exit(1)

# --- Leitura do Arquivo de Estados ---
try:
    file_path = f"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\estados.txt"
    with open(file_path, "r", encoding="utf-8") as file:
        linhas = file.read().splitlines()
except FileNotFoundError:
    logger.error(f"O arquivo 'estados.txt' não foi encontrado em: {file_path}")
    print(f"ERRO: Arquivo 'estados.txt' não encontrado. Verifique o log e o caminho.")
    sys.exit(1)

if len(linhas) == 0 or len(linhas) % 1 != 0:
    error_message = "O arquivo 'estados.txt' está vazio ou formatado incorretamente."
    logger.error(error_message)
    raise ValueError(error_message)

# --- Processamento Principal ---

# DIRETÓRIO BASE PARA SALVAMENTO
DIRETORIO_PAI_DESTINO = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtUFID"
URL_SERPRO = "https://dd-publico.serpro.gov.br/extensions/cipi/cipi.html"

for i in range(0, len(linhas), 1):
    estado = linhas[i].strip()
    
    # CRIA O CAMINHO ESPECÍFICO (EX: .../estadosCodInst/AC)
    diretorio_destino = os.path.join(DIRETORIO_PAI_DESTINO, estado)
    os.makedirs(diretorio_destino, exist_ok=True) # Cria a pasta AC, AL, etc.

    driver = None

    try:
        # --- Configuração do WebDriver ---
        chrome_options = Options()
        chrome_options.add_experimental_option(
            "prefs",
            {
                # USA O DIRETÓRIO DE DESTINO CORRETO PARA A PASTA DO ESTADO
                "download.default_directory": diretorio_destino,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True, 
            },
        )
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(URL_SERPRO)

        # 1. Espera inicial para carregamento completo da página
        time.sleep(15) 
        
        # 2. Clicar em 'UF ( Localização)' para filtrar o Estado
        estado_click = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='UF ( Localização)']"))
        )
        estado_click.click()
        print(f"1/8: Filtro 'UF ( Localização)' selecionado para {estado}.")
        time.sleep(5) 
        
        # 3. Digitar a sigla do estado no campo de busca e confirmar
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        search_input.send_keys(estado)
        time.sleep(5)  
        search_input.send_keys(Keys.ENTER)

        
        confirm_button = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        )
        time.sleep(random.uniform(1, 3)) 
        confirm_button.click()
        print(f"2/8: Estado {estado} filtrado com sucesso.")
        time.sleep(5)

        # 4. Clicar no elemento "Filtros Adicionais"
        filtros_adicionais = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Filtros Adicionais']"))
        )
        filtros_adicionais.click()
        time.sleep(5) 
        print("3/8: Clicado em 'Filtros Adicionais'.")

        # 5. Clicar no elemento 'Nº Instrumento (Transferegov)'
        n_instrumento_click = WebDriverWait(driver, 15).until( 
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Nº Instrumento (Transferegov)']"))
        )
        n_instrumento_click.click()
        time.sleep(5)
        print("4/8: Clicado em 'Nº Instrumento (Transferegov)'.")
        
        # 6. CLICAR NO ÍCONE 'MAIS' (Três pontos) para expandir as opções
        more_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='actions-toolbar-more']"))
        )
        more_button.click()
        print("5/8: Clicado no ícone 'Mais' (três pontos) para expandir.")

        time.sleep(5)
        # 7. Clicar no elemento 'Selecionar todos'
        select_all_click = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//p[text()='Selecionar todos']"))
        )
        select_all_click.click()
        print("6/8: Clicado em 'Selecionar todos'.")
        time.sleep(random.uniform(1, 2)) 

        # *** CLICAR NO ÍCONE DE CONFIRMAÇÃO (Checkmark) ***
        confirm_selection_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        )
        confirm_selection_button.click()
        print("7/8: Clicado no ícone de Confirmação (Checkmark).")
        time.sleep(random.uniform(1, 2)) 
        
        # 8. Clicar no botão 'Fechar' (do modal de seleção)
        close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-dismiss='modal'][style*='background-color: #294B89']"))
        )
        close_button.click()
        print("8/8: Modal de filtros adicionais fechado. Filtro aplicado.")
        
        time.sleep(5) 

        # 9. Clicar no ícone de exportação/download (save_alt)
        botao_exportar = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "btn-export-extrato-intervencao"))
        )
        
        if botao_exportar:
            botao_exportar.click()
            print(f"Exportação iniciada para {estado} com os filtros adicionais aplicados. ✅")
            time.sleep(15) 
        else:
            raise Exception("Botão de exportar (save_alt) não encontrado.")

    except Exception as e:
        logger.error(
            f"Erro inesperado na automação para {estado}: {str(e)}"
        )
        error_detail = str(e).splitlines()[0]
        print(
            f"ERRO: Falha na automação para {estado}. Verifique o log. Detalhe: {error_detail}"
        )

    finally:
        if driver:
            driver.quit()

    time.sleep(random.uniform(5, 8)) 


print("\nProcessamento de todos os estados concluído. 🎉")

os.system("exit")