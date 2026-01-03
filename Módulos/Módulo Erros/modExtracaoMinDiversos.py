import time
import sys
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import logging
from datetime import datetime # Importar datetime

# --- Configuração do Logger para Rota Diária com nome de arquivo datado ---
# Obtém a data atual no formato YYYY-MM-DD
data_atual = datetime.now().strftime("%Y-%m-%d")
log_filename = f'erros_automacao.{data_atual}.log' # Nome do arquivo já com a data

# Cria um FileHandler normal, não um TimedRotatingFileHandler
# Isso significa que a rotação por tempo não é automática para o nome do arquivo ATIVO.
# Você precisaria gerenciar a limpeza de arquivos antigos manualmente,
# ou adaptar para combinar com TimedRotatingFileHandler de forma mais avançada.
log_handler = logging.FileHandler(log_filename, encoding='utf-8')
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
logger.addHandler(log_handler)
# --- Fim da Configuração do Logger ---

# --- Função para tratamento global de exceções ---
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Ocorreu um erro não tratado:", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception
# --- Fim da Função para tratamento global de exceções ---

# --- Função para verificar a conexão com a internet ---
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

# --- Início do Script Principal ---

if not verificar_conexao_internet():
    logger.error("Sem conexão com a internet. O script será encerrado.")
    print("ERRO: Sem conexão com a internet. Verifique o arquivo de log.")
    sys.exit(1)

try:
    with open(f"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\pesquisaautomatica.txt", "r", encoding="utf-8") as file:
        linhas = file.read().splitlines()
except FileNotFoundError:
    logger.error("O arquivo 'pesquisaautomatica.txt' não foi encontrado.")
    sys.exit(1)

if len(linhas) % 2 != 0:
    error_message = "O arquivo deve conter pares consecutivos de linhas, cada par representando um órgão e um termo de pesquisa."
    logger.error(error_message)
    raise ValueError(error_message)

for i in range(0, len(linhas), 2):
    orgao = linhas[i]
    termo = linhas[i + 1]

    driver = None

    try:
        diretorio_destino = f"C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD\\Site_Legado\\{orgao}"

        chrome_options = Options()
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": diretorio_destino,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safeBrowse.enabled": True,
        })

        driver = webdriver.Chrome(options=chrome_options)

        url = "https://dd-publico.serpro.gov.br/extensions/obras/obras.html"

        try:
            driver.get(url)
        except Exception as e:
            if "net::ERR_INTERNET_DISCONNECTED" in str(e) or \
               "net::ERR_NAME_NOT_RESOLVED" in str(e) or \
               "net::ERR_CONNECTION_REFUSED" in str(e) or \
               ("TimeoutException" in str(e) and "loading" in str(e).lower()):
                logger.error(f"Erro de rede para {orgao} - {termo}: {e}")
                print(f"ERRO DE REDE para {orgao} - {termo}. O navegador não conseguiu acessar a URL. Verifique a conexão.")
                if driver: driver.quit()
                continue
            else:
                raise e

        time.sleep(5)

        orgao_superior = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão Superior']")))
        orgao_superior.click()
        print(f"Filtro 'Órgão Superior' selecionado para {orgao} - {termo}.")
        time.sleep(5)

        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']")))
        time.sleep(5)
        texto_para_escrever = termo
        novo_campo_input.send_keys(texto_para_escrever)
        novo_campo_input.send_keys(Keys.ENTER)
        time.sleep(5)

        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        botao_exportar = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "btn-export-tbl-detalhes-obras"))
        )
        botao_exportar.click()

        print(f"Exportação iniciada para {orgao} - {termo}.")
        time.sleep(10)

    except Exception as e:
        logger.error(f"Erro inesperado na automação para {orgao} - {termo}: {str(e)}")
        print(f"Erro inesperado na automação para {orgao} - {termo}. Verifique o arquivo de log para mais detalhes.")

    finally:
        if driver:
            driver.quit()

    time.sleep(2)