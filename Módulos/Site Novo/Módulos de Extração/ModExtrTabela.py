import time
import sys
import os
import glob
import shutil
import pandas as pd
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import random

# --- Configuração de Log ---
data_atual = datetime.now().strftime("%Y-%m-%d")
log_filename = f"log_download_PAD_CODIGOS_{data_atual}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# --- CAMINHOS ---
DIRETORIO_ENTRADA_CSVS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtraUFID_CODIGOS"
DIRETORIO_SAIDA_BASE = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ExtPAD"

# URLs
URL_LOGIN_GOV = "https://www.gov.br/transferegov/pt-br/sistemas/acesso-livre"
URL_PAD_DIRETA = "https://discricionarias.transferegov.sistema.gov.br/voluntarias/_gerencial/RelatorioItensDespesasPAD/relatorioItensDespesasPAD.jsf"

# Tempo máximo de sessão em segundos (20 minutos = 1200 segundos)
TEMPO_SESSAO_LIMITE = 1200 

def configurar_driver(pasta_download):
    """Configura o driver com a pasta de download específica da UF."""
    chrome_options = Options()
    prefs = {
        "download.default_directory": pasta_download,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    return driver

def fazer_login_e_acessar_pad(driver):
    """Realiza o fluxo de login e navega para a URL do PAD."""
    wait = WebDriverWait(driver, 30)
    
    logging.info("Iniciando fluxo de autenticação...")
    driver.get(URL_LOGIN_GOV)
    
    # Aceitar cookies (se houver) para evitar bloqueio de clique
    try:
        botao_cookie = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.br-button.btn-accept")))
        botao_cookie.click()
        time.sleep(1)
    except:
        pass

    # Clicar em "Consultar Pré-Instrumentos/Instrumentos"
    link_consultar = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Consultar Pré-Instrumentos/Instrumentos")))
    link_consultar.click()
    
    # Espera a nova aba abrir e troca para ela
    time.sleep(3)
    janelas = driver.window_handles
    driver.switch_to.window(janelas[-1])
    
    logging.info("Aba trocada. Acessando URL direta do PAD...")
    
    # Acessa a URL direta solicitada
    driver.get(URL_PAD_DIRETA)
    
    # Verifica se carregou o input chave
    wait.until(EC.presence_of_element_located((By.ID, "formRelatorioItensDespesasPAD:idInstrumento")))
    logging.info("Página PAD carregada com sucesso.")
    
    return time.time() # Retorna a hora que a sessão começou

def renomear_ultimo_arquivo(pasta_download, novo_nome_base):
    """
    Espera o download terminar, pega o arquivo mais recente e renomeia.
    novo_nome_base: Ex: PAD42830.12-20902286
    """
    # Espera até que não haja arquivos .crdownload (download em andamento)
    tempo_espera = 0
    while tempo_espera < 30:
        arquivos_temp = glob.glob(os.path.join(pasta_download, "*.crdownload"))
        if not arquivos_temp:
            break
        time.sleep(1)
        tempo_espera += 1

    # Pega todos os arquivos na pasta
    arquivos = glob.glob(os.path.join(pasta_download, "*"))
    # Remove pastas da lista, deixa só arquivos
    arquivos = [f for f in arquivos if os.path.isfile(f)]
    
    if not arquivos:
        return False

    # Pega o arquivo mais recente (por data de modificação)
    arquivo_mais_recente = max(arquivos, key=os.path.getmtime)
    
    # Pega a extensão do arquivo baixado (.xls, .csv, etc)
    extensao = os.path.splitext(arquivo_mais_recente)[1]
    
    novo_caminho = os.path.join(pasta_download, f"{novo_nome_base}{extensao}")
    
    # Se já existir um arquivo com esse nome, remove para substituir
    if os.path.exists(novo_caminho):
        try:
            os.remove(novo_caminho)
        except:
            pass

    try:
        os.rename(arquivo_mais_recente, novo_caminho)
        logging.info(f"Arquivo renomeado para: {os.path.basename(novo_caminho)}")
        return True
    except Exception as e:
        logging.error(f"Erro ao renomear arquivo: {e}")
        return False

def processar_estados():
    # Localiza os CSVs de entrada
    padrao_busca = os.path.join(DIRETORIO_ENTRADA_CSVS, "*.csv")
    arquivos_csv = glob.glob(padrao_busca)
    
    if not arquivos_csv:
        logging.error("Nenhum arquivo de códigos encontrado.")
        sys.exit()

    for arquivo_csv in arquivos_csv:
        # Extrai a UF do nome do arquivo (ex: codigos_instrumento_links_extraidos_AC.csv)
        nome_arquivo = os.path.basename(arquivo_csv)
        try:
            # Tenta pegar a UF (parte com 2 letras maiúsculas)
            parts = nome_arquivo.replace('.csv', '').split('_')
            uf = next(p for p in parts if len(p) == 2 and p.isupper())
        except:
            uf = "DESCONHECIDO"
        
        # Define pasta de saída para esta UF
        pasta_destino_uf = os.path.join(DIRETORIO_SAIDA_BASE, uf)
        os.makedirs(pasta_destino_uf, exist_ok=True)
        
        logging.info(f"--- Iniciando processamento da UF: {uf} ---")
        
        # Inicia Driver para esta UF
        driver = configurar_driver(pasta_destino_uf)
        inicio_sessao = fazer_login_e_acessar_pad(driver)
        
        try:
            # Lê o CSV
            df = pd.read_csv(arquivo_csv, sep=';', encoding='utf-8-sig', dtype=str)
            
            total_linhas = len(df)
            
            for index, row in df.iterrows():
                # Verifica tempo de sessão
                tempo_decorrido = time.time() - inicio_sessao
                if tempo_decorrido > TEMPO_SESSAO_LIMITE:
                    logging.warning("Tempo de sessão (20min) expirado. Reiniciando navegador...")
                    driver.quit()
                    driver = configurar_driver(pasta_destino_uf)
                    inicio_sessao = fazer_login_e_acessar_pad(driver)
                
                identificador = str(row['identificador_unico']).strip()
                codigo = str(row['codigo_instrumento']).strip()
                
                # Pula se o código estiver vazio ou inválido
                if not codigo or codigo.lower() in ['nan', 'n/a', 'vazio']:
                    continue

                logging.info(f"[{uf}] Processando {index+1}/{total_linhas}: ID {identificador} - Cód {codigo}")

                try:
                    wait = WebDriverWait(driver, 10)
                    
                    # 1. Digita o código no campo
                    campo_input = wait.until(EC.presence_of_element_located((By.ID, "formRelatorioItensDespesasPAD:idInstrumento")))
                    campo_input.clear()
                    campo_input.send_keys(codigo)
                    
                    # 2. Clica em Gerar
                    botao_gerar = driver.find_element(By.ID, "formRelatorioItensDespesasPAD:_idJsp89")
                    botao_gerar.click()
                    
                    # 3. Verifica Erro "Layer3" (Espera curta)
                    try:
                        # Espera 2 segundos para ver se o erro aparece
                        erro_layer = WebDriverWait(driver, 2).until(
                            EC.visibility_of_element_located((By.ID, "Layer3"))
                        )
                        if erro_layer.is_displayed():
                            logging.warning(f"[{uf}] Erro detectado para código {codigo}. Atualizando página...")
                            driver.refresh()
                            # Espera o input voltar
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.ID, "formRelatorioItensDespesasPAD:idInstrumento"))
                            )
                            continue # Pula para o próximo
                    except:
                        pass # Se não deu erro, segue o jogo

                    # 4. Se não deu erro, espera o download
                    # Não há um indicador visual de download fácil, então usamos tempo + verificação de pasta
                    time.sleep(5) 
                    
                    # 5. Renomeia o arquivo
                    nome_final = f"PAD-{identificador}-{codigo}"
                    sucesso = renomear_ultimo_arquivo(pasta_destino_uf, nome_final)
                    
                    if not sucesso:
                        logging.warning(f"[{uf}] Arquivo não baixado ou erro ao renomear para {codigo}")

                except Exception as e_item:
                    logging.error(f"Erro no item {codigo}: {e_item}")
                    # Tenta recuperar a página em caso de erro critico
                    try:
                        driver.get(URL_PAD_DIRETA)
                    except:
                        pass

        except Exception as e_csv:
            logging.error(f"Erro ao processar arquivo {nome_arquivo}: {e_csv}")
        
        finally:
            driver.quit()
            logging.info(f"Finalizado estado {uf}")
            time.sleep(2)

    logging.info("Processo Completo!")

if __name__ == "__main__":
    processar_estados()