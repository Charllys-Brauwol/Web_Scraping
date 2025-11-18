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
import csv

# --- Configuração de Log ---
data_atual = datetime.now().strftime("%Y-%m-%d")
log_filename = f"log_extracao_CODIGO_INSTRUMENTO_{data_atual}.log"

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
# Onde estão os arquivos com os links (Gerados pelo script anterior)
DIRETORIO_ENTRADA = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtraUFIDLINK"

# Onde vamos salvar os novos arquivos com os códigos extraídos
DIRETORIO_SAIDA = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtraUFID_CODIGOS"

def iniciar_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # Pode usar headless se quiser mais velocidade
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    return driver

def extrair_codigo_instrumento(driver, url):
    """Acessa a URL e busca o Código do Instrumento."""
    try:
        driver.get(url)
        
        # Espera o elemento aparecer (id="tr-alterarNumeroProposta")
        wait = WebDriverWait(driver, 10)
        
        # Estratégia: Procura a TR com o ID específico, depois pega o primeiro TD com classe 'field' dentro dela
        elemento_codigo = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#tr-alterarNumeroProposta td.field"))
        )
        
        # Pega o texto e limpa espaços em branco (o .strip() remove o &nbsp; e quebras de linha)
        codigo_bruto = elemento_codigo.text
        codigo_limpo = codigo_bruto.strip()
        
        if not codigo_limpo:
            return "VAZIO"
            
        return codigo_limpo

    except Exception as e:
        logger.warning(f"Falha ao extrair da URL: {url}. Erro: {str(e).splitlines()[0]}")
        return "ERRO_EXTRACAO"

def processar_arquivos():
    # Cria diretório de saída se não existir
    os.makedirs(DIRETORIO_SAIDA, exist_ok=True)
    
    # Localiza os arquivos CSV de entrada
    padrao_busca = os.path.join(DIRETORIO_ENTRADA, "*.csv")
    arquivos_csv = glob.glob(padrao_busca)

    if not arquivos_csv:
        logging.error("Nenhum arquivo CSV de entrada encontrado.")
        sys.exit()

    logging.info(f"Encontrados {len(arquivos_csv)} arquivos para processar.")

    driver = iniciar_driver()

    try:
        for arquivo_entrada in arquivos_csv:
            nome_arquivo = os.path.basename(arquivo_entrada)
            logging.info(f"--- Processando arquivo: {nome_arquivo} ---")
            
            # Define nome do arquivo de saída (Ex: codigos_extraidos_AC.csv)
            nome_saida = f"codigos_instrumento_{nome_arquivo}"
            caminho_saida = os.path.join(DIRETORIO_SAIDA, nome_saida)

            # Ler o CSV de entrada
            try:
                df = pd.read_csv(arquivo_entrada, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
            except:
                try:
                    df = pd.read_csv(arquivo_entrada, sep=';', encoding='latin1', on_bad_lines='skip')
                except Exception as e:
                    logging.error(f"Erro crítico ao ler {nome_arquivo}: {e}")
                    continue

            # FILTRO: Ignorar linhas onde id_proposta é N/A, nan ou NÃO
            # Convertemos para string para garantir a comparação
            df_filtrado = df[
                (df['id_proposta'].astype(str) != 'N/A') & 
                (df['id_proposta'].astype(str) != 'nan') & 
                (df['id_proposta'].astype(str) != 'NÃO') &
                (df['link_completo'].str.startswith('http')) # Garante que tem um link
            ].copy()

            total_linhas = len(df_filtrado)
            logging.info(f"Linhas válidas para processar: {total_linhas}")

            if total_linhas == 0:
                continue

            dados_finais = []

            # Loop linha a linha
            for index, row in df_filtrado.iterrows():
                id_unico = row['identificador_unico']
                link = row['link_completo']
                
                logging.info(f"Extraindo: {id_unico}...")
                
                # CHAMA A FUNÇÃO DE EXTRAÇÃO
                codigo_instrumento = extrair_codigo_instrumento(driver, link)
                
                logging.info(f"   -> Resultado: {codigo_instrumento}")
                
                dados_finais.append({
                    "identificador_unico": id_unico,
                    "codigo_instrumento": codigo_instrumento
                })

            # Salva o resultado em um novo CSV
            if dados_finais:
                df_resultado = pd.DataFrame(dados_finais)
                df_resultado.to_csv(caminho_saida, sep=';', index=False, encoding='utf-8-sig')
                logging.info(f"Arquivo salvo com sucesso: {caminho_saida}")

    except Exception as e_main:
        logging.error(f"Erro geral no script: {e_main}")
    
    finally:
        driver.quit()
        logging.info("Processo finalizado.")

if __name__ == "__main__":
    processar_arquivos()