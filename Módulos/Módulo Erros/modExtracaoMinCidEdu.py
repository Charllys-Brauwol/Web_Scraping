import time
import sys
import requests # Necessário para verificar a conexão com a internet
import logging # Necessário para o sistema de log
from datetime import datetime # Necessário para gerar nomes de arquivo com data
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# --- Configuração do Logger para Geração de Arquivos Diários ---
# Obtém a data atual no formato YYYY-MM-DD
data_atual = datetime.now().strftime("%Y-%m-%d")
# Nome do arquivo de log já com a data
log_filename = f'erros_cidades_educacao.{data_atual}.log'

# Cria um FileHandler simples.
# IMPORTANTE: Este handler não faz a rotação automática nem a limpeza de arquivos antigos.
# Ele sempre cria um novo arquivo por dia (se o script for executado pela primeira vez no dia).
log_handler = logging.FileHandler(log_filename, encoding='utf-8')
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Obtém o logger raiz e adiciona o manipulador
logger = logging.getLogger()
logger.setLevel(logging.ERROR) # Definir o nível mínimo para ERROR
logger.addHandler(log_handler)
# --- Fim da Configuração do Logger ---

# --- Função para tratamento global de exceções ---
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Não registrar KeyboardInterrupt (Ctrl+C)
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Registrar o erro não tratado
    logger.error("Ocorreu um erro não tratado:", exc_info=(exc_type, exc_value, exc_traceback))
    # Chamar o manipulador de exceções padrão do Python para que o erro ainda seja exibido no console
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

# Atribui nossa função ao gancho de exceções do sistema
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

# Verificar conexão antes de iniciar a automação
if not verificar_conexao_internet():
    logger.error("Sem conexão com a internet. O script será encerrado.")
    print("ERRO: Sem conexão com a internet. Verifique o arquivo de log para mais detalhes.")
    sys.exit(1) # Encerra o script com código de erro

# Ler a lista de órgãos e termos de pesquisa do arquivo de texto
try:
    with open("pesquisacidadeeeducacao.txt", "r", encoding="utf-8") as file:
        linhas = file.read().splitlines()
except FileNotFoundError:
    logger.error("O arquivo 'pesquisacidadeeeducacao.txt' não foi encontrado.")
    print("ERRO: Arquivo 'pesquisacidadeeeducacao.txt' não encontrado. Verifique o log.")
    sys.exit(1) # Sai do script se o arquivo não for encontrado

# Certificar-se de que há um número par de linhas
if len(linhas) % 3 != 0:
    error_message = (
        "O arquivo deve conter grupos de 3 linhas (Órgão Superior, Termo Órgão Superior, Termo Situação Atual)."
    )
    logger.error(error_message)
    raise ValueError(error_message) # Ainda eleva o erro para parar a execução

# Iterar sobre grupos de 3 linhas
for i in range(0, len(linhas), 3):
    orgaosup = linhas[i]
    termoorgsup = linhas[i + 1]
    termosituacao = linhas[i + 2]

    diretorio_destino = f"C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD\\{orgaosup}"
    # nome_do_arquivo = f"{orgaosup}.xlsx" # Esta variável não está sendo usada, pode ser removida se não for necessária

    driver = None # Inicializa driver como None para garantir que sempre estará definido

    try:
        # Configurar o WebDriver
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

        url = "https://dd-publico.serpro.gov.br/extensions/obras/obras.html"
        
        # Tentar carregar a URL e capturar erros de rede do Selenium
        try:
            driver.get(url)
        except Exception as e:
            # Captura a exceção específica que pode indicar problema de rede
            if "net::ERR_INTERNET_DISCONNECTED" in str(e) or \
               "net::ERR_NAME_NOT_RESOLVED" in str(e) or \
               "net::ERR_CONNECTION_REFUSED" in str(e) or \
               ("TimeoutException" in str(e) and "loading" in str(e).lower()):
                logger.error(f"Erro de rede ao acessar URL para {orgaosup} - {termoorgsup} - {termosituacao}: {e}")
                print(f"ERRO DE REDE para {orgaosup} - {termoorgsup}. O navegador não conseguiu acessar a URL. Verifique a conexão.")
                if driver: driver.quit() # Garante que o driver seja fechado antes de continuar
                continue # Pula para a próxima iteração se for erro de rede ao carregar a página
            else:
                raise e # Re-eleva se for outro tipo de erro para ser tratado pelo except mais abaixo

        time.sleep(5) # Atraso inicial após carregar a página

        # Aguarda e localiza o elemento "Órgão Superior" pelo texto exato
        orgao_superior = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão Superior']"))
        )

        # Clica no elemento "Órgão Superior"
        orgao_superior.click()

        print(f"Filtro 'Órgão Superior' selecionado para {orgaosup}.")

        time.sleep(5)

        # Aguardar o campo de pesquisa aparecer usando data-testid
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[data-testid='search-input-field']")
            )
        )

        time.sleep(5)  # Pequeno atraso para garantir estabilidade

        # Inserir texto da pesquisa
        texto_para_escrever = termoorgsup
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

        # Aguarda e localiza o elemento "Situação Atual" pelo texto exato
        situacao_atual = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Situação Atual']"))
        )

        # Clica no elemento "Situação Atual"
        situacao_atual.click()

        print(f"Filtro 'Situação Atual' selecionado para {orgaosup} - {termosituacao}.")
        time.sleep(2)

        # Aguardar o campo de pesquisa aparecer usando data-testid
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[data-testid='search-input-field']")
            )
        )

        # Inserir texto da pesquisa
        texto_para_escrever = termosituacao
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

        # Aguarda até que o botão de exportação esteja visível e clicável
        botao_exportar = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "btn-export-tbl-detalhes-obras"))
        )

        # Clica no botão de exportação
        botao_exportar.click()

        print(f"Exportação iniciada para {orgaosup} - {termoorgsup} - {termosituacao}.")
        time.sleep(10)

    except Exception as e:
        # Registrar o erro específico da automação Selenium
        logger.error(f"Erro inesperado na automação para {orgaosup} - {termoorgsup} - {termosituacao}: {str(e)}")
        print(f"Erro inesperado na automação para {orgaosup} - {termoorgsup} - {termosituacao}. Verifique o arquivo de log para mais detalhes.")

    finally:
        # Certifique-se de fechar o navegador, mesmo em caso de exceção
        if driver: # Verifica se o driver foi inicializado antes de tentar fechá-lo
            driver.quit()

    # Adicione um pequeno atraso entre as iterações, se necessário
    time.sleep(2)