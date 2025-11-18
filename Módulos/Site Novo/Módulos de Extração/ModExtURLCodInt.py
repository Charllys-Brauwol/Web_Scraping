import time
import sys
import os
import glob
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
log_filename = f"log_download_PDA_OTIMIZADO_{data_atual}.log"

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


# --- CAMINHOS ---
DIRETORIO_ENTRADA_CSVS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtraUFIDLINK"
DIRETORIO_SAIDA_BASE = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtraUFIDLINK\PDA"

URL_INICIAL = "https://idp.transferegov.sistema.gov.br/idp/"

def iniciar_driver():
    """Inicia o navegador UMA ÚNICA VEZ."""
    chrome_options = Options()
    prefs = {
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True 
    }
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window() 
    return driver

def mudar_pasta_download(driver, nova_pasta):
    """
    Mágica para mudar a pasta de download sem fechar o navegador.
    Usa o Chrome DevTools Protocol (CDP).
    """
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": nova_pasta
    })
    logging.info(f"Pasta de download alterada dinamicamente para: {nova_pasta}")

def limpar_id_proposta(valor):
    """Remove '.0' e garante que seja apenas dígitos."""
    s = str(valor).strip()
    if s.endswith('.0'):
        s = s[:-2] # Remove o .0 final
    return s

def garantir_acesso_relatorio(driver):
    """
    Verifica se já estamos na página do relatório. 
    Se não, faz todo o caminho de navegação.
    """
    wait = WebDriverWait(driver, 10)
    
    # Tenta encontrar o campo de input do relatório para ver se já estamos lá
    try:
        driver.find_element(By.ID, "formRelatorioItensDespesasPAD:idInstrumento")
        logging.info("Já estamos na página do Relatório PAD. Continuando...")
        return # Já estamos na página certa
    except:
        logging.info("Não estamos na página do relatório. Iniciando navegação completa...")

    # SE NÃO ESTIVER NA PÁGINA, FAZ O CAMINHO:
    wait_nav = WebDriverWait(driver, 30)

    # 1. Acessar link inicial
    driver.get(URL_INICIAL)
    time.sleep(random.uniform(3, 4))

    # 2. Clicar em "Acesso livre"
    botao_acesso_livre = wait_nav.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Acesso livre")))
    botao_acesso_livre.click()
    time.sleep(random.uniform(2, 3))

    # Aceitar Cookies (Se houver)
    try:
        wait_cookie = WebDriverWait(driver, 5)
        botao_cookie = wait_cookie.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-accept")))
        botao_cookie.click()
        time.sleep(1)
    except Exception:
        pass

    # 3. Consultar Pré-Instrumentos (Abre nova aba)
    botao_consultar = wait_nav.until(EC.element_to_be_clickable((By.LINK_TEXT, "Consultar Pré-Instrumentos/Instrumentos")))
    botao_consultar.click()
    time.sleep(random.uniform(3, 5))

    # Trocar de Aba se necessário
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[-1])
    
    time.sleep(random.uniform(2, 4))

    # 4. Menu Acomp. e Fiscalização
    menu_acomp = wait_nav.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Acomp. e Fiscalização')]")))
    menu_acomp.click()
    time.sleep(random.uniform(1.5, 3))
    
    # 5. Link Relatório PAD
    link_relatorio = wait_nav.until(EC.element_to_be_clickable((By.LINK_TEXT, "Relatório de Acompanhamento - Itens de Despesas (PAD)")))
    link_relatorio.click()
    
    time.sleep(random.uniform(4, 6))
    logging.info("Página de Relatório PAD carregada.")


def processar_arquivos():
    # 1. Localiza os arquivos CSV
    padrao_busca = os.path.join(DIRETORIO_ENTRADA_CSVS, "*.csv")
    arquivos_csv = glob.glob(padrao_busca)

    if not arquivos_csv:
        logging.error("Nenhum arquivo CSV encontrado.")
        sys.exit()

    logging.info(f"Iniciando sessão única para processar {len(arquivos_csv)} estados.")

    # 2. Inicia o Driver (UMA VEZ SÓ)
    driver = iniciar_driver()
    wait = WebDriverWait(driver, 20)

    try:
        # Navega até a página inicial do relatório
        garantir_acesso_relatorio(driver)

        # 3. Loop pelos Arquivos (Estados)
        for arquivo in arquivos_csv:
            nome_arquivo = os.path.basename(arquivo)
            
            # Identifica a UF
            try:
                parts = nome_arquivo.split('_')
                uf = next(p for p in parts if len(p) == 2 and p.isupper())
            except:
                uf = "DESCONHECIDO"
            
            # Define pasta de destino
            pasta_destino = os.path.join(DIRETORIO_SAIDA_BASE, uf)
            os.makedirs(pasta_destino, exist_ok=True)
            
            # --- MUDANÇA DINÂMICA DE PASTA ---
            mudar_pasta_download(driver, pasta_destino)
            # ---------------------------------

            logging.info(f"--- Processando UF: {uf} ---")

            # Lê e limpa o CSV
            try:
                df = pd.read_csv(arquivo, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
            except:
                try:
                    df = pd.read_csv(arquivo, sep=';', encoding='latin1', on_bad_lines='skip')
                except:
                    logging.error(f"Erro ao ler {nome_arquivo}")
                    continue

            # Filtra IDs inválidos
            df['id_proposta'] = df['id_proposta'].astype(str)
            ids_validos = df[
                (~df['id_proposta'].isin(['N/A', 'nan', 'NÃO', 'NAO'])) & 
                (df['id_proposta'].str.strip() != '')
            ]['id_proposta'].unique()

            total_ids = len(ids_validos)
            if total_ids == 0:
                logging.warning(f"[{uf}] Nenhum ID válido.")
                continue

            # Loop pelos IDs do Estado atual
            for i, id_bruto in enumerate(ids_validos, 1):
                # Limpeza crítica do ID (remove o .0)
                id_instrumento = limpar_id_proposta(id_bruto)

                try:
                    logging.info(f"[{uf}] {i}/{total_ids} - ID: {id_instrumento}")

                    # Verifica se ainda estamos na página certa, se não, reconecta
                    try:
                        campo_input = wait.until(EC.presence_of_element_located((By.ID, "formRelatorioItensDespesasPAD:idInstrumento")))
                    except:
                        logging.warning("Sessão pode ter caído ou página mudou. Navegando novamente...")
                        garantir_acesso_relatorio(driver)
                        mudar_pasta_download(driver, pasta_destino) # Reafirma a pasta após recarregar
                        campo_input = wait.until(EC.presence_of_element_located((By.ID, "formRelatorioItensDespesasPAD:idInstrumento")))

                    campo_input.clear()
                    # Pausa curta
                    time.sleep(0.5)
                    
                    # Digita o ID limpo
                    campo_input.send_keys(id_instrumento)
                    time.sleep(1) 

                    # Clica em Gerar
                    try:
                        botao_gerar = driver.find_element(By.CSS_SELECTOR, "input[value='Gerar novo relatório para exportação']")
                    except:
                        botao_gerar = driver.find_element(By.ID, "formRelatorioItensDespesasPAD:_idJsp89")
                    
                    botao_gerar.click()
                    
                    # Espera o download (pode ajustar esse tempo)
                    time.sleep(random.uniform(5, 7))

                    # Aceita alertas se aparecerem
                    try:
                        alert = driver.switch_to.alert
                        logging.warning(f"[{uf}] Alerta: {alert.text}")
                        alert.accept()
                        time.sleep(1)
                    except:
                        pass

                except Exception as e:
                    logging.error(f"[{uf}] Erro no ID {id_instrumento}: {e}")
                    # Tenta dar um refresh na página para limpar o formulário travado
                    driver.refresh()
                    time.sleep(3)

            logging.info(f"Finalizado estado {uf}. Continuando para o próximo...")
            time.sleep(2)

    except Exception as e_critico:
        logging.error(f"Erro crítico geral: {e_critico}")

    finally:
        driver.quit()
        logging.info("Navegador fechado. Fim do processo.")

if __name__ == "__main__":
    processar_arquivos()