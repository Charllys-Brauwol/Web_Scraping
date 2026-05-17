# ==============================================================================
# --- IMPORTAÇÕES ---
# Ferramentas de sistema, tempo, dados e automação web.
# ==============================================================================
import time  # Para pausas no script
import sys  # Para comandos do sistema
import os  # Para manipular caminhos e arquivos no Windows (essencial para renomear)
import glob  # Para buscar arquivos em lote (ex: procurar os .crdownload)
import shutil  # Para operações avançadas de arquivos (copiar/mover) - importado, mas não usado aqui
import pandas as pd  # Para ler a planilha de códigos
import logging  # Para o diário de bordo
from datetime import datetime  # Para a data atual
from selenium import webdriver  # O motor do navegador
from selenium.webdriver.common.by import By  # Para localizar botões
from selenium.webdriver.support.ui import WebDriverWait  # Para esperas inteligentes
from selenium.webdriver.support import expected_conditions as EC  # Regras de espera
from selenium.webdriver.chrome.options import Options  # Configurações ocultas do Chrome
import random  # Para tempos aleatórios (não está sendo usado ativamente neste script)

# ==============================================================================
# --- CONFIGURAÇÃO DE LOG (VERSÃO ENXUTA E MODERNA) ---
# Você trocou aquele monte de linhas do script anterior por 'basicConfig'. Muito melhor!
# ==============================================================================
data_atual = datetime.now().strftime("%Y-%m-%d")
log_filename = f"log_download_PAD_CODIGOS_{data_atual}.log"

# Configura o log de uma vez só: nível INFO, formato da mensagem e os dois destinos (Arquivo e Tela)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ==============================================================================
# --- CAMINHOS E URLs ---
# ==============================================================================
DIRETORIO_ENTRADA_CSVS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtraUFID_CODIGOS" # De onde vêm os códigos
DIRETORIO_SAIDA_BASE = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ExtPAD" # Para onde vão os relatórios PAD baixados

# URLs de acesso restrito (Governo)
URL_LOGIN_GOV = "https://www.gov.br/transferegov/pt-br/sistemas/acesso-livre"
URL_PAD_DIRETA = "https://discricionarias.transferegov.sistema.gov.br/voluntarias/_gerencial/RelatorioItensDespesasPAD/relatorioItensDespesasPAD.jsf"

# Tempo máximo de sessão em segundos (O painel do governo derruba a conexão por inatividade/tempo)
TEMPO_SESSAO_LIMITE = 1200 # 20 minutos exatos

# ==============================================================================
# --- FUNÇÃO: CONFIGURAR NAVEGADOR ---
# ==============================================================================
def configurar_driver(pasta_download):
    """Abre o Chrome já ensinando a ele em qual pasta específica da UF ele deve jogar os arquivos."""
    chrome_options = Options()
    prefs = {
        "download.default_directory": pasta_download, # Pasta dinâmica (Muda conforme o Estado)
        "download.prompt_for_download": False, # Desativa o "Salvar como..."
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    return driver

# ==============================================================================
# --- FUNÇÃO: LOGIN E ACESSO AO SISTEMA ---
# ==============================================================================
def fazer_login_e_acessar_pad(driver):
    """Faz a ponte entre a tela pública e a tela logada do PAD."""
    wait = WebDriverWait(driver, 30) # Paciência de 30s
    
    logging.info("Iniciando fluxo de autenticação...")
    driver.get(URL_LOGIN_GOV) # Acessa a página portal
    
    # 1. Tenta fechar o aviso de cookies para ele não ficar na frente dos botões
    try:
        botao_cookie = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.br-button.btn-accept")))
        botao_cookie.click()
        time.sleep(1)
    except:
        pass # Se não tiver aviso de cookie, ignora e segue a vida

    # 2. Clica no link que leva para o sistema interno
    link_consultar = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Consultar Pré-Instrumentos/Instrumentos")))
    link_consultar.click()
    
    # 3. Lógica brilhante de abas: O clique acima abre uma NOVA ABA. 
    # O Selenium precisa ser avisado para "olhar" para a aba nova, senão ele fica preso na antiga.
    time.sleep(3) # Espera a aba nascer
    janelas = driver.window_handles # Pega a lista de todas as abas abertas
    driver.switch_to.window(janelas[-1]) # Muda o foco para a última aba da lista (a mais nova)
    
    logging.info("Aba trocada. Acessando URL direta do PAD...")
    
    # 4. Agora que está autenticado/na aba certa, pula direto para a página final (atalho inteligente)
    driver.get(URL_PAD_DIRETA)
    
    # 5. Verifica se o campo de digitar o código carregou
    wait.until(EC.presence_of_element_located((By.ID, "formRelatorioItensDespesasPAD:idInstrumento")))
    logging.info("Página PAD carregada com sucesso.")
    
    # INCRÍVEL: Retorna o exato segundo em que o login foi feito para iniciar o cronômetro da sessão!
    return time.time() 

# ==============================================================================
# --- FUNÇÃO: MONITOR DE DOWNLOAD E RENOMEAÇÃO ---
# ==============================================================================
def renomear_ultimo_arquivo(pasta_download, novo_nome_base):
    """Fica de olho na pasta, espera o download terminar e troca o nome genérico pelo código do instrumento."""
    
    # 1. Espera o arquivo terminar de baixar
    # O Chrome cria um arquivo falso chamado ".crdownload" enquanto está baixando.
    tempo_espera = 0
    while tempo_espera < 30: # Fica em loop por no máximo 30 segundos
        arquivos_temp = glob.glob(os.path.join(pasta_download, "*.crdownload"))
        if not arquivos_temp: # Se a lista de arquivos temporários estiver vazia, o download acabou!
            break
        time.sleep(1) # Se ainda tiver baixando, dorme 1 segundo e checa de novo
        tempo_espera += 1

    # 2. Pega todos os arquivos reais da pasta
    arquivos = glob.glob(os.path.join(pasta_download, "*"))
    arquivos = [f for f in arquivos if os.path.isfile(f)] # Filtra pra garantir que não vai pegar uma subpasta por acidente
    
    if not arquivos: # Se não baixou nada
        return False

    # 3. Descobre qual é o arquivo recém-baixado olhando a data de modificação mais recente (getmtime)
    arquivo_mais_recente = max(arquivos, key=os.path.getmtime)
    
    # 4. Descobre se é .pdf, .xls, .csv dividindo o nome do arquivo da extensão
    extensao = os.path.splitext(arquivo_mais_recente)[1]
    
    # 5. Monta o nome final
    novo_caminho = os.path.join(pasta_download, f"{novo_nome_base}{extensao}")
    
    # Se o robô já baixou esse arquivo antes (num teste, por exemplo), apaga o velho
    if os.path.exists(novo_caminho):
        try:
            os.remove(novo_caminho)
        except:
            pass

    try:
        os.rename(arquivo_mais_recente, novo_caminho) # Faz a troca de nome no Windows
        logging.info(f"Arquivo renomeado para: {os.path.basename(novo_caminho)}")
        return True
    except Exception as e:
        logging.error(f"Erro ao renomear arquivo: {e}")
        return False

# ==============================================================================
# --- FUNÇÃO PRINCIPAL ---
# ==============================================================================
def processar_estados():
    
    # Acha todos os CSVs gerados pelo script anterior
    padrao_busca = os.path.join(DIRETORIO_ENTRADA_CSVS, "*.csv")
    arquivos_csv = glob.glob(padrao_busca)
    
    if not arquivos_csv:
        logging.error("Nenhum arquivo de códigos encontrado.")
        sys.exit()

    for arquivo_csv in arquivos_csv:
        nome_arquivo = os.path.basename(arquivo_csv)
        
        # Lógica engenhosa para "roubar" a UF de dentro do nome do arquivo
        try:
            parts = nome_arquivo.replace('.csv', '').split('_') # Quebra o nome nas underlines '_'
            # Procura o primeiro pedaço que tenha exatamente 2 letras E sejam maiúsculas (ex: "AC")
            uf = next(p for p in parts if len(p) == 2 and p.isupper()) 
        except:
            uf = "DESCONHECIDO" # Se falhar, salva numa pasta genérica
        
        pasta_destino_uf = os.path.join(DIRETORIO_SAIDA_BASE, uf)
        os.makedirs(pasta_destino_uf, exist_ok=True) # Cria a pasta do Estado
        
        logging.info(f"--- Iniciando processamento da UF: {uf} ---")
        
        # Abre o Chrome e faz o Login, anotando a hora que a sessão começou
        driver = configurar_driver(pasta_destino_uf)
        inicio_sessao = fazer_login_e_acessar_pad(driver)
        
        try:
            # Lê os códigos daquele estado
            df = pd.read_csv(arquivo_csv, sep=';', encoding='utf-8-sig', dtype=str)
            total_linhas = len(df)
            
            for index, row in df.iterrows():
                # --- O CRONÔMETRO DE SESSÃO ---
                # Verifica quanto tempo passou desde o login.
                tempo_decorrido = time.time() - inicio_sessao
                if tempo_decorrido > TEMPO_SESSAO_LIMITE: # Se passou de 20 min...
                    logging.warning("Tempo de sessão (20min) expirado. Reiniciando navegador...")
                    driver.quit() # Fecha tudo para matar o cache
                    driver = configurar_driver(pasta_destino_uf) # Abre de novo
                    inicio_sessao = fazer_login_e_acessar_pad(driver) # Loga de novo e zera o cronômetro!
                
                identificador = str(row['identificador_unico']).strip()
                codigo = str(row['codigo_instrumento']).strip()
                
                # Ignora lixo
                if not codigo or codigo.lower() in ['nan', 'n/a', 'vazio']:
                    continue

                logging.info(f"[{uf}] Processando {index+1}/{total_linhas}: ID {identificador} - Cód {codigo}")

                try:
                    wait = WebDriverWait(driver, 10)
                    
                    # 1. Digita o código da obra na caixa
                    campo_input = wait.until(EC.presence_of_element_located((By.ID, "formRelatorioItensDespesasPAD:idInstrumento")))
                    campo_input.clear()
                    campo_input.send_keys(codigo)
                    
                    # 2. Aperta o botão de Gerar Relatório
                    botao_gerar = driver.find_element(By.ID, "formRelatorioItensDespesasPAD:_idJsp89")
                    botao_gerar.click()
                    
                    # 3. Verifica o famigerado Erro "Layer3" (Aquela caixinha de aviso do site)
                    try:
                        # O robô olha rápido (2s) pra ver se a mensagem de erro pulou na tela
                        erro_layer = WebDriverWait(driver, 2).until(
                            EC.visibility_of_element_located((By.ID, "Layer3"))
                        )
                        if erro_layer.is_displayed(): # Se a caixa de erro apareceu
                            logging.warning(f"[{uf}] Erro detectado para código {codigo}. Atualizando página...")
                            driver.refresh() # Dá F5 para limpar o erro
                            # Espera o site carregar de novo
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.ID, "formRelatorioItensDespesasPAD:idInstrumento"))
                            )
                            continue # Abandona esse código e vai pro próximo da planilha
                    except:
                        pass # Se passou de 2s e o erro não apareceu, é porque o relatório gerou sucesso! Segue o baile.

                    # 4. Pausa fixa para dar tempo de o servidor do governo empurrar o download pro Chrome
                    time.sleep(5) 
                    
                    # 5. Manda a função ir lá na pasta do Windows pegar o arquivo que caiu e trocar o nome dele
                    nome_final = f"PAD-{identificador}-{codigo}"
                    sucesso = renomear_ultimo_arquivo(pasta_destino_uf, nome_final)
                    
                    if not sucesso:
                        logging.warning(f"[{uf}] Arquivo não baixado ou erro ao renomear para {codigo}")

                except Exception as e_item: # Se der bug extremo na navegação de um item específico
                    logging.error(f"Erro no item {codigo}: {e_item}")
                    try:
                        driver.get(URL_PAD_DIRETA) # Tenta forçar a voltar pra página limpa do PAD
                    except:
                        pass

        except Exception as e_csv:
            logging.error(f"Erro ao processar arquivo {nome_arquivo}: {e_csv}")
        
        finally:
            driver.quit() # Fecha o navegador daquela UF
            logging.info(f"Finalizado estado {uf}")
            time.sleep(2) # Respira e vai pro próximo CSV (próximo Estado)

    logging.info("Processo Completo!")

if __name__ == "__main__":
    processar_estados()