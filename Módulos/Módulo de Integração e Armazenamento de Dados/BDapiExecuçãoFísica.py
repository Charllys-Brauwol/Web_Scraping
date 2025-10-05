import psycopg2
import requests
import pandas as pd
from sqlalchemy import create_engine
from psycopg2 import OperationalError
import time
import sys
import random 
from datetime import datetime # Importa para o timestamp de execução

# --- Configurações do Banco de Dados ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb" 
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras"

# --- URL da API de Execução Física ---
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-fisica"
API_HEADERS = {"accept": "*/*"}

# Lista de estados a serem processados
estados = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

def get_db_connection():
    """
    Cria e retorna uma conexão com o banco de dados.
    """
    try:
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
        print("Conexão com o banco de dados estabelecida com sucesso.")
        return engine
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados '{TARGET_DB_NAME}': {e}")
        return None

def get_project_ids_by_state(engine, estado):
    """
    Consulta o banco de dados para obter os 'identificador_único' para um estado específico.
    """
    source_table_name = f'estados_{estado}'.lower()
    print(f"Buscando identificadores únicos na tabela '{source_table_name}'...")
    
    query = f'SELECT "identificador_único" FROM {source_table_name}'
    
    try:
        df_ids = pd.read_sql(query, con=engine)
        print(f"Encontrados {len(df_ids)} identificadores para o estado de {estado}.")
        return df_ids['identificador_único'].tolist()
    except Exception as e:
        print(f"Erro ao consultar a tabela '{source_table_name}': {e}")
        return []

def fetch_physical_data(project_id):
    """
    Faz a requisição à API para um ID de projeto e gerencia a paginação, tratando o erro 429.
    """
    all_data = []
    page = 0
    clean_pid = str(project_id).strip() # Limpa o ID
    
    while True:
        params = {
            "idUnico": clean_pid,
            "pagina": page,
            "tamanhoDaPagina": 100
        }
        try:
            response = requests.get(API_URL, params=params, headers=API_HEADERS, timeout=30)
            
            # --- Tratamento de Erro 429 (Rate Limit) ---
            if response.status_code == 429:
                print(f"!!! ERRO 429 - LIMITE ATINGIDO para {clean_pid}. Esperando 60 segundos...")
                time.sleep(60) # Espera 1 minuto
                continue # Tenta a requisição novamente
            # -------------------------------------------

            response.raise_for_status()
            data = response.json()
            
            content = data.get("content", [])
            if not content:
                break
            
            # Adiciona o 'identificador_único' a cada item da lista retornada pela API
            for item in content:
                item['id_unico'] = clean_pid
            
            all_data.extend(content)
            
            if data.get("last", False):
                break
            
            page += 1
            time.sleep(random.uniform(1, 2)) # Atraso menor entre as páginas

        except requests.exceptions.RequestException as e:
            print(f"AVISO: Erro na requisição para o ID {clean_pid} (página {page}): {e}")
            break
    
    return all_data

def process_and_load_data():
    """
    Função principal para orquestrar o processo.
    """
    engine = get_db_connection()
    if not engine:
        sys.exit(1)

    # NOVO: Define o timestamp da execução
    current_timestamp = datetime.now()

    # Nomes das colunas para os registros placeholder, incluindo 'id_unico'
    column_names = [
        'id_unico', 'idUnico', 'percentual', 'dataSituacao', 'situacao', 'observacoes', 
        'emOperacao', 'justificativaEmOperacao', 'cancelamentosParalisacoes', 'documentos'
    ]

    for estado in estados:
        print(f"\n--- Iniciando processamento para o estado: {estado} ---")
        
        project_ids = get_project_ids_by_state(engine, estado)
        if not project_ids:
            print(f"Nenhum ID de projeto encontrado para o estado {estado}. Pulando para o próximo.")
            continue
        
        estado_data = []
        for pid in project_ids:
            
            clean_pid = str(pid).strip()
            data_from_api = fetch_physical_data(clean_pid)
            
            if data_from_api:
                print(f"Dados encontrados para o projeto ID: {clean_pid}. Total de registros: {len(data_from_api)}")
                estado_data.extend(data_from_api)
            else:
                print(f"Nenhum dado encontrado para o projeto ID: {clean_pid}. Criando registro placeholder...")
                # Cria um registro com '-' em todas as colunas
                placeholder_record = {col: '-' for col in column_names}
                # Garante que o ID do projeto esteja correto
                placeholder_record['id_unico'] = clean_pid
                placeholder_record['idUnico'] = clean_pid
                estado_data.append(placeholder_record)
            
            # --- NOVO AJUSTE: Atraso maior entre cada ID de projeto ---
            # Tempo de espera de 2 a 3 segundos para evitar o erro 429
            time.sleep(random.uniform(2, 3)) 
            # --------------------------------------------------------

        if not estado_data:
            print(f"Nenhum dado, nem registro placeholder, encontrado para o estado {estado}. Nenhuma tabela será criada.")
            continue

        # Criação do DataFrame com os dados coletados
        df = pd.DataFrame(estado_data)

        # Ajusta os nomes das colunas para o formato snake_case
        df = df.rename(columns={
            'id_unico': 'id_unico',
            'idUnico': 'id_unico_api',
            'dataSituacao': 'data_situacao',
            'emOperacao': 'em_operacao',
            'justificativaEmOperacao': 'justificativa_em_operacao',
            'cancelamentosParalisacoes': 'cancelamentos_paralisacoes'
            # 'documentos' é array, mantido como está
        })

        # NOVO: Adiciona a coluna de timestamp
        df['data_execucao'] = current_timestamp

        # Define o nome da tabela de destino
        target_table_name = f'estados_{estado.lower()}_execucao_fisica'

        try:
            print(f"\nAnexando {len(df)} registros à tabela histórica '{target_table_name}'...")
            # MUDANÇA CRUCIAL: 'if_exists='append'' para salvar o histórico
            df.to_sql(name=target_table_name, con=engine, if_exists='append', index=False)
            print(f"Dados de Execução Física de {estado} anexados com sucesso na tabela '{target_table_name}'.")
        except Exception as e:
            print(f"ERRO ao salvar dados na tabela '{target_table_name}': {e}")
    
    print("\nProcessamento de todos os estados concluído.")

if __name__ == "__main__":
    process_and_load_data()