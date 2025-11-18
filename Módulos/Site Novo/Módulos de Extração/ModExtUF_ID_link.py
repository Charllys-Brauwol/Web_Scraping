import time
import sys
import requests
import logging
import os
import glob
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import random
import csv
from urllib.parse import urlparse, parse_qs 

# --- Configuração de Log ---
# Data atual para usar no log e nos arquivos CSV
data_atual = datetime.now().strftime("%Y-%m-%d")
log_filename = f"erros_extracao_POR_ESTADO_V10.{data_atual}.log"

# Limpa handlers antigos
logger = logging.getLogger()
if logger.hasHandlers():
    logger.handlers.clear()

file_handler = logging.FileHandler(log_filename, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

logger.setLevel(logging.INFO)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Ocorreu um erro não tratado:", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception

def verificar_conexao_internet(url="http://www.google.com", timeout=5):
    try:
        requests.head(url, timeout=timeout)
        return True
    except (requests.ConnectionError, requests.Timeout, Exception):
        return False

# --- CAMINHOS ---
DIRETORIO_BASE_DOWNLOADS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtUFID"
DIRETORIO_SAIDA_FINAL = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtraUFIDLINK"
ARQUIVO_ESTADOS = r"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\estados.txt"

URL_SERPRO = "https://dd-publico.serpro.gov.br/extensions/cipi/cipi.html"
LINK_SELECTOR = "a[ng-switch-when='url']"
FILTRO_ID_UNICO_XPATH = "//h6[text()='Identificador Único']"
FILTRO_UF_XPATH = "//h6[text()='UF ( Localização)']"
COLUNA_ALVO_IDS = "Identificador Único"


# --- [INÍCIO] Funções de Leitura de Arquivos ---
def encontrar_arquivos_por_estado(diretorio_base, estado):
    diretorio_estado = os.path.join(diretorio_base, estado)
    padrao_csv = os.path.join(diretorio_estado, "*.csv")
    padrao_xlsx = os.path.join(diretorio_estado, "*.xlsx")
    arquivos_csv = glob.glob(padrao_csv)
    arquivos_xlsx = glob.glob(padrao_xlsx)
    logging.info(f"[LEITURA {estado}] Encontrados {len(arquivos_csv)} CSVs e {len(arquivos_xlsx)} XLSXs.")
    return arquivos_csv + arquivos_xlsx

def ler_arquivo(filepath, estado):
    ids_encontrados = []
    try:
        if filepath.endswith('.csv'):
            try:
                df = pd.read_csv(filepath, sep=';', low_memory=False)
                if COLUNA_ALVO_IDS not in df.columns:
                    df = pd.read_csv(filepath, sep=',', low_memory=False)
            except Exception:
                df = pd.read_csv(filepath, low_memory=False)
        elif filepath.endswith('.xlsx'):
            df = pd.read_excel(filepath)
        else:
            return []
        if COLUNA_ALVO_IDS in df.columns:
            ids = df[COLUNA_ALVO_IDS].dropna().astype(str).unique().tolist()
            ids_encontrados.extend(ids)
        else:
            logging.warning(f"[LEITURA {estado}] Coluna '{COLUNA_ALVO_IDS}' não encontrada em {filepath}")
    except Exception as e:
        logging.error(f"[LEITURA {estado}] Erro ao processar o arquivo {filepath}: {e}")
    return ids_encontrados

def carregar_ids_por_estado(estado, diretorio_base):
    logging.info(f"--- Iniciando Leitura de Arquivos Locais para: {estado} ---")
    todos_arquivos = encontrar_arquivos_por_estado(diretorio_base, estado)
    if not todos_arquivos:
        logging.error(f"Nenhum arquivo CSV ou XLSX encontrado para {estado}")
        return []
    conjunto_ids_estado = set()
    for f in todos_arquivos:
        ids_do_arquivo = ler_arquivo(f, estado)
        conjunto_ids_estado.update(ids_do_arquivo)
    if conjunto_ids_estado:
        logging.info(f"--- Leitura {estado} Concluída: {len(conjunto_ids_estado)} IDs únicos encontrados. ---")
        return list(conjunto_ids_estado)
    else:
        logging.error(f"Nenhum Identificador Único foi extraído dos arquivos de {estado}.")
        return []
# --- [FIM] Funções de Leitura de Arquivos ---


# --- [INÍCIO] Funções de Extração (Selenium) ---
def get_batches(lista_ids, tamanho_lote=10):
    for i in range(0, len(lista_ids), tamanho_lote):
        yield lista_ids[i:i + tamanho_lote]

def save_data_to_csv(data_list, filepath):
    file_exists = os.path.isfile(filepath)
    try:
        with open(filepath, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            if not file_exists:
                writer.writerow(['identificador_unico', 'id_proposta', 'link_completo'])
            writer.writerows(data_list)
        logging.info(f"   -> SUCESSO: {len(data_list)} registros salvos em {filepath}")
    except Exception as e:
        logger.error(f"Erro ao salvar CSV: {e}")

def aplicar_filtro_estado(driver, estado, log_prefix):
    try:
        logging.info(f"{log_prefix} Aplicando filtro principal de Estado: {estado}")
        estado_click = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, FILTRO_UF_XPATH))
        )
        estado_click.click()
        logging.info(f"{log_prefix} 1/3: Filtro 'UF ( Localização)' selecionado.")
        
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
        )
        search_input.send_keys(estado)
        search_input.send_keys(Keys.ENTER)
        time.sleep(random.uniform(1, 2)) 
        
        confirm_button = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
        )
        confirm_button.click()
        logging.info(f"{log_prefix} 2/3: Estado {estado} filtrado com sucesso.")

        logging.info(f"{log_prefix} 3/3: Aguardando tabela principal atualizar com dados de {estado}...")
        time.sleep(random.uniform(3, 5)) 
        return True
    except Exception as e:
        logger.error(f"{log_prefix} FALHA ao aplicar o filtro de ESTADO (UF) para {estado}: {e}")
        return False


def aplicar_filtro_lote_CORRIGIDO(driver, lote_ids, log_prefix):
    logging.info(f"{log_prefix} 1/6: Clicando em 'Filtros Adicionais'...")
    filtros_adicionais = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//span[text()='Filtros Adicionais']"))
    )
    filtros_adicionais.click()

    logging.info(f"{log_prefix} 2/6: Clicando em 'Identificador Único'...")
    n_instrumento_click = WebDriverWait(driver, 15).until( 
        EC.element_to_be_clickable((By.XPATH, FILTRO_ID_UNICO_XPATH))
    )
    n_instrumento_click.click()
    
    logging.info(f"{log_prefix} 3/6: Limpando seleções anteriores...")
    try:
        limpar_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='actions-toolbar-clear']"))
        )
        limpar_btn.click()
        logging.info(f"{log_prefix}    -> Seleção anterior limpa.")
        time.sleep(random.uniform(0.5, 1))
    except Exception:
        logging.info(f"{log_prefix}    -> Nenhuma seleção anterior para limpar.")

    logging.info(f"{log_prefix} 4/6: Inserindo {len(lote_ids)} IDs no filtro (em lote, com espaço)...")
    search_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']"))
    )
    
    texto_lote = " ".join(lote_ids)
    search_input.send_keys(texto_lote)
    search_input.send_keys(Keys.ENTER)
    
    logging.info(f"{log_prefix}    -> Lote de IDs colado com espaço e 'Enter' pressionado.")
    time.sleep(random.uniform(1, 2))
    
    logging.info(f"{log_prefix} 5/6: Clicando em 'Confirmar seleção' (Checkmark)...")
    confirm_selection_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
    )
    confirm_selection_button.click()
    time.sleep(random.uniform(1, 2)) 
    
    logging.info(f"{log_prefix} 6/6: Fechando modal de filtros...")
    close_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-dismiss='modal'][style*='background-color: #294B89']"))
    )
    close_button.click()
    
    logging.info(f"{log_prefix} Aguardando tabela principal atualizar...")
    time.sleep(random.uniform(2, 4)) 

def extract_batch_data(driver, link_selector, log_prefix):
    all_extracted_data = []
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, link_selector))
        )
        time.sleep(2) 
        
        links = driver.find_elements(By.CSS_SELECTOR, link_selector)
        
        if not links:
            logging.warning(f"{log_prefix} AVISO: Filtro aplicado, mas nenhum link encontrado na tabela.")
            return []
        
        logging.info(f"{log_prefix} Extraindo {len(links)} links da tabela...")
        for link_element in links:
            try:
                id_unico_texto = link_element.text.strip()
                full_url_with_params = link_element.get_attribute('title')
                
                if id_unico_texto and full_url_with_params:
                    parsed_url = urlparse(full_url_with_params)
                    query_params = parse_qs(parsed_url.query)
                    id_proposta = query_params.get('idProposta', ['N/A'])[0]
                    all_extracted_data.append((id_unico_texto, id_proposta, full_url_with_params))
            except Exception as e_inner:
                logger.warning(f"{log_prefix} Falha ao processar um link individual: {e_inner}")
                continue
                
    except Exception as e_outer:
        logging.warning(f"{log_prefix} Nenhum dado encontrado (Timeout de espera): {e_outer}")
    
    return all_extracted_data
# --- [FIM] Funções de Extração (Selenium) ---


# --- Processamento Principal ---
def main():
    if not verificar_conexao_internet():
        logger.error("Sem conexão com a internet. O script será encerrado.")
        sys.exit(1)

    os.makedirs(DIRETORIO_SAIDA_FINAL, exist_ok=True)
    logging.info(f"Diretório de saída configurado: {DIRETORIO_SAIDA_FINAL}")

    try:
        with open(ARQUIVO_ESTADOS, "r", encoding="utf-8") as file:
            linhas_estados = [line.strip() for line in file if line.strip()]
        if not linhas_estados:
            raise ValueError("Arquivo de estados está vazio.")
        logging.info(f"Arquivo 'estados.txt' lido. {len(linhas_estados)} estados para processar.")
    except FileNotFoundError:
        logger.error(f"O arquivo 'estados.txt' não foi encontrado em: {ARQUIVO_ESTADOS}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro ao ler 'estados.txt': {e}")
        sys.exit(1)

    
    # 2. Loop principal POR ESTADO
    for estado in linhas_estados:
        log_prefix_estado = f"[{estado}]"
        logging.info(f"\n=======================================================")
        logging.info(f"=== INICIANDO PROCESSAMENTO COMPLETO PARA: {estado} ===")
        logging.info(f"=======================================================")
        
        # *** ALTERAÇÃO AQUI ***
        # Adiciona a data_atual (ex: 2023-10-27) ao nome do arquivo
        nome_arquivo_estado = f"links_extraidos_{estado}_{data_atual}.csv"
        caminho_saida_estado = os.path.join(DIRETORIO_SAIDA_FINAL, nome_arquivo_estado)
        logging.info(f"Arquivo de saída DIÁRIO para este estado: {caminho_saida_estado}")
        
        # --- ETAPA 1 (por estado): LEITURA DOS ARQUIVOS ---
        lista_ids_estado = carregar_ids_por_estado(estado, DIRETORIO_BASE_DOWNLOADS)
        
        if not lista_ids_estado:
            logging.warning(f"{log_prefix_estado} Nenhum ID encontrado. Pulando para o próximo estado.")
            continue
            
        lotes = list(get_batches(lista_ids_estado, 10))
        total_lotes = len(lotes)
        
        logging.info(f"--- Iniciando Etapa 2 [WEB]: Extração de {len(lista_ids_estado)} IDs em {total_lotes} lotes para {estado} ---")
        
        driver = None
        try:
            # --- ETAPA 2 (por estado): CONFIGURAÇÃO DO SELENIUM ---
            chrome_options = Options()
            # chrome_options.add_argument("--headless")
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(URL_SERPRO)

            logging.info(f"{log_prefix_estado} Aguardando carregamento inicial da página...")
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, FILTRO_UF_XPATH))
            )
            time.sleep(5)
            logging.info(f"{log_prefix_estado} Página carregada.")

            # --- ETAPA 3 (por estado): APLICAR FILTRO DE ESTADO ---
            if not aplicar_filtro_estado(driver, estado, log_prefix_estado):
                logging.error(f"{log_prefix_estado} Falha crítica ao filtrar estado. Pulando para o próximo.")
                continue

            # --- ETAPA 4 (por estado): LOOP PELOS LOTES ---
            for i, lote_atual in enumerate(lotes, 1):
                log_prefix_lote = f"[{estado} - Lote {i}/{total_lotes}]"
                logging.info(f"\n{log_prefix_lote} --- Processando {len(lote_atual)} IDs ---")
                
                try:
                    aplicar_filtro_lote_CORRIGIDO(driver, lote_atual, log_prefix_lote)
                    dados_extraidos = extract_batch_data(driver, LINK_SELECTOR, log_prefix_lote)
                    
                    if dados_extraidos:
                        save_data_to_csv(dados_extraidos, caminho_saida_estado)
                    else:
                        logging.warning(f"{log_prefix_lote} Nenhum dado extraído para este lote.")
                        logger.warning(f"IDs do lote {i} ({estado}) sem dados: {lote_atual}")

                except Exception as e_lote:
                    logger.error(f"{log_prefix_lote} Erro fatal no processamento do lote: {e_lote}")
                    logging.info(f"{log_prefix_lote} TENTATIVA DE RECUPERAÇÃO: Recarregando página...")
                    
                    try:
                        driver.get(URL_SERPRO)
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.XPATH, FILTRO_UF_XPATH))
                        )
                        time.sleep(5)
                        
                        if not aplicar_filtro_estado(driver, estado, log_prefix_estado):
                             logging.error(f"{log_prefix_estado} Falha ao RE-filtrar estado. Abortando estado.")
                             break 
                        
                        logging.info(f"{log_prefix_estado} Recuperado. Indo para o próximo lote...")
                        continue 

                    except Exception as e_recup:
                        logging.error(f"{log_prefix_estado} Falha na recuperação: {e_recup}. Abortando estado.")
                        break

        except Exception as e_main:
            logger.error(f"{log_prefix_estado} Erro inesperado no processo principal do Selenium: {str(e_main)}")
        finally:
            if driver:
                driver.quit()
                logging.info(f"{log_prefix_estado} Navegador fechado.")
        
        logging.info(f"=== PROCESSAMENTO {estado} CONCLUÍDO ===")
        time.sleep(random.uniform(5, 10)) 

    logging.info(f"\nProcessamento de TODOS OS ESTADOS concluído. 🎉")

if __name__ == "__main__":
    main()