# ==============================================================================
# --- IMPORTAÇÕES ---
# As ferramentas do nosso minerador de dados.
# ==============================================================================
import time  # Para pequenas pausas
import sys  # Para encerrar o programa se der erro grave
import os  # Para manipular caminhos de pastas e arquivos no Windows
import glob  # Para listar arquivos em massa (ex: buscar todos os .csv de uma vez)
import pandas as pd  # Nossa ferramenta peso-pesado para ler e filtrar as planilhas
import logging  # Para o diário de bordo (log)
from datetime import datetime  # Para colocar a data no nome do arquivo
from selenium import webdriver  # O motorista do navegador
from selenium.webdriver.common.by import By  # Para localizar itens na tela
from selenium.webdriver.support.ui import WebDriverWait  # Para esperas inteligentes
from selenium.webdriver.support import expected_conditions as EC  # Regras de espera
from selenium.webdriver.chrome.options import Options  # Configurações do Chrome
import csv  # (Importado mas não usado ativamente neste script, o pandas assumiu o trabalho!)

# ==============================================================================
# --- CONFIGURAÇÃO DE LOG (DIÁRIO DE BORDO) ---
# ==============================================================================
data_atual = datetime.now().strftime("%Y-%m-%d") # Pega a data de hoje
log_filename = f"log_extracao_CODIGO_INSTRUMENTO_{data_atual}.log" # Nome do arquivo de log

# Limpa configurações antigas se o script for rodado duas vezes seguidas
logger = logging.getLogger()
if logger.hasHandlers():
    logger.handlers.clear()

# Configura para escrever os erros num arquivo de texto (FileHandler)
file_handler = logging.FileHandler(log_filename, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

# Configura para mostrar os avisos na tela preta (Console) ao vivo (StreamHandler)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) # Mostra mensagens de "INFO" e não só de "ERROR"
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

logger.setLevel(logging.INFO) # Define o nível de fofoca do log para nível INFO (conta tudo)


# ==============================================================================
# --- CAMINHOS DE PASTAS ---
# ==============================================================================
# Onde o robô vai buscar os arquivos gerados pelo script anterior
DIRETORIO_ENTRADA = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtraUFIDLINK"

# Onde o robô vai salvar as planilhas novas com os códigos finais
DIRETORIO_SAIDA = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtraUFID_CODIGOS"

# ==============================================================================
# --- FUNÇÃO: INICIAR NAVEGADOR ---
# ==============================================================================
def iniciar_driver():
    """Prepara e abre o navegador Chrome."""
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # Se tirar o #, o Chrome roda invisível e BEM mais rápido!
    driver = webdriver.Chrome(options=chrome_options) # Abre o navegador
    driver.maximize_window() # Tela cheia
    return driver # Devolve o navegador pronto para uso

# ==============================================================================
# --- FUNÇÃO: EXTRAIR O CÓDIGO (A MÁGICA ACONTECE AQUI) ---
# ==============================================================================
def extrair_codigo_instrumento(driver, url):
    """Acessa o link de uma obra específica e rouba o Código do Instrumento da tela."""
    try:
        driver.get(url) # Manda o navegador abrir o link da obra
        
        wait = WebDriverWait(driver, 10) # Define paciência máxima de 10 segundos
        
        # Estratégia Sniper: O site tem uma linha de tabela (tr) com ID '#tr-alterarNumeroProposta'.
        # Dentro dessa linha, queremos a célula (td) que tem a classe '.field'.
        elemento_codigo = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#tr-alterarNumeroProposta td.field"))
        )
        
        codigo_bruto = elemento_codigo.text # Pega o texto que está escrito lá dentro
        codigo_limpo = codigo_bruto.strip() # Remove espaços em branco invisíveis do começo e do fim
        
        if not codigo_limpo: # Se a célula estiver vazia no site
            return "VAZIO"
            
        return codigo_limpo # Retorna o código encontrado com sucesso!

    except Exception as e: # Se a página demorar, der erro ou não existir essa linha no site
        # Pega só a primeira linha do erro gigante do Selenium para não poluir a tela
        logger.warning(f"Falha ao extrair da URL: {url}. Erro: {str(e).splitlines()[0]}")
        return "ERRO_EXTRACAO" # Retorna esse aviso para não quebrar a planilha

# ==============================================================================
# --- FUNÇÃO PRINCIPAL: ORQUESTRAR TUDO ---
# ==============================================================================
def processar_arquivos():
    """Lê as planilhas de entrada, filtra o lixo, extrai os códigos e salva o resultado."""
    
    os.makedirs(DIRETORIO_SAIDA, exist_ok=True) # Cria a pasta de saída se ela não existir
    
    # Manda o Python procurar todos os arquivos que terminem em ".csv" na pasta de entrada
    padrao_busca = os.path.join(DIRETORIO_ENTRADA, "*.csv")
    arquivos_csv = glob.glob(padrao_busca)

    if not arquivos_csv: # Se a pasta estiver vazia
        logging.error("Nenhum arquivo CSV de entrada encontrado.")
        sys.exit() # Encerra o programa

    logging.info(f"Encontrados {len(arquivos_csv)} arquivos para processar.")

    driver = iniciar_driver() # Chama a função que abre o Chrome UMA ÚNICA VEZ

    try:
        # Começa a passar de arquivo em arquivo (Estado por Estado)
        for arquivo_entrada in arquivos_csv:
            nome_arquivo = os.path.basename(arquivo_entrada) # Pega só o nome (ex: links_AC.csv)
            logging.info(f"--- Processando arquivo: {nome_arquivo} ---")
            
            # Define o nome do arquivo final que será salvo
            nome_saida = f"codigos_instrumento_{nome_arquivo}"
            caminho_saida = os.path.join(DIRETORIO_SAIDA, nome_saida)

            # --- LEITURA DA PLANILHA (PANDAS) ---
            try:
                # Tenta ler com a codificação utf-8-sig (padrão de Excel novo). 
                # on_bad_lines='skip' ignora linhas corrompidas para o script não travar.
                df = pd.read_csv(arquivo_entrada, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
            except:
                try:
                    # Se falhar, tenta com codificação 'latin1' (comum no Windows antigo)
                    df = pd.read_csv(arquivo_entrada, sep=';', encoding='latin1', on_bad_lines='skip')
                except Exception as e:
                    logging.error(f"Erro crítico ao ler {nome_arquivo}: {e}")
                    continue # Se os dois falharem, desiste desse arquivo e pula pro próximo

            # --- LIMPEZA DE DADOS (FILTRO) ---
            # Aqui você elimina linhas inúteis ANTES de mandar o robô acessar a internet (ganho gigante de tempo!)
            df_filtrado = df[
                (df['id_proposta'].astype(str) != 'N/A') & # Ignora propostas não aplicáveis
                (df['id_proposta'].astype(str) != 'nan') & # Ignora células vazias do pandas (Not a Number)
                (df['id_proposta'].astype(str) != 'NÃO') & # Ignora se estiver escrito "NÃO"
                (df['link_completo'].str.startswith('http')) # Garante que a coluna de link realmente começa com "http"
            ].copy() # .copy() cria uma planilha nova e segura na memória

            total_linhas = len(df_filtrado) # Conta quantas linhas sobraram após a limpeza
            logging.info(f"Linhas válidas para processar: {total_linhas}")

            if total_linhas == 0: # Se sobrou nada, pula pro próximo arquivo
                continue

            dados_finais = [] # Cria uma caixinha vazia para guardar os resultados

            # --- LOOP DE ACESSO (LINHA POR LINHA) ---
            # .iterrows() faz o pandas ler a tabela linha por linha
            for index, row in df_filtrado.iterrows():
                id_unico = row['identificador_unico'] # Pega o ID
                link = row['link_completo'] # Pega o link para clicar
                
                logging.info(f"Extraindo: {id_unico}...")
                
                # CHAMA A FUNÇÃO DE EXTRAÇÃO (Manda o navegador ir lá buscar)
                codigo_instrumento = extrair_codigo_instrumento(driver, link)
                
                logging.info(f"   -> Resultado: {codigo_instrumento}")
                
                # Guarda o resultado na caixinha no formato de um dicionário
                dados_finais.append({
                    "identificador_unico": id_unico,
                    "codigo_instrumento": codigo_instrumento
                })

            # --- SALVAMENTO FINAL ---
            if dados_finais: # Se a caixinha não estiver vazia
                df_resultado = pd.DataFrame(dados_finais) # Converte a caixinha numa tabela oficial do Pandas
                # Salva a tabela no computador como CSV
                df_resultado.to_csv(caminho_saida, sep=';', index=False, encoding='utf-8-sig')
                logging.info(f"Arquivo salvo com sucesso: {caminho_saida}")

    except Exception as e_main: # Se algo der muito errado no processo todo
        logging.error(f"Erro geral no script: {e_main}")
    
    finally: # Independente de dar certo ou explodir tudo
        driver.quit() # Fecha o navegador para não gastar sua memória RAM
        logging.info("Processo finalizado.")

# Chama a função principal para a roda girar
if __name__ == "__main__":
    processar_arquivos()