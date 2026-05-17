# --- IMPORTAÇÃO DE BIBLIOTECAS ---
import time  # Para pausas fixas (sleep)
import sys  # Para comandos do sistema (como encerrar o script)
import requests  # Para fazer requisições HTTP (testar internet)
import logging  # Para criar e gerenciar arquivos de log de erros
import os  # Para manipular pastas e caminhos de arquivos
from datetime import datetime  # Para pegar a data e hora atual
from selenium import webdriver  # O motor principal do navegador
from selenium.webdriver.common.by import By  # Para localizar elementos (ID, XPATH, CSS)
from selenium.webdriver.support.ui import WebDriverWait  # Para esperas inteligentes
from selenium.webdriver.support import expected_conditions as EC  # Condições de espera (ex: clicar)
from selenium.webdriver.common.keys import Keys  # Para simular teclas como ENTER e TAB
from selenium.webdriver.chrome.options import Options  # Para configurar o comportamento do Chrome
from selenium.webdriver.chrome.service import Service  # Para configurar o serviço do driver
from webdriver_manager.chrome import ChromeDriverManager # Baixa o driver correto automaticamente

# --- BLOCO DE CONFIGURAÇÃO DO LOGGER ---
# Este bloco define como e onde os erros serão salvos para consulta posterior
data_atual = datetime.now().strftime("%Y-%m-%d") # Pega a data atual formatada
log_filename = f'erros_automacao.{data_atual}.log' # Define o nome do arquivo de log com a data

log_handler = logging.FileHandler(log_filename, encoding='utf-8') # Cria o manipulador do arquivo com UTF-8
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')) # Define o formato da linha de log

logger = logging.getLogger() # Instancia o objeto de log
logger.setLevel(logging.ERROR) # Define que apenas erros (e não avisos) serão registrados

if logger.hasHandlers(): # Verifica se já existem configuradores ativos
    logger.handlers.clear() # Limpa para evitar que o erro seja escrito duas vezes
logger.addHandler(log_handler) # Adiciona o configurador ao logger principal

# --- FUNÇÃO: VERIFICAR CONEXÃO DE INTERNET ---
# Tenta acessar o Google para saber se o computador está online antes de abrir o navegador
def verificar_conexao_internet(url="http://www.google.com", timeout=5):
    try: # Tenta executar o bloco abaixo
        requests.head(url, timeout=timeout) # Tenta "bater" no site do Google
        return True # Se conseguir, retorna Verdadeiro
    except Exception: # Se der erro (timeout ou sem rede)
        return False # Retorna Falso

# --- INÍCIO DO FLUXO PRINCIPAL ---

print("--- Iniciando Script de Automação ---") # Mensagem no console

if not verificar_conexao_internet(): # Chama a função de internet
    print("ERRO CRÍTICO: Sem conexão com a internet.") # Avisa o usuário
    sys.exit(1) # Fecha o script com código de erro 1

# Caminho onde está o arquivo com a lista de órgãos e termos
caminho_arquivo = r"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\pesquisaautomatica.txt"

# --- BLOCO: LEITURA DO ARQUIVO DE ENTRADA ---
try: # Tenta ler o arquivo TXT
    with open(caminho_arquivo, "r", encoding="utf-8") as file: # Abre para leitura
        linhas = file.read().splitlines() # Lê todas as linhas e remove o "quebra de linha" (\n)
except FileNotFoundError: # Caso o arquivo não exista no caminho especificado
    print(f"ERRO CRÍTICO: Arquivo não encontrado em {caminho_arquivo}") # Avisa o erro
    sys.exit(1) # Fecha o programa

# Verifica se o arquivo está vazio ou se não tem pares de Órgão + Termo
if len(linhas) == 0 or len(linhas) % 2 != 0:
    print("ERRO: O arquivo deve conter pares de linhas (Órgão + Termo).") # Mensagem de erro
    sys.exit(1) # Fecha o programa

print(f"Carregados {len(linhas)//2} itens para processar.") # Mostra quantos pares foram achados

# --- LOOP DE PROCESSAMENTO ---
# Percorre a lista de 2 em 2 (i=0, i=2, i=4...) para pegar sempre o par correto
for i in range(0, len(linhas), 2):
    orgao = linhas[i] # A linha par é o nome do Órgão (nome da pasta)
    termo = linhas[i + 1] # A linha ímpar é o termo de busca no site

    driver = None # Reseta a variável do navegador para cada ciclo

    try: # Tenta realizar a automação para este item específico
        print(f"\n>>> Processando: {orgao} -> {termo}") # Log visual no console
        
        # Monta o caminho da pasta onde o arquivo será salvo
        diretorio_destino = f"C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD\\Site_Legado\\{orgao}"
        
        if not os.path.exists(diretorio_destino): # Se a pasta não existir
            os.makedirs(diretorio_destino) # Cria a pasta automaticamente

        # --- BLOCO: CONFIGURAÇÃO DO CHROME (DRIVER) ---
        chrome_options = Options() # Cria o objeto de configurações
        chrome_options.add_argument("--ignore-certificate-errors") # Ignora erros de SSL/Segurança
        chrome_options.add_argument("--ignore-ssl-errors") # Ignora erros de certificados SSL
        chrome_options.add_argument("--no-sandbox") # Medida de segurança para ambientes Linux/Servidores
        chrome_options.add_argument("--disable-dev-shm-usage") # Evita erro de memória compartilhada
        
        # Define preferências internas do navegador (onde salvar o arquivo)
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": diretorio_destino, # Define a pasta de destino
            "download.prompt_for_download": False, # Não pergunta onde salvar
            "download.directory_upgrade": True, # Força a atualização do diretório
            "safeBrowse.enabled": True, # Ativa navegação segura para permitir downloads
        })

        # Remove a mensagem de que o Chrome é um robô (evita bloqueios)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Inicia o serviço do driver baixando a versão correta do Chrome automaticamente
        servico = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=servico, options=chrome_options) # Abre o navegador
        driver.maximize_window() # Deixa a janela em tela cheia

        # --- BLOCO: NAVEGAÇÃO E INTERAÇÃO ---
        url = "https://dd-publico.serpro.gov.br/extensions/obras/obras.html" # URL alvo
        driver.get(url) # Comando para o navegador ir até o site

        time.sleep(15) # Espera fixa de 15s para o dashboard carregar (pesado)

        # 1. Localiza o texto "Órgão Superior" e clica nele para abrir o filtro
        print("Tentando clicar em Órgão Superior...")
        orgao_superior = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão Superior']"))
        )
        orgao_superior.click() # Clica no elemento
        time.sleep(2) # Espera o menu abrir

        # 2. Localiza o campo de input de busca por um atributo específico (data-testid)
        print(f"Digitando termo: {termo}")
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        novo_campo_input.clear() # Limpa qualquer texto que já esteja lá
        novo_campo_input.send_keys(termo) # Digita o termo do arquivo TXT
        time.sleep(1) # Espera 1s
        novo_campo_input.send_keys(Keys.ENTER) # Aperta a tecla ENTER
        time.sleep(3) # Espera o filtro ser aplicado

        # 3. Localiza o botão de confirmar a seleção dos filtros
        print("Confirmando seleção...")
        botao = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        )
        botao.click() # Clica no botão
        
        time.sleep(5) # Espera a tabela atualizar os dados na tela

        # 4. Localiza o botão de exportar (Download) pelo ID
        print("Clicando em exportar...")
        botao_exportar = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "btn-export-tbl-detalhes-obras"))
        )
        botao_exportar.click() # Clica para baixar o arquivo

        print(f"SUCESSO: Download iniciado para {orgao}.")
        
        time.sleep(20) # Espera 20s para garantir que o download termine antes de fechar

    except Exception as e: # Caso ocorra qualquer erro no bloco try acima
        erro_msg = str(e) # Converte o erro em texto
        logger.error(f"Erro em {orgao}: {erro_msg}") # Grava no arquivo de log
        print(f"!!! ERRO em {orgao}: {erro_msg}") # Avisa no console

    finally: # Bloco que SEMPRE executa, com erro ou não
        if driver: # Se o navegador chegou a ser aberto
            try:
                driver.quit() # Fecha o navegador e encerra o processo
            except: # Se falhar ao fechar (navegador já fechado)
                pass # Apenas ignora
    
    time.sleep(3) # Pausa curta antes de começar o próximo órgão da lista

print("\nProcesso finalizado.") # Fim do script