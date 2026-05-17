# ==============================================================================
# --- IMPORTAÇÕES ---
# Ferramentas necessárias para rodar a automação e controlar o navegador.
# ==============================================================================
import time  # Para pausar o script (esperas fixas)
import sys  # Para comandos do sistema (como fechar o programa)
import requests  # Para testar a internet
import logging  # Para criar o arquivo de "diário" de erros (log)
import os  # Para criar as pastas no Windows
from datetime import datetime  # Para pegar a data atual
from selenium import webdriver  # Controlador do navegador Chrome
from selenium.webdriver.common.by import By  # Para localizar elementos no site
from selenium.webdriver.support.ui import WebDriverWait  # Para esperas inteligentes
from selenium.webdriver.support import expected_conditions as EC  # Regras de espera
from selenium.webdriver.common.keys import Keys  # Para simular teclas (ENTER)
from selenium.webdriver.chrome.options import Options  # Configurações do Chrome
import random # NOVIDADE: Para gerar tempos de espera aleatórios (humanização)

# ==============================================================================
# --- CONFIGURAÇÃO DE LOG E ERROS ---
# ==============================================================================
data_atual = datetime.now().strftime("%Y-%m-%d") # Extrai a data (Ano-Mês-Dia)
log_filename = f"erros_filtros_adicionais.{data_atual}.log" # Nomeia o arquivo

log_handler = logging.FileHandler(log_filename, encoding="utf-8") # Prepara para gravar com acentos
log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")) # Formata a mensagem

logger = logging.getLogger() # Inicia o anotador
logger.setLevel(logging.ERROR) # Só anota erros
logger.addHandler(log_handler) # Liga o anotador ao arquivo

# Função "para-quedas" para capturar erros fatais que não estão nos blocos "try"
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt): # Se você apertar Ctrl+C
        sys.__excepthook__(exc_type, exc_value, exc_traceback) # Fecha normal
        return
    logger.error( # Se for erro no código, salva no Log
        "Ocorreu um erro não tratado:", exc_info=(exc_type, exc_value, exc_traceback)
    )
    sys.__excepthook__(exc_type, exc_value, exc_traceback) # E mostra na tela

sys.excepthook = handle_exception # Ativa a função acima

# ==============================================================================
# --- VERIFICAÇÃO DE INTERNET ---
# ==============================================================================
def verificar_conexao_internet(url="http://www.google.com", timeout=5):
    try: # Tenta pingar o Google
        requests.head(url, timeout=timeout)
        return True # Se responder, OK
    except requests.ConnectionError: # Se não tiver cabo/wifi
        return False
    except requests.Timeout: # Se demorar mais de 5s
        return False
    except Exception as e: # Qualquer outra falha de rede
        logger.error(f"Erro inesperado ao verificar conexão: {e}")
        return False

# Checa a rede antes de iniciar o robô
if not verificar_conexao_internet():
    logger.error("Sem conexão com a internet. O script será encerrado.")
    print("ERRO: Sem conexão com a internet. Verifique o arquivo de log para mais detalhes.")
    sys.exit(1) # Fecha tudo

# ==============================================================================
# --- LEITURA DO ARQUIVO DE ESTADOS ---
# ==============================================================================
try:
    file_path = f"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\estados.txt" # Caminho do TXT
    with open(file_path, "r", encoding="utf-8") as file: # Abre o arquivo
        linhas = file.read().splitlines() # Lê as linhas e remove o espaço invisível
except FileNotFoundError: # Se não achar o arquivo
    logger.error(f"O arquivo 'estados.txt' não foi encontrado em: {file_path}")
    print(f"ERRO: Arquivo 'estados.txt' não encontrado. Verifique o log e o caminho.")
    sys.exit(1) # Fecha tudo

# Valida se o arquivo não está vazio. (A divisão por 1 sempre dá certo, mas o len(linhas) == 0 protege)
if len(linhas) == 0 or len(linhas) % 1 != 0:
    error_message = "O arquivo 'estados.txt' está vazio ou formatado incorretamente."
    logger.error(error_message)
    raise ValueError(error_message)

# ==============================================================================
# --- PROCESSAMENTO PRINCIPAL ---
# ==============================================================================

# DIRETÓRIO BASE PARA SALVAMENTO (Uma pasta "Pai" onde as outras vão nascer)
DIRETORIO_PAI_DESTINO = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtUFID"
URL_SERPRO = "https://dd-publico.serpro.gov.br/extensions/cipi/cipi.html" # Link do site

# Loop de 1 em 1 linha (1 estado por linha)
for i in range(0, len(linhas), 1):
    estado = linhas[i].strip() # Pega o estado e o .strip() garante que não há espaços extras no começo/fim
    
    # CRIA O CAMINHO ESPECÍFICO (Junta a pasta Pai com a sigla do estado. Ex: ...\ModExtUFID\CE)
    diretorio_destino = os.path.join(DIRETORIO_PAI_DESTINO, estado)
    os.makedirs(diretorio_destino, exist_ok=True) # Cria a pasta. O 'exist_ok=True' impede que dê erro se a pasta já existir!

    driver = None # Reseta o navegador

    try:
        # --- Configuração do WebDriver ---
        chrome_options = Options()
        chrome_options.add_experimental_option(
            "prefs",
            {
                # Diz pro Chrome baixar o arquivo na pasta do estado atual
                "download.default_directory": diretorio_destino,
                "download.prompt_for_download": False, # Baixa direto
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,  # Libera antivírus para não travar o download
            },
        )
        # Inicia o Chrome (Atenção: usando a versão local do seu PC. Pode quebrar se o Chrome atualizar)
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(URL_SERPRO) # Entra no site

        # 1. Espera inicial bruta para carregamento completo da página e gráficos (15s)
        time.sleep(15) 
        
        # 2. Clicar em 'UF ( Localização)' para abrir a lista de Estados
        estado_click = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='UF ( Localização)']"))
        )
        estado_click.click()
        print(f"1/8: Filtro 'UF ( Localização)' selecionado para {estado}.")
        time.sleep(5) 
        
        # 3. Localiza a caixa de texto, digita a sigla do estado e confirma
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        search_input.send_keys(estado) # Digita a sigla
        time.sleep(5)  
        search_input.send_keys(Keys.ENTER) # Filtra

        # Acha o botão de Confirmar
        confirm_button = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        )
        # NOVIDADE: Espera um tempo aleatório entre 1 e 3 segundos antes de clicar (imita um humano)
        time.sleep(random.uniform(1, 3)) 
        confirm_button.click()
        print(f"2/8: Estado {estado} filtrado com sucesso.")
        time.sleep(5)

        # 4. Clicar no elemento superior "Filtros Adicionais"
        filtros_adicionais = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Filtros Adicionais']"))
        )
        filtros_adicionais.click()
        time.sleep(5) 
        print("3/8: Clicado em 'Filtros Adicionais'.")

        # 5. Dentro do novo menu, clicar em 'Nº Instrumento (Transferegov)'
        n_instrumento_click = WebDriverWait(driver, 15).until( 
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Nº Instrumento (Transferegov)']"))
        )
        n_instrumento_click.click()
        time.sleep(5)
        print("4/8: Clicado em 'Nº Instrumento (Transferegov)'.")
        
        # 6. CLICAR NO ÍCONE 'MAIS' (Três pontos) para abrir um submenu de ações
        more_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='actions-toolbar-more']"))
        )
        more_button.click()
        print("5/8: Clicado no ícone 'Mais' (três pontos) para expandir.")

        time.sleep(5)
        
        # 7. Clicar no botão 'Selecionar todos' para marcar todos os instrumentos
        select_all_click = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//p[text()='Selecionar todos']"))
        )
        select_all_click.click()
        print("6/8: Clicado em 'Selecionar todos'.")
        time.sleep(random.uniform(1, 2)) # Espera aleatória humanizada

        # *** CLICAR NO ÍCONE DE CONFIRMAÇÃO (Checkmark) verde do submenu ***
        confirm_selection_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        )
        confirm_selection_button.click()
        print("7/8: Clicado no ícone de Confirmação (Checkmark).")
        time.sleep(random.uniform(1, 2)) 
        
        # 8. Clicar no botão azul de 'Fechar' a janela modal que abriu na tela
        # Ele procura um botão de fechar que tenha uma cor azul específica (#294B89)
        close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-dismiss='modal'][style*='background-color: #294B89']"))
        )
        close_button.click()
        print("8/8: Modal de filtros adicionais fechado. Filtro aplicado.")
        
        time.sleep(5) # Espera a tabela do fundo recalcular tudo

        # 9. Clicar no botão principal de Exportar da página
        botao_exportar = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "btn-export-extrato-intervencao"))
        )
        
        # O Selenium já garante que o botão existe (no step acima), mas esse 'if' é uma checagem dupla
        if botao_exportar:
            botao_exportar.click()
            print(f"Exportação iniciada para {estado} com os filtros adicionais aplicados. ✅")
            time.sleep(25) # Espera o Excel terminar de baixar
        else:
            raise Exception("Botão de exportar (save_alt) não encontrado.") # Nunca vai cair aqui, mas é bom ter.

    except Exception as e: # Se der qualquer erro no longo caminho acima
        logger.error(
            f"Erro inesperado na automação para {estado}: {str(e)}"
        )
        error_detail = str(e).splitlines()[0] # Pega só a primeira linha do erro gigantesco para não poluir a tela
        print(
            f"ERRO: Falha na automação para {estado}. Verifique o log. Detalhe: {error_detail}"
        )

    finally: # Código de limpeza
        if driver:
            driver.quit() # Fecha o navegador ao final do Estado (tenha dado sucesso ou erro)

    # Pausa entre 5 e 8 segundos antes de abrir o navegador de novo para o próximo Estado
    time.sleep(random.uniform(5, 8)) 

print("\nProcessamento de todos os estados concluído. 🎉")

# Fecha o terminal do Windows onde o código estava rodando
os.system("exit")