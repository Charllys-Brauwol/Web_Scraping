# ==============================================================================
# --- IMPORTAÇÃO DE BIBLIOTECAS ---
# Trazendo as ferramentas necessárias para o robô funcionar.
# ==============================================================================
import time  # Para pausar o script (esperas fixas)
import sys  # Para comandos do sistema (como fechar o programa ou capturar erros globais)
import requests  # Para testar a internet
import logging  # Para criar o arquivo de "diário" (log)
from datetime import datetime  # Para pegar a data de hoje
from selenium import webdriver  # O controlador do navegador
from selenium.webdriver.common.by import By  # Para achar botões e campos
from selenium.webdriver.support.ui import WebDriverWait  # Para esperas inteligentes
from selenium.webdriver.support import expected_conditions as EC  # Regras de espera
from selenium.webdriver.common.keys import Keys  # Para simular o teclado
from selenium.webdriver.chrome.options import Options  # Opções ocultas do Chrome

# ==============================================================================
# --- CONFIGURAÇÃO DO LOGGER (REGISTRO DE ERROS) ---
# ==============================================================================
data_atual = datetime.now().strftime("%Y-%m-%d") # Pega a data (Ano-Mês-Dia)
log_filename = f"erros_sitenovo.{data_atual}.log" # Cria o nome do arquivo de log

log_handler = logging.FileHandler(log_filename, encoding="utf-8") # Prepara para gravar com acentos
log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")) # Formato da mensagem

logger = logging.getLogger() # Inicia o anotador
logger.setLevel(logging.ERROR) # Grava apenas erros críticos
logger.addHandler(log_handler) # Ativa a gravação no arquivo


# ==============================================================================
# --- FUNÇÃO: CAPTURA GLOBAL DE ERROS (NOVIDADE!) ---
# Essa função é um "para-quedas". Se o script der um erro fatal em QUALQUER lugar
# que não tenha um "try/except", ele cai aqui e é salvo no log antes de fechar.
# ==============================================================================
def handle_exception(exc_type, exc_value, exc_traceback):
    # Se o erro for o usuário apertando "Ctrl+C" para forçar a parada, ele só fecha normalmente
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Se for um erro do código, salva o rastreio completo no arquivo de log
    logger.error(
        "Ocorreu um erro não tratado:", exc_info=(exc_type, exc_value, exc_traceback)
    )
    # Mostra o erro na tela padrão do sistema
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

# Ativa o "para-quedas" substituindo o tratador de erros padrão do Python pelo nosso
sys.excepthook = handle_exception


# ==============================================================================
# --- FUNÇÃO: VERIFICAÇÃO DE INTERNET ---
# Testa se há rede antes de abrir o Chrome.
# ==============================================================================
def verificar_conexao_internet(url="http://www.google.com", timeout=5):
    try: # Tenta pingar o Google
        requests.head(url, timeout=timeout)
        return True # Tem rede
    except requests.ConnectionError: # Erro específico de cabo desconectado/sem Wi-Fi
        return False
    except requests.Timeout: # Erro específico de internet muito lenta
        return False
    except Exception as e: # Qualquer outro erro estranho
        logger.error(f"Erro inesperado ao verificar conexão: {e}")
        return False


# Se não tiver internet...
if not verificar_conexao_internet():
    logger.error("Sem conexão com a internet. O script será encerrado.") # Grava no log
    print(
        "ERRO: Sem conexão com a internet. Verifique o arquivo de log para mais detalhes."
    ) # Avisa na tela
    sys.exit(1) # Fecha o script

# ==============================================================================
# --- LEITURA DO ARQUIVO DE ESTADOS ---
# ==============================================================================
try: # Tenta abrir o arquivo com a lista de estados
    with open(
        f"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\estados.txt",
        "r",
        encoding="utf-8",
    ) as file:
        linhas = file.read().splitlines() # Lê linha por linha e tira os espaços invisíveis
except FileNotFoundError: # Se não achar o arquivo de texto
    logger.error("O arquivo 'estados.txt' não foi encontrado.")
    print(
        "ERRO: Arquivo 'estados.txt' não encontrado. Verifique o log."
    )
    sys.exit(1) # Fecha o script

# VALIDAÇÃO: Verifica se tem grupos de 1 linha. 
# Nota: Matematicamente, qualquer número dividido por 1 tem resto 0. Então isso aqui nunca vai dar erro, mas serve de segurança se a lista estiver vazia.
if len(linhas) % 1 != 0:
    error_message = "O arquivo deve conter grupos de 1 linhas (Estado)."
    logger.error(error_message)
    raise ValueError(error_message)

# ==============================================================================
# --- LOOP PRINCIPAL DE NAVEGAÇÃO ---
# ==============================================================================
# Como é 1 estado por linha, pula de 1 em 1
for i in range(0, len(linhas), 1):
    estado = linhas[i] # Pega o nome do estado atual (Ex: "Ceará")

    # Define a pasta onde o Excel desse estado vai ser salvo
    diretorio_destino = (
        f"C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD\\ModExtUF\\{estado}"
    )

    driver = None # Prepara a variável do navegador

    try: # Inicia o processo web
        chrome_options = Options() # Inicia as configurações do Chrome
        
        # Configura as preferências de download direto para a pasta do estado
        chrome_options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": diretorio_destino,
                "download.prompt_for_download": False, # Não pergunta onde salvar
                "download.directory_upgrade": True,
                "safeBrowse.enabled": True, # Permite o download sem bloqueio de segurança
            },
        )

        # AQUI FALTOU O CHROMEDRIVERMANAGER! O robô vai usar a versão local instalada na máquina.
        driver = webdriver.Chrome(options=chrome_options)

        # URL nova do CIPI
        url = "https://dd-publico.serpro.gov.br/extensions/cipi/cipi.html"

        # Tenta acessar o site com um tratamento de erro super detalhado para falhas de rede (Nova adição muito boa!)
        try:
            driver.get(url)
        except Exception as e:
            # Se for falha de internet desconectada, DNS não resolvido, conexão recusada ou timeout...
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
                if driver: # Se o navegador abriu, fecha ele
                    driver.quit()
                continue # Pula este estado e vai para a próxima linha do arquivo de texto
            else:
                raise e # Se for um erro diferente dos de rede, joga o erro para o "except" lá de baixo

        time.sleep(15) # Espera 15s o painel CIPI carregar (é pesado)

        # --- PASSO 1: FILTRAR O ESTADO ---
        # Espera até 10s o botão do filtro do Estado (UF) aparecer e clica nele
        estadoClick = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='UF ( Localização)']"))
        )
        estadoClick.click()

        print(f"Filtro 'UF (Localização)' selecionado para {estado}.")

        time.sleep(5) # Espera o menu abrir

        # Procura a caixinha de texto para digitar o nome do estado
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[data-testid='search-input-field']")
            )
        )

        # Digita o estado
        texto_para_escrever = estado
        novo_campo_input.send_keys(texto_para_escrever)
        time.sleep(5) # Espera o site reagir à digitação
        novo_campo_input.send_keys(Keys.ENTER) # Dá Enter

        time.sleep(5) # Espera a lista de sugestões filtrar

        # Clica no botão verde de confirmar seleção
        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(15) # Espera longa para o painel de mapas e gráficos processar o estado selecionado

        # --- EXPORTAÇÃO ---
        # Procura o botão de exportar usando a ID nova específica desse painel (btn-export-extrato-intervencao)
        botao_exportar = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "btn-export-extrato-intervencao"))
        )
        time.sleep(3) # Pausa de segurança
        botao_exportar.click() # Clica para baixar
        time.sleep(3) # Pausa de segurança

        print(
            f"Exportação iniciada para {estado}."
        )
        time.sleep(80) # Espera cega de 80s para garantir que o Excel termine de baixar

    except Exception as e: # Se der qualquer outro bug não previsto (como site fora do ar)
        logger.error(
            f"Erro inesperado na automação para {estado}: {str(e)}"
        )
        print(
            f"Erro inesperado na automação para {estado}. Verifique o arquivo de log para mais detalhes."
        )

    finally: # Bloco de limpeza executado independente de dar certo ou errado
        if driver:
            driver.quit() # Fecha o navegador para liberar a memória do PC

    time.sleep(2) # Pausa antes de tentar fazer o próximo Estado da lista