# ==============================================================================
# --- IMPORTAÇÃO DE BIBLIOTECAS ---
# Módulos necessários para o robô funcionar, acessar a web e manipular arquivos.
# ==============================================================================
import time  # Para pausar a execução (sleep)
import sys  # Para comandos de sistema, como abortar o script (sys.exit)
import requests  # Para testar se a conexão com a internet está ativa
import logging  # Para registrar falhas em um arquivo de texto (log)
import os  # Para criar as pastas onde os arquivos serão salvos
from datetime import datetime  # Para obter a data atual (usada no nome do arquivo de log)
from selenium import webdriver  # Para abrir e controlar o navegador Google Chrome
from selenium.webdriver.common.by import By  # Para localizar elementos (botões, campos) no HTML
from selenium.webdriver.support.ui import WebDriverWait  # Para configurar esperas inteligentes
from selenium.webdriver.support import expected_conditions as EC  # Regras de espera (ex: esperar o botão ficar visível)
from selenium.webdriver.common.keys import Keys  # Para simular o uso do teclado (ex: tecla ENTER)
from selenium.webdriver.chrome.options import Options  # Para configurar preferências do Chrome (ex: onde salvar downloads)
from selenium.webdriver.chrome.service import Service  # Para gerenciar o processo do ChromeDriver
from webdriver_manager.chrome import ChromeDriverManager  # Baixa e instala a versão correta do ChromeDriver automaticamente

# ==============================================================================
# --- CONFIGURAÇÃO DO LOGGER (REGISTRO DE ERROS) ---
# Prepara um arquivo de texto para salvar detalhes caso o robô falhe em alguma etapa.
# ==============================================================================
data_atual = datetime.now().strftime("%Y-%m-%d") # Extrai a data de hoje no formato Ano-Mês-Dia
log_filename = f'erros_saude_automacao.{data_atual}.log' # Define o nome do arquivo de erro com a data

log_handler = logging.FileHandler(log_filename, encoding='utf-8') # Cria/Abre o arquivo, permitindo caracteres especiais (acentos)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')) # Define que as anotações terão: Data/Hora - Gravidade - Mensagem

logger = logging.getLogger() # Instancia o gerenciador de logs
logger.setLevel(logging.ERROR) # Define que ele só vai anotar coisas da gravidade "ERRO" para cima
if logger.hasHandlers(): # Verifica se já existe um gravador de log ativo na memória
    logger.handlers.clear() # Se existir, limpa para evitar que a mesma mensagem seja escrita várias vezes
logger.addHandler(log_handler) # Atrela o arquivo ao gerenciador

# ==============================================================================
# --- FUNÇÃO: VERIFICAÇÃO DE INTERNET ---
# Impede que o script tente abrir o Chrome se não houver internet.
# ==============================================================================
def verificar_conexao_internet(url="http://www.google.com", timeout=5):
    try: # Tenta executar o comando
        requests.head(url, timeout=timeout) # Faz um "ping" rápido no Google. Se demorar mais de 5s, desiste.
        return True # Se o Google responder, avisa que a internet está OK
    except Exception: # Se der qualquer falha de rede
        return False # Avisa que a internet caiu

# ==============================================================================
# --- INÍCIO DO SCRIPT PRINCIPAL ---
# ==============================================================================

print("--- Iniciando Script de Automação (SAÚDE/3 LINHAS) ---") # Imprime na tela preta do terminal

if not verificar_conexao_internet(): # Chama a função de internet. Se o resultado for 'Falso':
    print("ERRO CRÍTICO: Sem conexão com a internet.") # Exibe o aviso
    sys.exit(1) # E encerra o programa imediatamente

# Define onde está o arquivo com a lista do que o robô deve pesquisar
caminho_arquivo = r"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\pesquisasaude.txt"

try: # Tenta abrir o arquivo TXT
    with open(caminho_arquivo, "r", encoding="utf-8") as file: # Abre em modo leitura ("r")
        linhas = file.read().splitlines() # Lê tudo e quebra em uma lista, linha por linha
except FileNotFoundError: # Se não achar o arquivo no local indicado
    print(f"ERRO CRÍTICO: Arquivo não encontrado em {caminho_arquivo}")
    sys.exit(1) # Encerra o programa

# ==============================================================================
# --- VALIDAÇÃO DO ARQUIVO (MÚLTIPLOS DE 3) ---
# Garante que as informações foram cadastradas em grupos de 3 linhas.
# ==============================================================================
if len(linhas) == 0 or len(linhas) % 3 != 0: # Verifica se está vazio ou se sobram linhas na divisão por 3
    print("ERRO: O arquivo deve conter grupos de 3 linhas (Órgão Sup. + Termo Sup. + Órgão).")
    sys.exit(1) # Encerra o programa

print(f"Carregados {len(linhas)//3} itens para processar.") # Avisa quantos trios foram encontrados

# ==============================================================================
# --- LOOP DE EXECUÇÃO ---
# ==============================================================================
for i in range(0, len(linhas), 3): # Percorre a lista pulando de 3 em 3
    orgaosup = linhas[i] # Linha 1: Nome da pasta/Órgão Maior
    termoorgsup = linhas[i + 1] # Linha 2: Termo a ser digitado no 1º filtro
    orgao_filtro_valor = linhas[i + 2] # Linha 3: Termo a ser digitado no 2º filtro

    driver = None # Zera a variável que controla o navegador

    try: # Inicia a tentativa de executar os passos no site
        print(f"\n>>> Processando: {orgaosup} -> {orgao_filtro_valor}")
        
        # Define o caminho completo onde o arquivo baixado vai ser salvo
        diretorio_destino = f"C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD\\Site_Legado\\{orgaosup}"
        
        if not os.path.exists(diretorio_destino): # Se a pasta não existir no Windows...
            os.makedirs(diretorio_destino) # ...o Python cria ela para você

        # ==============================================================================
        # --- CONFIGURAÇÃO DO DRIVER (NAVEGADOR) ---
        # ==============================================================================
        chrome_options = Options() # Instancia o painel de configurações ocultas
        chrome_options.add_argument("--ignore-certificate-errors") # Ignora bloqueios de "Site não seguro" (comum no governo)
        chrome_options.add_argument("--ignore-ssl-errors") # Ignora problemas com certificados digitais da página
        chrome_options.add_argument("--no-sandbox") # Libera restrições de segurança do Windows (evita travamentos)
        chrome_options.add_argument("--disable-dev-shm-usage") # Usa o disco rígido em vez da memória RAM para arquivos temporários (evita o erro "Aw, Snap!" do Chrome)
        
        # Configura as preferências de download
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": diretorio_destino, # Os arquivos baixados vão direto para a pasta que criamos acima
            "download.prompt_for_download": False, # Desativa aquela janela de "Salvar como"
            "download.directory_upgrade": True, # Ajuda o Chrome a reconhecer alterações na pasta
            "safeBrowse.enabled": True, # Mantém o download seguro, evitando que o Google bloqueie a planilha silenciosamente
        })
        
        # Esconde do site que o navegador está sendo controlado por robô
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Baixa a versão correta do Chrome e inicia a janela
        servico = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=servico, options=chrome_options)
        driver.maximize_window() # Deixa a janela em tela cheia

        # ==============================================================================
        # --- NAVEGAÇÃO NO PAINEL DO SERPRO ---
        # ==============================================================================
        url = "https://dd-publico.serpro.gov.br/extensions/obras/obras.html"
        driver.get(url) # Manda o Chrome acessar o link

        # Espera bruta de 15 segundos para dar tempo do painel carregar gráficos e filtros iniciais
        time.sleep(15)

        # --- PASSO 1: ÓRGÃO SUPERIOR ---
        print("1. Selecionando Órgão Superior...")
        orgao_superior = WebDriverWait(driver, 20).until( # Espera até 20s
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão Superior']")) # Até o botão com o texto "Órgão Superior" ficar clicável
        )
        orgao_superior.click() # Clica no botão para abrir a lista suspensa
        time.sleep(2) # Espera a lista descer

        # Digita o termo do órgão superior
        novo_campo_input = WebDriverWait(driver, 10).until( # Espera 10s
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']")) # Até a caixa de pesquisa aparecer
        )
        novo_campo_input.clear() # Limpa qualquer texto fantasma
        novo_campo_input.send_keys(termoorgsup) # Escreve o texto da Linha 2 do txt
        time.sleep(1) # Pausa para o site registrar a digitação
        novo_campo_input.send_keys(Keys.ENTER) # Simula um aperto no "ENTER" para filtrar
        time.sleep(3) # Aguarda o painel responder à tecla Enter

        # Confirma
        botao = WebDriverWait(driver, 10).until( # Procura o botão verde de confirmação
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        )
        botao.click() # Confirma o 1º filtro
        time.sleep(3) # Espera o painel recalcular tudo

        # --- PASSO 2: ÓRGÃO ---
        print("2. Selecionando Órgão...")
        orgao_filtro = WebDriverWait(driver, 20).until( # Espera até 20s
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão']")) # Pelo segundo botão (Filtro subordinado)
        )
        orgao_filtro.click() # Clica
        time.sleep(2) # Espera lista descer

        # Digita o termo do órgão
        novo_campo_input = WebDriverWait(driver, 10).until( # Procura a caixa de pesquisa desse menu
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        novo_campo_input.clear() # Limpa
        novo_campo_input.send_keys(orgao_filtro_valor) # Digita a Linha 3 do seu txt
        time.sleep(1) # Pausa
        novo_campo_input.send_keys(Keys.ENTER) # Aperta ENTER
        time.sleep(3) # Pausa

        # Confirma
        botao = WebDriverWait(driver, 10).until( # Procura o botão de confirmar do 2º filtro
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        )
        botao.click() # Confirma
        time.sleep(5) # Espera 5 segundos para a tabela de dados principal do site atualizar com os dois filtros aplicados

        # --- EXPORTAÇÃO (DOWNLOAD) ---
        print("3. Exportando...")
        botao_exportar = WebDriverWait(driver, 20).until( # Espera 20s pelo botão de exportar
            EC.element_to_be_clickable((By.ID, "btn-export-tbl-detalhes-obras")) # Achando ele pela ID do HTML
        )
        botao_exportar.click() # Manda baixar a planilha Excel

        print(f"SUCESSO: Download iniciado para {orgaosup} - {orgao_filtro_valor}.")
        
        # O robô espera 25 segundos para garantir que o arquivo seja baixado por completo
        time.sleep(25)

    except Exception as e: # Caso dê algum erro de carregamento ou o site mude nos blocos "try" acima...
        erro_msg = str(e) # Converte o erro em formato de texto
        logger.error(f"Erro em {orgaosup}: {erro_msg}") # Salva o erro naquele arquivo .log que configuramos no início
        print(f"!!! ERRO em {orgaosup}: {erro_msg}") # Mostra o erro em vermelho na sua tela preta

    finally: # Bloco de segurança final (roda com ou sem erro no meio do caminho)
        if driver: # Verifica se o Chrome chegou a ser aberto na memória
            try:
                driver.quit() # Encerra o navegador e libera memória RAM
            except:
                pass # Ignora erros de fechamento (ex: você já fechou a janela na mão)
    
    time.sleep(3) # Pausa rápida de 3 segundos antes do loop voltar e processar o próximo grupo de 3 linhas do arquivo.

print("\nProcesso finalizado.") # Fim da execução   