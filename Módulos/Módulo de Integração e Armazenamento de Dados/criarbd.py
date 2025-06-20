import psycopg2
from psycopg2 import OperationalError
import pandas as pd
from sqlalchemy import create_engine
import os 
import glob 

DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb" 
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras" 

PASTA_RAIZ_DADOS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD" 


ministerios = [
    "ministerio_da_defesa",
    "ministerio_da_pesca_e_aquicultura",
    "ministerio_da_ciencia_tecnologia_e_inovacao",
    "ministerio_da_gestao_e_da_inovacao_em_servicos_publicos",
    "ministerio_da_cultura",
    "ministerio_da_justica_e_seguranca_publica",
    "ministerio_do_turismo",
    "ministerio_da_economia",
    "ministerio_das_comunicacoes",
    "ministerio_das_mulheres",
    "ministerio_de_minas_e_energia",
    "ministerio_de_portos_e_aeroportos",
    "ministerio_da_infraestrutura",
    "ministerio_do_esporte",
    "presidencia_da_republica",
    "sec_esp_de_agric_fam_e_desenv_agrario",
    "ministerio_do_desenvolvimento_e_assistencia_social_familiar_e_combate_a_fome",
    "ministerio_do_desenvolvimento_agrario_e_da_agricultura_familiar",
    "ministerio_do_desenvolvimento_industria_comercio_e_servicos",
    "ministerio_do_meio_ambiente",
    "ministerio_do_trabalho_e_emprego",
    "ministerio_do_desenvolvimento_regional",
    "MINISTERIO_DAS_CIDADES",
    "MINISTERIO_DA_EDUCACAO",
    "MINISTERIO_DA_SAUDE"
]



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
        conn.autocommit = True # Permite que comandos DDL (como CREATE DATABASE) sejam executados
        cursor = conn.cursor()

        # Verifica se o DB existe antes de criar
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


def process_and_load_ministry_data():
    """
    Conecta ao banco de dados principal, itera sobre os ministérios,
    encontra o arquivo Excel mais recente em cada pasta e o carrega.
    """
    print(f"\nTentando conectar ao banco de dados: {TARGET_DB_NAME}")
    try:
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
        print("Conexão com o banco de dados principal estabelecida para carga de dados.")
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados '{TARGET_DB_NAME}' para carga de dados: {e}")
        print("Certifique-se de que o banco de dados foi criado e as credenciais estão corretas.")
        return 

    print("\nIniciando processamento dos arquivos Excel dos ministérios...")
    for ministerio in ministerios:
        ministry_folder_path = os.path.join(PASTA_RAIZ_DADOS, ministerio)

        if not os.path.isdir(ministry_folder_path):
            print(f"  AVISO: Pasta do ministério '{ministry_folder_path}' não encontrada. Pulando...")
            continue

        excel_files = glob.glob(os.path.join(ministry_folder_path, '*.xlsx'))

        if not excel_files:
            print(f"  AVISO: Nenhum arquivo .xlsx encontrado na pasta '{ministry_folder_path}'. Pulando...")
            continue

        latest_excel_file = max(excel_files, key=os.path.getmtime)
        print(f"  Processando: {ministerio} (arquivo mais recente: {latest_excel_file})")

        try:
            df = pd.read_excel(latest_excel_file, header=0)

            if df.empty:
                print(f"  AVISO: O arquivo '{os.path.basename(latest_excel_file)}' está vazio. Nenhuma tabela criada/atualizada.")
                continue

            df.columns = [
                col.lower()
                .replace(' ', '_')
                .replace('.', '')
                .replace('-', '_')
                .replace('(', '')
                .replace(')', '')
                .replace('[', '') 
                .replace(']', '')
                .strip()
                for col in df.columns
            ]

            df = df.rename(columns={c: f'col_{i}' for i, c in enumerate(df.columns) if not c.strip() or not c.replace('_', '').isalnum()})
            df.columns = ['_'.join(filter(None, col.split('_'))) for col in df.columns]


            df.to_sql(name=ministerio, con=engine, if_exists='replace', index=False)
            print(f"  Tabela '{ministerio}' criada/atualizada e dados inseridos com sucesso.")

        except pd.errors.EmptyDataError:
            print(f"  AVISO: O arquivo Excel '{os.path.basename(latest_excel_file)}' está vazio ou não possui dados válidos. Nenhuma tabela criada/atualizada para este ministério.")
        except FileNotFoundError:
            print(f"  ERRO: Arquivo '{os.path.basename(latest_excel_file)}' não encontrado. Isso não deveria acontecer com o glob. Verifique permissões.")
        except Exception as e:
            print(f"  ERRO ao processar '{ministerio}' do arquivo '{os.path.basename(latest_excel_file)}': {e}")

    print("\nProcessamento de todos os ministérios concluído.")

if __name__ == "__main__":
    create_target_database()
    process_and_load_ministry_data()