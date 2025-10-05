import psycopg2
from psycopg2 import OperationalError
import pandas as pd
from sqlalchemy import create_engine
import os 
import glob 

# --- Configurações do Banco de Dados ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb" 
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras" 

# --- Diretório Raiz de Dados ---
PASTA_RAIZ_DADOS_ESTADOS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\estados"

# A lista de estados é obtida do seu primeiro script, mas para o carregamento,
# podemos simplesmente iterar pelas pastas dentro de 'estados'.
# Esta lista será gerada dinamicamente.


def create_target_database():
    """
    Tenta criar o banco de dados especificado por TARGET_DB_NAME,
    conectando-se primeiro ao banco de dados 'postgres' padrão.
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            database="postgres" 
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB_NAME}'")
        exists = cursor.fetchone()

        if not exists:
            print(f"Criando banco de dados: {TARGET_DB_NAME}")
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME}")
            print(f"Banco de dados '{TARGET_DB_NAME}' criado com sucesso.")
        else:
            print(f"Banco de dados '{TARGET_DB_NAME}' já existe.")

        cursor.close()
        conn.close()

    except OperationalError as e:
        print(f"Erro de conexão ou ao criar o banco de dados '{TARGET_DB_NAME}': {e}")
        exit() 
    except Exception as e:
        print(f"Um erro inesperado ocorreu ao criar o banco de dados: {e}")
        exit()


def process_and_load_state_data():
    """
    Conecta ao banco de dados principal, itera sobre as pastas de estados,
    encontra o arquivo Excel mais recente em cada uma e o carrega.
    """
    print(f"\nTentando conectar ao banco de dados: {TARGET_DB_NAME}")
    try:
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
        print("Conexão com o banco de dados principal estabelecida para carga de dados.")
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados '{TARGET_DB_NAME}' para carga de dados: {e}")
        print("Certifique-se de que o banco de dados foi criado e as credenciais estão corretas.")
        return 

    print("\nIniciando processamento dos arquivos Excel dos estados...")
    
    # Gera a lista de estados a partir dos nomes das pastas
    estado_folders = [d for d in os.listdir(PASTA_RAIZ_DADOS_ESTADOS) if os.path.isdir(os.path.join(PASTA_RAIZ_DADOS_ESTADOS, d))]
    
    if not estado_folders:
        print("AVISO: Nenhuma pasta de estado encontrada em 'C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD\\estados'. Verifique se os downloads foram concluídos.")
        return

    for estado in estado_folders:
        state_folder_path = os.path.join(PASTA_RAIZ_DADOS_ESTADOS, estado)

        excel_files = glob.glob(os.path.join(state_folder_path, '*.xlsx'))

        if not excel_files:
            print(f"  AVISO: Nenhum arquivo .xlsx encontrado na pasta '{state_folder_path}'. Pulando...")
            continue

        latest_excel_file = max(excel_files, key=os.path.getmtime)
        print(f"  Processando: {estado} (arquivo mais recente: {latest_excel_file})")

        try:
            df = pd.read_excel(latest_excel_file, header=0)

            if df.empty:
                print(f"  AVISO: O arquivo '{os.path.basename(latest_excel_file)}' está vazio. Nenhuma tabela criada/atualizada.")
                continue

            # Limpeza e normalização dos nomes das colunas
            df.columns = [
                col.lower()
                .replace(' ', '_')
                .replace('.', '')
                .replace('-', '_')
                .replace('(', '')
                .replace(')', '')
                .replace('[', '') 
                .replace(']', '')
                .replace('__', '_') # Substitui duplos underscores por um único
                .strip()
                for col in df.columns
            ]

            # Renomeia colunas que ficaram vazias ou inválidas
            df = df.rename(columns={c: f'col_{i}' for i, c in enumerate(df.columns) if not c.strip() or not c.replace('_', '').isalnum()})
            df.columns = ['_'.join(filter(None, col.split('_'))) for col in df.columns]

            # Define o nome da tabela com o prefixo 'estados_' para evitar conflito com os ministérios
            table_name = f'estados_{estado}'.lower()
            df.to_sql(name=table_name, con=engine, if_exists='replace', index=False)
            print(f"  Tabela '{table_name}' criada/atualizada e dados inseridos com sucesso.")

        except pd.errors.EmptyDataError:
            print(f"  AVISO: O arquivo Excel '{os.path.basename(latest_excel_file)}' está vazio ou não possui dados válidos. Nenhuma tabela criada/atualizada para este estado.")
        except FileNotFoundError:
            print(f"  ERRO: Arquivo '{os.path.basename(latest_excel_file)}' não encontrado. Isso não deveria acontecer com o glob. Verifique permissões.")
        except Exception as e:
            print(f"  ERRO ao processar '{estado}' do arquivo '{os.path.basename(latest_excel_file)}': {e}")

    print("\nProcessamento de todos os estados concluído.")


if __name__ == "__main__":
    create_target_database()
    process_and_load_state_data()