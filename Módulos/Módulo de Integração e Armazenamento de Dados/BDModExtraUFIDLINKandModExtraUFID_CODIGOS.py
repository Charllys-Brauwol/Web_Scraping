import psycopg2
from psycopg2 import OperationalError
import pandas as pd
from sqlalchemy import create_engine
import os 
import glob 
import re # Biblioteca para expressões regulares (achar padrões no texto)

# --- Configurações do Banco ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb" 
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras" 

# --- Caminho Base ---
CAMINHO_BASE_ARQUIVOS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD"

# --- Pastas a Processar ---
PASTAS_ALVO = ["ModExtraUFIDLINK", "ModExtraUFID_CODIGOS"]

def create_target_database():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, database="postgres"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB_NAME}'")
        if not cursor.fetchone():
            print(f"Criando banco de dados: {TARGET_DB_NAME}")
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar DB: {e}")
        exit()

def limpar_nomes_colunas(df):
    """Padroniza colunas."""
    df.columns = [
        str(col).lower()
        .replace(' ', '_').replace('.', '').replace('-', '_')
        .replace('/', '_').strip()
        for col in df.columns
    ]
    return df

def extrair_uf_data(nome_arquivo):
    """
    Usa Regex para encontrar o padrão _UF_DATA no nome do arquivo.
    Ex: links_extraidos_TO_2026-01-03.csv -> Retorna ('TO', '2026_01_03')
    """
    # Procura por: underscore + 2 letras maiúsculas + underscore + data (YYYY-MM-DD)
    padrao = r"_([A-Z]{2})_(\d{4}-\d{2}-\d{2})"
    match = re.search(padrao, nome_arquivo)
    
    if match:
        uf = match.group(1)
        data = match.group(2).replace('-', '_') # Troca traço por underline para o SQL não reclamar
        return uf, data
    return None, None

def processar_arquivos_soltos():
    print(f"\nConectando ao banco: {TARGET_DB_NAME}")
    try:
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return 

    print("\nIniciando processamento...")

    for pasta in PASTAS_ALVO:
        caminho_completo = os.path.join(CAMINHO_BASE_ARQUIVOS, pasta)
        
        print(f"\n==========================================")
        print(f">>> PROCESSANDO PASTA: {pasta}")
        print(f"==========================================")

        if not os.path.isdir(caminho_completo):
            print(f"   [ERRO] Pasta não encontrada: {caminho_completo}")
            continue

        # Pega todos os CSVs da pasta
        arquivos = glob.glob(os.path.join(caminho_completo, '*.csv'))
        
        if not arquivos:
            print(f"   [AVISO] Nenhum arquivo CSV encontrado.")
            continue

        for arquivo in arquivos:
            nome_arquivo = os.path.basename(arquivo)
            
            # 1. Extrai UF e Data do nome do arquivo
            uf, data = extrair_uf_data(nome_arquivo)
            
            if uf and data:
                # 2. Monta o nome da tabela conforme pedido: PASTA + UF + DATA
                nome_tabela = f"{pasta}_{uf}_{data}"
            else:
                # Fallback: Se o nome do arquivo estiver fora do padrão, usa o nome do arquivo limpo
                print(f"   [ALERTA] Nome fora do padrão: {nome_arquivo}. Usando nome do arquivo como tabela.")
                nome_tabela = nome_arquivo.replace('.csv', '').replace('-', '_')

            print(f"   Lendo: {nome_arquivo} -> Criando Tabela: {nome_tabela}")

            try:
                # Tenta ler com ; ou ,
                try:
                    df = pd.read_csv(arquivo, sep=';', low_memory=False)
                except:
                    df = pd.read_csv(arquivo, sep=',', low_memory=False)

                if df.empty:
                    print(f"   [PULANDO] Arquivo vazio.")
                    continue

                df = limpar_nomes_colunas(df)
                
                # Salva no Banco
                df.to_sql(name=nome_tabela, con=engine, if_exists='replace', index=False)
                print(f"   SUCESSO: {len(df)} registros salvos.")

            except Exception as e:
                print(f"   ERRO ao processar {nome_arquivo}: {e}")

    print("\nProcessamento concluído. 🎉")

if __name__ == "__main__":
    create_target_database()
    processar_arquivos_soltos()