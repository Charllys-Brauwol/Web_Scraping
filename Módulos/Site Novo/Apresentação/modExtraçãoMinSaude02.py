# ==============================================================================
# --- IMPORTAÇÃO DE BIBLIOTECAS ---
# Ferramentas que o Python vai usar para controlar tempo, arquivos e o navegador.
# ==============================================================================
import time  # Para pausar o código (esperar a tela carregar)
import sys  # Para encerrar o programa em caso de erro crítico
import requests  # Para testar a conexão com a internet
import logging  # Para criar o "diário" (log) de erros
import os  # Para criar as pastas no Windows
from datetime import datetime  # Para pegar a data atual para o nome do log
from selenium import webdriver  # O controlador do navegador
from selenium.webdriver.common.by import By  # Para localizar botões e campos
from selenium.webdriver.support.ui import WebDriverWait  # Para esperas inteligentes
from selenium.webdriver.support import expected_conditions as EC  # Condições de espera (ex: elemento clicável)
from selenium.webdriver.common.keys import Keys  # Para simular o uso do teclado (ENTER)
from selenium.webdriver.chrome.options import Options  # Configurações invisíveis do Chrome
from selenium.webdriver.chrome.service import Service  # Gerenciador do serviço do Chrome
from webdriver_manager.chrome import ChromeDriverManager # A mágica que baixa o driver certo sozinho

# ==============================================================================
# --- CONFIGURAÇÃO DO LOGGER (REGISTRO DE ERROS) ---
# Cria um arquivo .log para registrar falhas sem que o script pare de rodar.
# ==============================================================================
data_atual = datetime.now().strftime("%Y-%m-%d") # Pega a data atual (Ano-Mês-Dia)
log_filename = f'erros_saude2_automacao.{data_atual}.log' # Define o nome do arquivo com a data

log_handler = logging.FileHandler(log_filename, encoding='utf-8') # Prepara para gravar texto com acentos
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')) # Formato: Data/Hora - Tipo - Mensagem

logger = logging.getLogger() # Cria o anotador
logger.setLevel(logging.ERROR) # Diz para anotar só erros graves
if logger.hasHandlers(): # Se já existir um anotador aberto...
    logger.handlers.clear() # ...limpa para não duplicar os avisos
logger.addHandler(log_handler) # Inicia a gravação

# ==============================================================================
# --- FUNÇÃO: VERIFICAÇÃO DE INTERNET ---
# Testa a rede antes de abrir o navegador.
# ==============================================================================
def verificar_conexao_internet(url="http://www.google.com", timeout=5):
    try: # Tenta acessar o Google
        requests.head(url, timeout=timeout) # Espera resposta por até 5 segundos
        return True # Retorna Verdadeiro se tem internet
    except Exception: # Se falhar
        return False # Retorna Falso

# ==============================================================================
# --- INÍCIO DO SCRIPT PRINCIPAL ---
# ==============================================================================

print("--- Iniciando Script de Automação (SAÚDE 2 - 4 LINHAS) ---") # Aviso no terminal

if not verificar_conexao_internet(): # Chama a função da internet. Se der Falso:
    print("ERRO CRÍTICO: Sem conexão com a internet.") # Avisa
    sys.exit(1) # E fecha o programa

# Onde o script vai procurar as instruções (o arquivo de texto)
caminho_arquivo = r"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\pesquisasaude2.txt"

try: # Tenta abrir o arquivo TXT
    with open(caminho_arquivo, "r", encoding="utf-8") as file: # Lê com suporte a acentos
        linhas = file.read().splitlines() # Separa linha por linha e tira os espaços invisíveis
except FileNotFoundError: # Se não achar o arquivo no pendrive/HD
    print(f"ERRO CRÍTICO: Arquivo não encontrado em {caminho_arquivo}")
    sys.exit(1) # Fecha o programa

# ==============================================================================
# --- VALIDAÇÃO DO ARQUIVO (MÚLTIPLOS DE 4) ---
# Garante que o usuário formatou o txt corretamente com blocos de 4 linhas.
# ==============================================================================
if len(linhas) == 0 or len(linhas) % 4 != 0: # Se for vazio ou não for divisível por 4
    print("ERRO: O arquivo deve conter grupos de 4 linhas:\n1. Órgão Sup.\n2. Termo Sup.\n3. Órgão\n4. Situação Atual")
    sys.exit(1) # Fecha o programa

print(f"Carregados {len(linhas)//4} itens para processar.") # Mostra quantos quartetos encontrou

# ==============================================================================
# --- LOOP PRINCIPAL DE NAVEGAÇÃO ---
# ==============================================================================
# Pula de 4 em 4 linhas para ler um bloco completo de cada vez
for i in range(0, len(linhas), 4):
    orgaosup = linhas[i] # Linha 1: Nome da pasta e Órgão Superior
    termoorgsup = linhas[i + 1] # Linha 2: O que digitar no 1º filtro
    orgao_filtro_valor = linhas[i + 2] # Linha 3: O que digitar no 2º filtro (Novo!)
    termosituacao = linhas[i + 3] # Linha 4: O que digitar no 3º filtro

    driver = None # Reseta o navegador para este ciclo

    try: # Tenta executar os passos abaixo
        print(f"\n>>> Processando: {orgaosup} -> {orgao_filtro_valor} -> {termosituacao}")
        
        # Define a pasta no Windows onde a planilha vai cair
        diretorio_destino = f"C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD\\Site_Legado\\{orgaosup}"
        
        if not os.path.exists(diretorio_destino): # Se a pasta não existe...
            os.makedirs(diretorio_destino) # ...cria a pasta

        # ==============================================================================
        # --- CONFIGURAÇÃO BLINDADA DO DRIVER ---
        # ==============================================================================
        chrome_options = Options() # Configura o Chrome
        chrome_options.add_argument("--ignore-certificate-errors") # Ignora erro de site inseguro (SSL inválido)
        chrome_options.add_argument("--ignore-ssl-errors") # Reforça a ignorância a erros SSL
        chrome_options.add_argument("--no-sandbox") # Previne que o Chrome seja bloqueado pelo Windows
        chrome_options.add_argument("--disable-dev-shm-usage") # Evita crash de memória no navegador
        
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": diretorio_destino, # Diz para baixar direto na pasta do Órgão
            "download.prompt_for_download": False, # Desativa a janela "Salvar como..."
            "download.directory_upgrade": True, # Atualiza permissão da pasta
            "safeBrowse.enabled": True, # Deixa o antivírus do Chrome ativado para não bloquear o arquivo
        })
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) # Tira aviso de robô
        chrome_options.add_experimental_option('useAutomationExtension', False) # Oculta ser robô

        # Baixa o driver certinho e abre o navegador
        servico = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=servico, options=chrome_options)
        driver.maximize_window() # Tela cheia

        # ==============================================================================
        # --- NAVEGAÇÃO NO SITE DO SERPRO ---
        # ==============================================================================
        url = "https://dd-publico.serpro.gov.br/extensions/obras/obras.html"
        driver.get(url) # Acessa a página

        time.sleep(15) # Espera 15s o painel pesado carregar

        # ---------------------------------------------------------
        # FILTRO 1: ÓRGÃO SUPERIOR
        # ---------------------------------------------------------
        print("1. Selecionando Órgão Superior...")
        WebDriverWait(driver, 20).until( # Espera até 20s
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão Superior']")) # Até o botão aparecer
        ).click() # E clica
        time.sleep(2) # Espera menu descer

        campo = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        campo.clear() # Limpa a caixa
        campo.send_keys(termoorgsup) # Digita a Linha 2 do txt
        time.sleep(1)
        campo.send_keys(Keys.ENTER) # Dá Enter
        time.sleep(3)

        WebDriverWait(driver, 10).until( # Confirma o 1º filtro
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        ).click()
        time.sleep(3)

        # ---------------------------------------------------------
        # FILTRO 2: ÓRGÃO (A Novidade deste script)
        # ---------------------------------------------------------
        print("2. Selecionando Órgão...")
        WebDriverWait(driver, 20).until( # Procura o botão de Órgão (subordinado ao Órgão Superior)
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão']"))
        ).click()
        time.sleep(2)

        campo = WebDriverWait(driver, 10).until( # Pega o campo de texto novo
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        campo.clear()
        campo.send_keys(orgao_filtro_valor) # Digita a Linha 3 do txt
        time.sleep(1)
        campo.send_keys(Keys.ENTER)
        time.sleep(3)

        WebDriverWait(driver, 10).until( # Confirma o 2º filtro
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        ).click()
        time.sleep(3)

        # ---------------------------------------------------------
        # FILTRO 3: SITUAÇÃO ATUAL
        # ---------------------------------------------------------
        print("3. Selecionando Situação Atual...")
        WebDriverWait(driver, 20).until( # Procura o filtro de Situação
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Situação Atual']"))
        ).click()
        time.sleep(2)

        campo = WebDriverWait(driver, 10).until( # Pega o campo
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        campo.clear()
        campo.send_keys(termosituacao) # Digita a Linha 4 do txt
        time.sleep(1)
        campo.send_keys(Keys.ENTER)
        time.sleep(3)

        WebDriverWait(driver, 10).until( # Confirma o 3º filtro
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        ).click()
        
        # Espera 5 segundos para a tabela no meio da tela terminar de carregar com as 3 regras aplicadas
        time.sleep(5) 

        # ---------------------------------------------------------
        # EXPORTAÇÃO
        # ---------------------------------------------------------
        print("4. Exportando...")
        botao_exportar = WebDriverWait(driver, 20).until( # Espera o botão de baixar ficar verde/clicável
            EC.element_to_be_clickable((By.ID, "btn-export-tbl-detalhes-obras"))
        )
        botao_exportar.click() # Clica para baixar

        print(f"SUCESSO: Download iniciado.")
        
        # Robô cruza os braços e espera 60 segundos para garantir que o arquivo baixe antes de fechar tudo
        time.sleep(60)

    except Exception as e: # Se der qualquer bug na navegação
        erro_msg = str(e) # Transforma o erro em texto
        logger.error(f"Erro em {orgaosup} (Situação: {termosituacao}): {erro_msg}") # Grava no log
        print(f"!!! ERRO: {erro_msg}") # Avisa no terminal

    finally: # Código de limpeza (roda independente de erro ou sucesso)
        if driver: # Se o navegador estiver aberto
            try:
                driver.quit() # Encerra o Chrome
            except:
                pass # Se já estava fechado, ignora
    
    time.sleep(3) # Pausa dramática de 3s antes do próximo grupo de 4 linhas

print("\nProcesso finalizado.") # Fim da leitura do TXT