import time
import sys
import requests
import logging
import os
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import random
import glob
from urllib.parse import urlparse, parse_qs 
import pandas as pd 

# --- Configuração de Log e Funções Utilitárias (Mantidas) ---
data_atual = datetime.now().strftime("%Y-%m-%d")
log_filename = f"erros_pesquisa_lote_final.{data_atual}.log"

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
logger.addHandler(logging.FileHandler(log_filename, encoding="utf-8"))

def verificar_conexao_internet(url="http://www.google.com", timeout=5):
    try:
        requests.head(url, timeout=timeout)
        return True
    except (requests.ConnectionError, requests.Timeout, Exception):
        return False

if not verificar_conexao_internet():
    logger.error("Sem conexão com a internet. O script será encerrado.")
    print("ERRO: Sem conexão com a internet. Verifique o arquivo de log para mais detalhes.")
    sys.exit(1)

# --- Variáveis de Caminho e URL ---
DIRETORIO_PAI_ORIGEM = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\estadosCodInst"
URL_SERPRO = "https://dd-publico.serpro.gov.br/extensions/cipi/cipi.html"
LINK_SELECTOR = "a[ng-switch-when='url']"
ID_COLUMN_MASTER = 'identificador_unico' 
OUTPUT_SUFFIX = '_links_transferegov_lote.csv'
APPLIED_FILTER_CLOSE_XPATH = "//div[@class='qv-state-item']//span[contains(text(), 'Identificador Único')]/following-sibling::button"
CLEAR_SELECTION_BUTTON_SELECTOR = "button[data-testid='actions-toolbar-clear']"
MODAL_SEARCH_INPUT_SELECTOR = "input[placeholder='Pesquisar na caixa de listagem']"


# --- INÍCIO: DEFINIÇÃO CORRETA DA VARIÁVEL ESTADOS ---
try:
    file_path = f"D:\Mestrado\Orientador\Código de Web Scraping\Módulos\estados.txt" 
    with open(file_path, "r", encoding="utf-8") as file:
        linhas = file.read().splitlines()
    ESTADOS = [linha.strip() for linha in linhas if linha.strip()]
except FileNotFoundError:
    try:
        ESTADOS = [d for d in os.listdir(DIRETORIO_PAI_ORIGEM) 
                    if os.path.isdir(os.path.join(DIRETORIO_PAI_ORIGEM, d))]
    except FileNotFoundError:
        ESTADOS = [] 

if not ESTADOS:
    print(f"AVISO: Nenhuma lista de estados definida. O script será encerrado.")
    sys.exit(0)
# --- FIM: DEFINIÇÃO CORRETA DA VARIÁVEL ESTADOS ---


def get_ids_from_file(estado, dir_path):
    """Lê a coluna 'Identificador Único' do arquivo de dados mestres mais recente."""
    
    print(f"   Buscando arquivo mestre em: {dir_path}")

    all_files = glob.glob(os.path.join(dir_path, '*.xlsx')) + glob.glob(os.path.join(dir_path, '*.csv'))
    
    if not all_files:
        print(f"AVISO: Nenhum arquivo Excel/CSV encontrado para {estado} no diretório de busca.")
        return []

    latest_file = max(all_files, key=os.path.getmtime)
    
    try:
        if latest_file.endswith('.xlsx'):
            df = pd.read_excel(latest_file, header=0) 
        elif latest_file.endswith('.csv'):
            try:
                df = pd.read_csv(latest_file, sep=';', encoding='utf-8')
            except:
                df = pd.read_csv(latest_file, sep=',', encoding='utf-8')
        else:
            return []

        df.columns = [
            col.lower()
            .replace(' ', '_')
            .replace('ú', 'u')
            .replace('.', '')
            .replace('-', '_')
            .replace('(', '')
            .replace(')', '')
            .replace('__', '_')
            .strip()
            for col in df.columns
        ]

        if ID_COLUMN_MASTER in df.columns:
            ids = df[ID_COLUMN_MASTER].astype(str).str.strip().tolist()
            print(f"   Lidos {len(ids)} IDs mestres do arquivo: {os.path.basename(latest_file)}")
            return [i for i in ids if i and i != 'nan']
        else:
            print(f"ERRO: Coluna mestra '{ID_COLUMN_MASTER}' não encontrada no arquivo {os.path.basename(latest_file)}.")
            return []

    except Exception as e:
        logger.error(f"Erro ao processar arquivo mestre para {estado} ({os.path.basename(latest_file)}): {e}")
        return []


def save_final_data(data, estado, dir_path):
    """Salva os dados extraídos em um arquivo CSV no subdiretório do estado."""
    filename = f"ids_links_{estado}{OUTPUT_SUFFIX}"
    filepath = os.path.join(dir_path, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow(['id_proposta', 'link_completo']) # Cabeçalho
        writer.writerows(data)
    print(f"   SUCESSO: {len(data)} registros salvos em {filename}")


def apply_unique_id_filter(driver, id_list):
    """Abre o modal de filtro e aplica a pesquisa de IDs em lote."""
    
    # Junta os IDs em uma string separada por espaço
    ids_string = " ".join(id_list)
    
    # 1. Clicar em 'Identificador Único'
    unique_id_click = WebDriverWait(driver, 15).until( 
        EC.element_to_be_clickable((By.XPATH, "//h6[text()='Identificador Único']"))
    )
    unique_id_click.click()
    print("      -> Clicado em 'Identificador Único'.")
    time.sleep(random.uniform(3, 5)) 
    
    # 2. Clicar no botão Limpar Seleção (Limpa seleções do modal)
    clear_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, CLEAR_SELECTION_BUTTON_SELECTOR))
    )
    driver.execute_script("arguments[0].click();", clear_button)
    print("      -> Seleção anterior limpada (Botão 'Limpar' clicado).")
    time.sleep(random.uniform(1, 2)) 
    
    # 3. Digitar a lista de IDs no campo de busca simples (input type=text)
    search_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, MODAL_SEARCH_INPUT_SELECTOR))
    )
    
    # 4. Digita o novo lote de IDs
    search_input.send_keys(ids_string)
    print(f"      -> {len(id_list)} IDs digitados no campo de busca.")
    time.sleep(random.uniform(3, 5))
    
    # 5. Dar ENTER para acionar o filtro de busca no modal
    search_input.send_keys(Keys.ENTER)
    print("      -> ENTER simulado para aplicar filtro na caixa de seleção.")
    time.sleep(random.uniform(1, 2))
    
    # 6. Clicar no botão 'Confirmar seleção' (o Checkmark)
    confirm_selection_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Confirmar seleção']"))
    )
    driver.execute_script("arguments[0].click();", confirm_selection_button)
    print("      -> Seleção confirmada (Checkmark).")

    # 7. Clicar no botão 'Fechar' do modal de Filtros Adicionais (o modal que fica por último)
    close_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-dismiss='modal'][style*='background-color: #294B89']"))
    )
    driver.execute_script("arguments[0].click();", close_button)
    print("      -> Modal de Filtros Adicionais fechado.")
    time.sleep(8) # Espera maior (8s) para a tabela principal carregar


def extract_data_from_links(driver, ids_lote):
    """Extrai os links de Transferegov para todos os IDs de um lote."""
    extracted_lote_data = []
    
    # Espera que pelo menos um dos links apareça (máximo 15s)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, LINK_SELECTOR))
    )
    
    # Extrai TODOS os links visíveis na tabela atual
    links = driver.find_elements(By.CSS_SELECTOR, LINK_SELECTOR)
    
    for link_element in links:
        try:
            # O texto do link é o Identificador Único (Ex: 48003.12-07)
            id_text = link_element.text.strip()
            
            # Checa se o ID pertence ao lote (garantia extra)
            if id_text in ids_lote:
                full_url_with_params = link_element.get_attribute('title')
                
                if full_url_with_params:
                    # Extrai o idProposta do URL
                    parsed_url = urlparse(full_url_with_params)
                    query_params = parse_qs(parsed_url.query)
                    id_proposta = query_params.get('idProposta', ['N/A'])[0]
                    
                    extracted_lote_data.append((id_proposta, full_url_with_params))
        except Exception:
            continue
            
    return extracted_lote_data


for estado in ESTADOS:
    
    diretorio_origem = os.path.join(DIRETORIO_PAI_ORIGEM, estado)
    ids_to_process = get_ids_from_file(estado, diretorio_origem)
    
    if not ids_to_process:
        continue # Continua para o próximo estado se não houver IDs.

    # Divide a lista de IDs em lotes de 10
    lote_size = 10
    id_batches = [ids_to_process[i:i + lote_size] for i in range(0, len(ids_to_process), lote_size)]
    
    driver = None
    extracted_data = []

    try:
        chrome_options = Options()
        driver = webdriver.Chrome(options=chrome_options)
        
        # 1. Abre a página UMA ÚNICA VEZ
        driver.get(URL_SERPRO)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//span[text()='Filtros Adicionais']"))
        )
        
        # --- APLICA O FILTRO DE ESTADO (UF) ---
        
        # 2. Clicar em 'UF ( Localização)' para filtrar o Estado (Robusto)
        estado_click = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//h6[text()='UF ( Localização)']"))
        )
        estado_click.click()
        print(f"1/8: Filtro 'UF ( Localização)' selecionado para {estado}.")
        
        # 3. Digitar a sigla do estado no campo de busca e confirmar
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
        print(f"2/8: Estado {estado} filtrado com sucesso.")
        time.sleep(5) # Espera o filtro do estado ser aplicado

        print(f"\n--- INICIANDO PESQUISA POR LOTE (Tamanho: {lote_size}) para {estado} ---")
        
        for index, batch in enumerate(id_batches):
            print(f"   [Lote {index+1}/{len(id_batches)}] Pesquisando {len(batch)} IDs.")

            # --- 3. CLICAR EM FILTROS ADICIONAIS ---
            try:
                filtros_adicionais = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Filtros Adicionais']"))
                )
                filtros_adicionais.click()
                time.sleep(random.uniform(1, 2)) 
            except Exception as e:
                logger.error(f"Erro ao clicar em 'Filtros Adicionais' no Lote {index+1} para {estado}: {e}")
                print(f"      -> ERRO: Falha ao abrir filtros. Pulando este lote.")
                continue # CONTINUA: Falha grave, mas vamos para o próximo lote
            
            try:
                # 4. Aplica os filtros de Identificador Único (Lote de 10)
                apply_unique_id_filter(driver, batch)
                
                # 5. Extrai os registros para este lote
                records = extract_data_from_links(driver, batch)
                extracted_data.extend(records)
                
                print(f"      -> SUCESSO: {len(records)} registros extraídos neste lote. Total: {len(extracted_data)}")

            except Exception as e:
                logger.error(f"Erro na aplicação/extração do Lote {index+1} para {estado}: {e}")
                print(f"      -> ERRO: Falha no Lote {index+1}. Verifique o log. Continuando...")
                continue # CONTINUA: Erro específico do lote, vamos para o próximo lote
            
            # 7. Atraso de segurança entre cada lote
            time.sleep(random.uniform(3, 5)) 

        # 8. Salva o resultado final para este estado
        save_final_data(extracted_data, estado, diretorio_origem)

    except Exception as e:
        # Erro FATAL no estado (ex: falha na inicialização do driver ou no filtro de estado)
        logger.error(f"Erro fatal na automação do estado {estado}: {e}")
        print(f"ERRO FATAL: Falha no processo de {estado}. Verifique o log. Reiniciando para o próximo estado.")
        # O código segue para o 'finally' e depois para a próxima iteração do loop 'for estado in ESTADOS'

    finally:
        # ESSENCIAL: Garante que o navegador seja sempre fechado.
        if driver:
            driver.quit()

print("\nProcessamento de todos os estados concluído. 🎉")