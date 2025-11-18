import time
import sys
import requests
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

data_atual = datetime.now().strftime("%Y-%m-%d")
log_filename = f"erros_sitenovo.{data_atual}.log"

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
    print(
        "ERRO: Sem conexão com a internet. Verifique o arquivo de log para mais detalhes."
    )
    sys.exit(1)

try:
    with open(
        f"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\estados.txt",
        "r",
        encoding="utf-8",
    ) as file:
        linhas = file.read().splitlines()
except FileNotFoundError:
    logger.error("O arquivo 'estados.txt' não foi encontrado.")
    print(
        "ERRO: Arquivo 'estados.txt' não encontrado. Verifique o log."
    )
    sys.exit(1)


if len(linhas) % 1 != 0:
    error_message = "O arquivo deve conter grupos de 1 linhas (Estado)."
    logger.error(error_message)
    raise ValueError(error_message)

for i in range(0, len(linhas), 1):
    estado = linhas[i]

    diretorio_destino = (
        f"C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD\\ModExtUF\\{estado}"
    )

    driver = None

    try:
        chrome_options = Options()
        chrome_options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": diretorio_destino,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safeBrowse.enabled": True,
            },
        )

        driver = webdriver.Chrome(options=chrome_options)

        url = "https://dd-publico.serpro.gov.br/extensions/cipi/cipi.html"

        try:
            driver.get(url)
        except Exception as e:
            if (
                "net::ERR_INTERNET_DISCONNECTED" in str(e)
                or "net::ERR_NAME_NOT_RESOLVED" in str(e)
                or "net::ERR_CONNECTION_REFUSED" in str(e)
                or ("TimeoutException" in str(e) and "loading" in str(e).lower())
            ):
                logger.error(
                    f"Erro de rede ao acessar URL: {e}"
                )
                print(
                    f"ERRO DE REDE para. O navegador não conseguiu acessar a URL. Verifique a conexão."
                )
                if driver:
                    driver.quit()
                continue
            else:
                raise e

        time.sleep(15)

        estadoClick = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='UF ( Localização)']"))
        )

        estadoClick.click()

        print(f"Filtro 'UF (Localização)' selecionado para {estado}.")

        time.sleep(5)

        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[data-testid='search-input-field']")
            )
        )

        time.sleep(5)

        texto_para_escrever = estado
        novo_campo_input.send_keys(texto_para_escrever)

        novo_campo_input.send_keys(Keys.ENTER)

        time.sleep(5)

        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        botao_exportar = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "btn-export-extrato-intervencao"))
        )

        botao_exportar.click()

        print(
            f"Exportação iniciada para {estado}."
        )
        time.sleep(10)

    except Exception as e:
        logger.error(
            f"Erro inesperado na automação para {estado}: {str(e)}"
        )
        print(
            f"Erro inesperado na automação para {estado}. Verifique o arquivo de log para mais detalhes."
        )

    finally:
        if driver:
            driver.quit()

    time.sleep(2)
