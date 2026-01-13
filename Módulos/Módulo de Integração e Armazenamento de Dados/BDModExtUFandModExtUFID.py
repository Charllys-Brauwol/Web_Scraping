import psycopg2
from psycopg2 import OperationalError
import pandas as pd
from sqlalchemy import create_engine
import os 
import glob 

# --- Configurações do Banco ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb" 
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras" 

# --- Caminho Base ---
# O script vai procurar as pastas ModExtUF e ModExtUFID dentro deste caminho
CAMINHO_BASE_ARQUIVOS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD"

# --- Configuração das Pastas a Processar ---
PASTAS_ALVO = ["ModExtUF", "ModExtUFID"]

# --- Lista de Estados ---
ESTADOS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", 
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

def create_target_database():
    """Garante que o banco existe."""
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
        else:
            print(f"Banco de dados '{TARGET_DB_NAME}' já existe.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar DB: {e}")
        exit()

def limpar_nomes_colunas(df):
    """Padroniza nomes das colunas para o PostgreSQL."""
    df.columns = [
        str(col).lower()
        .replace(' ', '_')
        .replace('.', '')
        .replace('-', '_')
        .replace('/', '_')
        .replace('(', '').replace(')', '')
        .strip()
        for col in df.columns
    ]
    return df

def ler_arquivo_robusto(filepath):
    """Tenta ler Excel ou CSV com diferentes separadores."""
    if filepath.endswith('.xlsx'):
        return pd.read_excel(filepath)
    elif filepath.endswith('.csv'):
        try:
            # Tenta ponto e vírgula (padrão brasileiro)
            return pd.read_csv(filepath, sep=';', low_memory=False)
        except:
            # Tenta vírgula (padrão americano)
            return pd.read_csv(filepath, sep=',', low_memory=False)
    return pd.DataFrame() # Retorna vazio se não for extensão conhecida

def processar_pastas_estados():
    print(f"\nConectando ao banco: {TARGET_DB_NAME}")
    try:
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return 

    print("\nIniciando processamento dos Estados...")

    # 1. Loop pelas pastas principais (ModExtUF, ModExtUFID)
    for pasta_raiz in PASTAS_ALVO:
        print(f"\n==========================================")
        print(f">>> PROCESSANDO DIRETÓRIO: {pasta_raiz}")
        print(f"==========================================")

        # 2. Loop pelos Estados (AC, AL, etc.)
        for estado in ESTADOS:
            
            # Monta o caminho: C:\...\ModExtUF\AC
            caminho_estado = os.path.join(CAMINHO_BASE_ARQUIVOS, pasta_raiz, estado)
            
            # Define o nome da tabela: ModExtUF_AC
            nome_tabela = f"{pasta_raiz}_{estado}"

            if not os.path.isdir(caminho_estado):
                print(f"   [PULANDO] Pasta não encontrada: {caminho_estado}")
                continue

            # Busca arquivos (CSV e XLSX)
            arquivos = glob.glob(os.path.join(caminho_estado, '*.csv')) + \
                       glob.glob(os.path.join(caminho_estado, '*.xlsx'))
            
            if not arquivos:
                print(f"   [VAZIO] Nenhum arquivo em {pasta_raiz}/{estado}")
                continue

            # 3. Pega o MAIS RECENTE
            arquivo_recente = max(arquivos, key=os.path.getmtime)
            print(f"   Lendo: {os.path.basename(arquivo_recente)} -> Tabela: {nome_tabela}")

            try:
                df = ler_arquivo_robusto(arquivo_recente)
                
                if df.empty:
                    print(f"   [AVISO] Arquivo vazio. Ignorando.")
                    continue

                # Limpeza
                df = limpar_nomes_colunas(df)
                
                # Adiciona coluna de controle (opcional)
                df['arquivo_origem'] = os.path.basename(arquivo_recente)

                # 4. Salva no Banco
                df.to_sql(name=nome_tabela, con=engine, if_exists='replace', index=False)
                print(f"   SUCESSO: Tabela '{nome_tabela}' criada com {len(df)} registros.")

            except Exception as e:
                print(f"   ERRO CRÍTICO ao processar {estado}: {e}")

    print("\nProcessamento concluído. 🎉")

if __name__ == "__main__":
    create_target_database()
    processar_pastas_estados()