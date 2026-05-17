# ==============================================================================
# --- IMPORTAÇÕES ---
# ==============================================================================
import psycopg2  # Conector do PostgreSQL
from psycopg2 import OperationalError  # Para capturar erros de banco
import pandas as pd  # Para manipular as planilhas CSV
from sqlalchemy import create_engine  # Motor de exportação para o banco
import os  # Para manipular pastas no Windows
import glob  # Para buscar arquivos em lote (ex: '*.csv')
import re # Biblioteca de Expressões Regulares (Regex) para achar padrões de texto em strings

# ==============================================================================
# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# ==============================================================================
DB_HOST = "localhost" # Banco na máquina local
DB_USER = "postgres" # Usuário administrador
DB_PASSWORD = "cb2907cb" # Senha
DB_PORT = "5432" # Porta padrão
TARGET_DB_NAME = "minhas_obras" # Banco alvo

# ==============================================================================
# --- CAMINHOS E PASTAS ALVO ---
# ==============================================================================
# Caminho base onde estão as pastas
CAMINHO_BASE_ARQUIVOS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD"

# As pastas específicas que contêm os arquivos soltos que queremos processar
PASTAS_ALVO = ["ModExtraUFIDLINK", "ModExtraUFID_CODIGOS"]

# ==============================================================================
# --- FUNÇÃO: VERIFICAR/CRIAR O BANCO DE DADOS ---
# ==============================================================================
def create_target_database():
    """Garante que o banco de dados 'minhas_obras' exista antes de iniciar."""
    try:
        # Conecta no banco de fábrica ('postgres')
        conn = psycopg2.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, database="postgres"
        )
        conn.autocommit = True # Exigido para comandos estruturais
        cursor = conn.cursor()
        
        # Pergunta ao sistema se o banco alvo já existe
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB_NAME}'")
        
        if not cursor.fetchone(): # Se não achar o banco...
            print(f"Criando banco de dados: {TARGET_DB_NAME}")
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME}") # Cria do zero
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar DB: {e}")
        exit() # Mata o script se der erro de conexão

# ==============================================================================
# --- FUNÇÃO: PADRONIZAR NOME DAS COLUNAS ---
# ==============================================================================
def limpar_nomes_colunas(df):
    """Limpa os nomes das colunas para o padrão snake_case do PostgreSQL."""
    df.columns = [
        str(col).lower() # Tudo minúsculo
        .replace(' ', '_').replace('.', '').replace('-', '_') # Troca espaços e traços por underline
        .replace('/', '_').strip() # Troca barras e tira espaços nas pontas
        for col in df.columns
    ]
    return df

# ==============================================================================
# --- FUNÇÃO: EXTRAIR METADADOS DO NOME DO ARQUIVO (REGEX) ---
# ==============================================================================
def extrair_uf_data(nome_arquivo):
    """
    A MÁGICA: Lê o nome do arquivo e 'rouba' a UF e a Data de dentro dele.
    Ex: de 'links_extraidos_TO_2026-01-03.csv' ele tira ('TO', '2026_01_03').
    """
    # Regex: Procura por _ (underline) + 2 letras Maiúsculas + _ (underline) + Data YYYY-MM-DD
    padrao = r"_([A-Z]{2})_(\d{4}-\d{2}-\d{2})"
    match = re.search(padrao, nome_arquivo)
    
    if match: # Se o nome do arquivo seguir essa regra...
        uf = match.group(1) # Pega o Grupo 1 (A sigla do estado, ex: TO)
        data = match.group(2).replace('-', '_') # Pega o Grupo 2 (A data) e troca traço por underline pro banco de dados aceitar no nome da tabela
        return uf, data # Devolve as duas variáveis
        
    return None, None # Se o nome for fora do padrão, devolve vazio

# ==============================================================================
# --- FUNÇÃO PRINCIPAL: ORQUESTRAÇÃO DE CARGA ---
# ==============================================================================
def processar_arquivos_soltos():
    print(f"\nConectando ao banco: {TARGET_DB_NAME}")
    try:
        # Liga o motor do SQLAlchemy apontando pro banco de dados
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return 

    print("\nIniciando processamento...")

    # --- LOOP DAS PASTAS ALVO ---
    for pasta in PASTAS_ALVO:
        # Junta o caminho base com o nome da pasta alvo
        caminho_completo = os.path.join(CAMINHO_BASE_ARQUIVOS, pasta)
        
        print(f"\n==========================================")
        print(f">>> PROCESSANDO PASTA: {pasta}")
        print(f"==========================================")

        # Confere se a pasta realmente existe no seu computador
        if not os.path.isdir(caminho_completo):
            print(f"   [ERRO] Pasta não encontrada: {caminho_completo}")
            continue # Pula pra próxima se não existir

        # Busca todos os arquivos CSV soltos dentro dessa pasta
        arquivos = glob.glob(os.path.join(caminho_completo, '*.csv'))
        
        if not arquivos: # Se a pasta estiver vazia
            print(f"   [AVISO] Nenhum arquivo CSV encontrado.")
            continue

        # --- LOOP DOS ARQUIVOS ---
        for arquivo in arquivos:
            # Extrai apenas o nome final do arquivo (Ex: 'links_extraidos_SP_2026-03-22.csv')
            nome_arquivo = os.path.basename(arquivo)
            
            # 1. Manda o nome pro nosso extrator Regex
            uf, data = extrair_uf_data(nome_arquivo)
            
            if uf and data: # Se a Regex funcionou perfeitamente
                # 2. Monta o nome da tabela dinamicamente. Ex: ModExtraUFIDLINK_SP_2026_03_22
                nome_tabela = f"{pasta}_{uf}_{data}"
            else:
                # 3. Fallback (Plano B): Se você renomeou o arquivo na mão fora do padrão...
                print(f"   [ALERTA] Nome fora do padrão: {nome_arquivo}. Usando nome do arquivo como tabela.")
                # Ele usa o próprio nome do arquivo limpo como nome da tabela
                nome_tabela = nome_arquivo.replace('.csv', '').replace('-', '_')

            print(f"   Lendo: {nome_arquivo} -> Criando Tabela: {nome_tabela}")

            try:
                # --- LEITURA À PROVA DE FALHAS ---
                try:
                    # 1ª Tentativa: Tenta ler com separador Ponto-e-Vírgula (;)
                    df = pd.read_csv(arquivo, sep=';', low_memory=False)
                except:
                    # 2ª Tentativa: Tenta ler com separador Vírgula (,)
                    df = pd.read_csv(arquivo, sep=',', low_memory=False)

                if df.empty: # Se a planilha só tiver cabeçalho
                    print(f"   [PULANDO] Arquivo vazio.")
                    continue

                # Passa a vassoura nos nomes das colunas
                df = limpar_nomes_colunas(df)
                
                # --- CARGA NO BANCO DE DADOS (LOAD) ---
                # Empurra pro PostgreSQL. if_exists='replace' deleta a tabela velha (se existir com esse nome exato) e sobe a nova.
                df.to_sql(name=nome_tabela, con=engine, if_exists='replace', index=False)
                
                print(f"   SUCESSO: {len(df)} registros salvos.")

            except Exception as e:
                # Se a planilha estiver muito bugada/corrompida
                print(f"   ERRO ao processar {nome_arquivo}: {e}")

    print("\nProcessamento concluído. 🎉")

# Ponto de partida do Python
if __name__ == "__main__":
    create_target_database()
    processar_arquivos_soltos()