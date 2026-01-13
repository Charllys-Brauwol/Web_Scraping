import time
import sys
import logging
import os
import glob
import pandas as pd
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import random
from urllib.parse import urlparse, parse_qs 

# --- CONFIGURAÇÕES ---
data_atual = datetime.now().strftime("%Y-%m-%d")
log_filename = f"log_repescagem_V6_{data_atual}.log"

logger = logging.getLogger()
if logger.hasHandlers():
    logger.handlers.clear()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - REPESCAGEM - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# --- CAMINHOS ---
DIRETORIO_BASE_ORIGEM = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtUFID" 
DIRETORIO_SAIDA_LINKS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtraUFIDLINK"
ARQUIVO_ESTADOS = r"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\estados.txt"

URL_SERPRO = "https://dd-publico.serpro.gov.br/extensions/cipi/cipi.html"
LINK_SELECTOR = "a[ng-switch-when='url']"

# NOMES DAS COLUNAS
COLUNA_ORIGEM = "Identificador Único"
COLUNA_DESTINO = "identificador_unico"

# ==============================================================================
# 1. FUNÇÕES DE LEITURA
# ==============================================================================

def pegar_arquivos_recentes(diretorio, padrao="*", qtd=2):
    caminho_busca = os.path.join(diretorio, padrao)
    arquivos = glob.glob(caminho_busca)
    if not arquivos: return []
    arquivos.sort(key=os.path.getmtime, reverse=True)
    return arquivos[:qtd]

def ler_ids_origem(lista_arquivos):
    ids_encontrados = set()
    for arquivo in lista_arquivos:
        try:
            if arquivo.endswith('.xlsx'):
                df = pd.read_excel(arquivo)
            else:
                try: df = pd.read_csv(arquivo, sep=';', low_memory=False, dtype=str)
                except: df = pd.read_csv(arquivo, sep=',', low_memory=False, dtype=str)
            
            if COLUNA_ORIGEM in df.columns:
                # Remove espaços para garantir que ' 123 ' vire '123'
                lista = df[COLUNA_ORIGEM].dropna().astype(str).str.strip().tolist()
                ids_encontrados.update(lista)
        except Exception as e:
            logging.error(f"   [ORIGEM] Erro ao ler {os.path.basename(arquivo)}: {e}")
    return ids_encontrados

def ler_ids_destino(lista_arquivos):
    ids_encontrados = set()
    for arquivo in lista_arquivos:
        try:
            # Lê tudo como string
            df = pd.read_csv(arquivo, sep=';', low_memory=False, dtype=str)
            
            if COLUNA_DESTINO in df.columns:
                # TRUQUE DE LIMPEZA: Remove linhas onde o ID é SIM, NÃO, N/A
                # Isso garante que a contagem de "Já Baixados" ignore o lixo
                df_limpo = df[~df[COLUNA_DESTINO].str.contains('SIM|NÃO|NAO|NAN|N/A', case=False, na=False)]
                
                lista = df_limpo[COLUNA_DESTINO].dropna().astype(str).str.strip().tolist()
                ids_encontrados.update(lista)
        except Exception as e:
            logging.warning(f"   [DESTINO] Ignorando {os.path.basename(arquivo)}: {e}")
    return ids_encontrados

def calcular_delta_estado(estado):
    logging.info(f"--- Calculando Delta para {estado} ---")
    
    dir_estado_origem = os.path.join(DIRETORIO_BASE_ORIGEM, estado)
    
    # 1. Origem (O que eu quero)
    arquivos_origem = pegar_arquivos_recentes(dir_estado_origem, "*.csv", 2) + \
                      pegar_arquivos_recentes(dir_estado_origem, "*.xlsx", 2)
    ids_total_origem = ler_ids_origem(arquivos_origem)
    
    # 2. Destino (O que eu já tenho)
    padrao_saida = f"links_extraidos_{estado}_*.csv"
    # Pega até 5 arquivos recentes para garantir que leu tudo que foi feito
    arquivos_saida = pegar_arquivos_recentes(DIRETORIO_SAIDA_LINKS, padrao_saida, 5)
    ids_ja_baixados = ler_ids_destino(arquivos_saida)
    
    # 3. Definição do Arquivo para SALVAR (O mais recente de todos)
    if arquivos_saida:
        # Pega o arquivo MAIS NOVO existente para fazer APPEND nele
        arquivo_destino = arquivos_saida[0]
        logging.info(f"   -> Append será feito no arquivo existente: {os.path.basename(arquivo_destino)}")
    else:
        # Se não existe nenhum, cria um novo
        arquivo_destino = os.path.join(DIRETORIO_SAIDA_LINKS, f"links_extraidos_{estado}_{data_atual}.csv")
        logging.info(f"   -> Nenhum arquivo anterior encontrado. Criando novo: {os.path.basename(arquivo_destino)}")
    
    # 4. Cálculo
    faltantes = list(ids_total_origem - ids_ja_baixados)
    
    logging.info(f"[{estado}] Total Origem: {len(ids_total_origem)} | Já Baixados: {len(ids_ja_baixados)} | FALTAM: {len(faltantes)}")
    
    return faltantes, arquivo_destino

# ==============================================================================
# 2. AUTOMAÇÃO WEB
# ==============================================================================

def configurar_driver():
    opts = Options()
    opts.add_argument("--ignore-certificate-errors"); opts.add_argument("--ignore-ssl-errors")
    opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
    opts.add_experimental_option("prefs", {"download.prompt_for_download": False, "safeBrowse.enabled": True})
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    s = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=s, options=opts)

def aplicar_filtro_lote(driver, lote_ids):
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Filtros Adicionais']"))).click()
    WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//h6[text()='Identificador Único']"))).click()
    try: WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='actions-toolbar-clear']"))).click()
    except: pass

    inp = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']")))
    # Limpa IDs antes de digitar
    ids_limpos = [i.strip() for i in lote_ids]
    inp.send_keys(" ".join(ids_limpos))
    inp.send_keys(Keys.ENTER)
    time.sleep(1)
    
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))).click()
    time.sleep(1)
    try:
        btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-dismiss='modal'][style*='background-color: #294B89']")))
        driver.execute_script("arguments[0].click();", btn)
    except: webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    time.sleep(4)

def extrair_links(driver, lote_ids):
    links_data = []
    # Cria lista limpa para comparação
    lote_ids_limpo = [str(i).strip() for i in lote_ids]
    
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, LINK_SELECTOR)))
        els = driver.find_elements(By.CSS_SELECTOR, LINK_SELECTOR)
        
        for el in els:
            try:
                txt_id_site = el.text.strip()
                
                # Se o ID do site bater com o que pedimos
                if txt_id_site in lote_ids_limpo:
                    url = el.get_attribute('title')
                    if url:
                        parsed = urlparse(url)
                        id_prop = parse_qs(parsed.query).get('idProposta', ['N/A'])[0]
                        
                        # FILTRO FINAL: Só salva se não for N/A (elimina o lixo SIM/NÃO)
                        if id_prop and id_prop not in ['N/A', '', 'None']:
                            links_data.append((txt_id_site, id_prop, url))
            except: continue
    except: pass
    return links_data

def salvar_append(dados, filepath):
    existe = os.path.exists(filepath)
    try:
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            if not existe:
                writer.writerow(['identificador_unico', 'id_proposta', 'link_completo'])
            writer.writerows(dados)
        logging.info(f"      -> SUCESSO: +{len(dados)} novos registros adicionados em {os.path.basename(filepath)}")
    except Exception as e:
        logging.error(f"Erro ao salvar: {e}")

# ==============================================================================
# 3. PRINCIPAL
# ==============================================================================

def main():
    print("--- REPESCAGEM V6 (SALVANDO NO MESMO ARQUIVO) ---")
    
    try:
        with open(ARQUIVO_ESTADOS, "r", encoding="utf-8") as f:
            estados = [l.strip() for l in f if l.strip()]
    except: sys.exit(1)

    for estado in estados:
        logging.info(f"\n>>> ESTADO: {estado}")
        
        # 1. Calcula usando arquivo existente e ignora lixo
        ids_faltantes, arquivo_destino = calcular_delta_estado(estado)
        
        if not ids_faltantes:
            logging.info(f"[{estado}] Nada pendente.")
            continue
            
        logging.info(f"[{estado}] Buscando {len(ids_faltantes)} IDs...")

        driver = configurar_driver()
        try:
            driver.get(URL_SERPRO)
            time.sleep(8)
            
            # Filtro Estado
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//h6[text()='UF ( Localização)']"))).click()
            inp = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']")))
            inp.send_keys(estado); inp.send_keys(Keys.ENTER); time.sleep(1)
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))).click()
            time.sleep(5)
            
            # Lotes
            lotes = [ids_faltantes[i:i + 10] for i in range(0, len(ids_faltantes), 10)]
            
            for i, lote in enumerate(lotes):
                logging.info(f"[{estado}] Lote {i+1}/{len(lotes)} ({len(lote)} IDs)...")
                try:
                    aplicar_filtro_lote(driver, lote)
                    dados = extrair_links(driver, lote)
                    
                    if dados:
                        # SALVA NO MESMO ARQUIVO DO ESTADO
                        salvar_append(dados, arquivo_destino)
                    else:
                        logging.warning(f"[{estado}] Lote {i+1} sem retorno válido.")
                        
                except Exception as e:
                    logging.error(f"Erro lote {i+1}: {e}")
                    try: driver.refresh(); time.sleep(5); 
                    except: pass
                
                time.sleep(random.uniform(2, 3))
                
        finally:
            driver.quit()
            logging.info(f"[{estado}] Fim.")
            time.sleep(2)

    logging.info("\n=== FIM ===")

if __name__ == "__main__":
    main()