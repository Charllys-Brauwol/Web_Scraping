# ==============================================================================
# --- IMPORTAÇÃO DE BIBLIOTECAS ---
# Aqui trazemos todas as ferramentas que o Python vai precisar usar.
# ==============================================================================
import time  # Para criar pausas manuais no código (esperar a tela carregar)
import sys  # Para comandos do sistema, como fechar o programa em caso de erro fatal
import requests  # Para testar a conexão com a internet
import logging  # Para criar o arquivo de "diário" (log) onde os erros serão salvos
import os  # Para criar e manipular pastas no Windows
from datetime import datetime  # Para pegar a data de hoje e colocar no nome do arquivo de log
from selenium import webdriver  # O "motorista" principal que vai abrir o navegador
from selenium.webdriver.common.by import By  # Para achar elementos na tela (por XPATH, CSS, ID)
from selenium.webdriver.support.ui import WebDriverWait  # Para mandar o robô ter paciência e esperar
from selenium.webdriver.support import expected_conditions as EC  # Para definir o que o robô deve esperar (ex: um botão aparecer)
from selenium.webdriver.common.keys import Keys  # Para simular apertos no teclado (como a tecla ENTER)
from selenium.webdriver.chrome.options import Options  # Para configurar opções ocultas do Chrome
from selenium.webdriver.chrome.service import Service  # Para gerenciar o serviço do Chrome em segundo plano
from webdriver_manager.chrome import ChromeDriverManager # Baixa a versão correta do Chrome automaticamente (A "Mágica")

# ==============================================================================
# --- CONFIGURAÇÃO DO LOGGER (REGISTRO DE ERROS) ---
# Este bloco cria um arquivo de texto para anotar qualquer erro que faça o robô falhar.
# ==============================================================================
data_atual = datetime.now().strftime("%Y-%m-%d") # Pega a data de hoje no formato Ano-Mês-Dia
log_filename = f"erros_cidades_educacao.{data_atual}.log" # Dá o nome ao arquivo com a data de hoje

log_handler = logging.FileHandler(log_filename, encoding="utf-8") # Prepara para escrever no arquivo aceitando acentos (UTF-8)
log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")) # Define que cada linha terá: Hora - Tipo de Erro - Mensagem

logger = logging.getLogger() # Cria o "anotador" principal
logger.setLevel(logging.ERROR) # Diz para o anotador só registrar ERROS (ignorar avisos bobos)
if logger.hasHandlers(): # Se o anotador já tiver um arquivo aberto na memória...
    logger.handlers.clear() # ...limpa para não escrever as coisas duplicadas
logger.addHandler(log_handler) # Entrega o caderno (arquivo) para o anotador

# ==============================================================================
# --- FUNÇÃO: VERIFICAÇÃO DE INTERNET ---
# Tenta acessar o Google rapidamente. Se não conseguir, é porque a internet caiu.
# ==============================================================================
def verificar_conexao_internet(url="http://www.google.com", timeout=5):
    try: # Tenta fazer o que está abaixo
        requests.head(url, timeout=timeout) # Tenta bater na porta do Google esperando no máximo 5 segundos
        return True # Se o Google responder, retorna que TEM internet
    except Exception: # Se der erro ou o tempo esgotar...
        return False # Retorna que NÃO TEM internet

# ==============================================================================
# --- INÍCIO DO SCRIPT ---
# Aqui começa a execução real do programa de automação.
# ==============================================================================

print("--- Iniciando Script Cidades e Educação (3 Linhas: OrgSup, Termo, Situação) ---") # Aviso na tela preta do terminal

if not verificar_conexao_internet(): # Chama a função que criamos acima. Se for Falso...
    print("ERRO CRÍTICO: Sem conexão com a internet.") # Imprime o erro
    sys.exit(1) # Mata o programa imediatamente

# Caminho do arquivo de texto que contém a lista do que deve ser pesquisado
caminho_arquivo = r"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\pesquisacidadeeeducacao.txt"

try: # Tenta abrir o arquivo
    with open(caminho_arquivo, "r", encoding="utf-8") as file: # Abre em modo Leitura ("r") com acentos suportados
        linhas = file.read().splitlines() # Lê tudo, divide linha por linha e remove o "Enter" invisível do final de cada uma
except FileNotFoundError: # Se o arquivo não existir na pasta D:\...
    print(f"ERRO CRÍTICO: Arquivo não encontrado em {caminho_arquivo}") # Avisa onde procurou e não achou
    sys.exit(1) # Mata o programa

# ==============================================================================
# --- VALIDAÇÃO DO ARQUIVO (MÚLTIPLOS DE 3) ---
# Garante que o usuário não preencheu o arquivo txt errado. Tem que ser trio.
# ==============================================================================
if len(linhas) == 0 or len(linhas) % 3 != 0: # Se não tiver nada OR a divisão por 3 não for exata (resto != 0)
    error_message = "O arquivo deve conter grupos de 3 linhas (Órgão Sup, Termo Org, Situação)."
    logger.error(error_message) # Salva o erro no arquivo de log
    print(f"ERRO: {error_message}") # Mostra na tela
    sys.exit(1) # Mata o programa

print(f"Carregados {len(linhas)//3} itens para processar.") # Mostra quantos trios foram identificados

# ==============================================================================
# --- LOOP PRINCIPAL DE NAVEGAÇÃO ---
# Para cada trio de linhas no arquivo, o robô vai abrir o navegador e fazer a pesquisa.
# ==============================================================================
for i in range(0, len(linhas), 3): # Vai do zero até o fim da lista, pulando de 3 em 3
    orgaosup = linhas[i] # A 1ª linha do trio é o nome da pasta a ser criada
    termoorgsup = linhas[i + 1] # A 2ª linha do trio é o termo de busca do Órgão Superior
    termosituacao = linhas[i + 2] # A 3ª linha do trio é o termo de busca da Situação da obra

    driver = None # Reseta a variável do navegador para não misturar com o ciclo anterior

    try: # Inicia o bloco de tentativa (se der erro aqui dentro, ele pula pro "except" lá embaixo)
        print(f"\n>>> Processando: {orgaosup} -> {termoorgsup} -> {termosituacao}") # Mostra na tela o que está fazendo
        
        # Define onde o arquivo será salvo no seu computador
        diretorio_destino = f"C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD\\Site_Legado\\{orgaosup}"
        
        if not os.path.exists(diretorio_destino): # Pergunta ao Windows: "Essa pasta já existe?"
            os.makedirs(diretorio_destino) # Se não existe, cria a pasta e as subpastas

        # ==============================================================================
        # --- CONFIGURAÇÃO E ABERTURA DO DRIVER (NAVEGADOR) ---
        # Deixa o Chrome invisível a bloqueios e define onde salvar os downloads
        # ==============================================================================
        chrome_options = Options() # Instancia o configurador
        chrome_options.add_argument("--ignore-certificate-errors") # Ignora aviso de site não seguro (HTTPS cortado)
        chrome_options.add_argument("--ignore-ssl-errors") # Ignora falhas de certificado SSL
        chrome_options.add_argument("--no-sandbox") # Evita que o navegador trave por falta de privilégios do Windows
        chrome_options.add_argument("--disable-dev-shm-usage") # Evita erro de falta de memória (tela branca no Chrome)
        
        chrome_options.add_experimental_option("prefs", { # Configurações de preferências do usuário
            "download.default_directory": diretorio_destino, # Joga o download direto pra sua pasta criada lá em cima
            "download.prompt_for_download": False, # Não abre aquela janela perguntando "Onde deseja salvar?"
            "download.directory_upgrade": True, # Força o Chrome a reconhecer a pasta nova
            "safeBrowse.enabled": True, # Mantém verificação de vírus ativa para o download não ser bloqueado silenciosamente
        })
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) # Tira a faixa "O Chrome está sendo controlado"
        chrome_options.add_experimental_option('useAutomationExtension', False) # Desativa extensões de automação para burlar defesas do site

        servico = Service(ChromeDriverManager().install()) # Verifica a versão do seu Chrome, baixa o arquivo executável correto e prepara o serviço
        driver = webdriver.Chrome(service=servico, options=chrome_options) # Finalmente, abre o Chrome com todas as regras acima
        driver.maximize_window() # Deixa a janela grande para não esconder nenhum botão

        # ==============================================================================
        # --- NAVEGAÇÃO NO SITE DO SERPRO ---
        # ==============================================================================
        url = "https://dd-publico.serpro.gov.br/extensions/obras/obras.html" # Endereço do painel
        driver.get(url) # Manda o navegador ir para o endereço
        
        time.sleep(15) # Espera 15 segundos porque o painel do Qlik/Serpro é muito pesado para carregar os gráficos

        # ---------------------------------------------------------
        # FILTRO 1: ÓRGÃO SUPERIOR
        # ---------------------------------------------------------
        print("1. Selecionando Órgão Superior...")
        WebDriverWait(driver, 20).until( # Espera até 20 segundos...
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão Superior']")) # ...até o título "Órgão Superior" ficar clicável
        ).click() # E clica nele
        time.sleep(2) # Espera o menu descer

        campo = WebDriverWait(driver, 10).until( # Espera até 10 segundos...
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']")) # ...até a caixinha de texto aparecer
        )
        campo.clear() # Limpa qualquer lixo que estiver lá
        campo.send_keys(termoorgsup) # Digita a 2ª linha do seu txt
        time.sleep(1) # Espera o site processar as letras
        campo.send_keys(Keys.ENTER) # Aperta o Enter do teclado
        time.sleep(3) # Espera a lista filtrar e ficar só um item

        WebDriverWait(driver, 10).until( # Espera 10 segundos...
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']")) # ...pelo botão verde (ou check) de confirmar
        ).click() # E clica nele
        time.sleep(3) # Espera o painel inteiro recalcular os números com base nesse filtro

        # ---------------------------------------------------------
        # FILTRO 2: SITUAÇÃO ATUAL
        # ---------------------------------------------------------
        print("2. Selecionando Situação Atual...")
        WebDriverWait(driver, 20).until( # Mesma lógica: espera 20s...
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='Situação Atual']")) # ...até achar a caixinha da "Situação Atual"
        ).click() # E clica
        time.sleep(2) # Espera o menu descer

        campo = WebDriverWait(driver, 10).until( # Espera a caixa de pesquisa
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        campo.clear() # Limpa
        campo.send_keys(termosituacao) # Digita a 3ª linha do seu txt (Ex: "Concluída")
        time.sleep(1)
        campo.send_keys(Keys.ENTER) # Dá Enter
        time.sleep(3) # Espera filtrar a lista do menu

        WebDriverWait(driver, 10).until( # Procura o botão de confirmar do 2º filtro
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        ).click() # Clica
        
        time.sleep(5) # Espera final de 5s pro painel inteiro recalcular antes de você mandar baixar

        # ---------------------------------------------------------
        # EXPORTAÇÃO
        # ---------------------------------------------------------
        print("3. Exportando...")
        botao_exportar = WebDriverWait(driver, 20).until( # Espera 20s até o botão de download liberar
            EC.element_to_be_clickable((By.ID, "btn-export-tbl-detalhes-obras")) # Localiza o botão pelo ID dele no código do site
        )
        botao_exportar.click() # Manda baixar o arquivo (planilha)

        print(f"SUCESSO: Download iniciado.")
        time.sleep(80) # O robô cruza os braços e espera absurdos 80 segundos. (Tempo chutado para garantir que um download lento termine)

    except Exception as e: # Se literalmente QUALQUER erro ocorrer do "try:" até aqui...
        erro_msg = str(e) # Converte o erro técnico para formato de texto
        logger.error(f"Erro em {orgaosup} - {termoorgsup}: {erro_msg}") # Escreve o texto no nosso arquivo de log
        print(f"!!! ERRO: {erro_msg}") # Joga o texto em vermelho na tela

    finally: # Executa isso INDEPENDENTE de ter dado sucesso ou erro
        if driver: # Verifica se o robô realmente chegou a abrir uma tela do navegador
            try:
                driver.quit() # Aperta o 'X' e fecha o Chrome, liberando a Memória RAM do computador
            except: # Se ele já estiver fechado e der erro...
                pass # ...finge que não viu nada e segue a vida

    time.sleep(2) # Pequena pausa para respirar antes de abrir o próximo grupo de 3 linhas

print("\nProcesso finalizado.") # Acabaram as linhas do txt. O programa acaba.