import psycopg2
import requests
import pandas as pd
from sqlalchemy import create_engine
from psycopg2 import OperationalError
import time
import sys
import random 
from datetime import datetime 

# --- Configurações do Banco de Dados ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb" 
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras"

# --- URL da API de Saldo Contábil ---
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira/saldo-contabil"
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

def obter_ug(engine, estado):
    """
    Consulta a tabela de detalhes financeiros para obter pares DISTINTOS de (ug_emitente, id_projeto).
    """
    nome_tabela_origem = f'estados_{estado.lower()}_execucaofinanceira_detalhes'
    print(f"Buscando pares (UG, ID_UNICO) na tabela '{nome_tabela_origem}'...")
    
    # Busca pares distintos de ug_emitente e id_projeto_investimento
    # Usamos id_projeto_investimento que é o campo que contém o identificador_unico
    query = f"""
        SELECT 
            DISTINCT ug_emitente, 
            id_projeto_investimento AS id_unico 
        FROM {nome_tabela_origem} 
        WHERE ug_emitente != '-' AND id_projeto_investimento != '-'
    """
    
    try:
        df_pares = pd.read_sql(query, con=engine)
        
        # Garante que os valores são strings e limpos
        df_pares['ug_emitente'] = df_pares['ug_emitente'].astype(str).str.strip()
        df_pares['id_unico'] = df_pares['id_unico'].astype(str).str.strip()
        
        print(f"Encontrados {len(df_pares)} pares (UG, ID_UNICO) distintos para o estado de {estado}.")
        return df_pares
        
    except Exception as e:
        print(f"Erro ao consultar a tabela '{nome_tabela_origem}'. Verifique se o script anterior foi executado: {e}")
        return pd.DataFrame()

def obter_dados_financeiros(ug_emitente):
    """
    Faz a requisição à API para um UG Emitente e gerencia a paginação, tratando o erro 429.
    """
    dados = []
    pag = 0
    limpar_ug = str(ug_emitente).strip()
    
    while True:
        params = {
            "ugEmitente": limpar_ug,
            "pagina": pag,
            "tamanhoDaPagina": 100
        }
        try:
            response = requests.get(API_URL, params=params, headers=API_HEADERS, timeout=30)
            
            # --- Tratamento de Erro 429 (Rate Limit) ---
            if response.status_code == 429:
                print(f"!!! ERRO 429 - LIMITE ATINGIDO para a UG {limpar_ug}. Esperando 60 segundos...")
                time.sleep(60)
                continue
            # -------------------------------------------

            response.raise_for_status()
            data = response.json()
            
            content = data.get("content", [])
            if not content:
                break

            dados.extend(content)

            if data.get("last", False):
                break
            
            pag += 1
            time.sleep(random.uniform(1, 2))

        except requests.exceptions.RequestException as e:
            print(f"AVISO: Erro na requisição para a UG {limpar_ug} (página {pag}): {e}")
            break
    
    return dados

def process_and_load_data():
    """
    Função principal para orquestrar o processo.
    """
    engine = get_db_connection()
    if not engine:
        sys.exit(1)

    current_timestamp = datetime.now()

    # Nomes das colunas para os registros placeholder
    column_names = [
        'ugEmitente', 'nrNotaEmpenho', 'vlTransferidoExercicioAnterior', 'vlTransferido', 
        'vlRestosAPagar', 'vlReinscritoRp', 'vlReforcado', 'vlRecebidoTransferido', 
        'vlRecebidoExercicioAnterior', 'vlPago', 'vlLiquidadoAPagar', 'vlInscritoRp', 
        'vlIncluido', 'unidadeOrcamentaria', 'vlEmLiquidacao', 
        'vlCanceladoExercicioAnterior', 'vlAnuladoCancelado', 'vlALiquidar', 
        'id_unico' # Adicionamos esta coluna para o placeholder
    ]

    for estado in estados:
        print(f"\n--- Iniciando processamento para o estado: {estado} ---")
        
        # NOVO: Obtém o DataFrame com pares UG e ID_UNICO
        ug_id_pairs_df = obter_ug(engine, estado)
        if ug_id_pairs_df.empty:
            print(f"Nenhum par (UG, ID_UNICO) encontrado para o estado {estado}. Pulando.")
            continue
        
        # Obtém apenas a lista de UGs únicas para consultar a API (para evitar chamadas duplicadas)
        unique_ugs = ug_id_pairs_df['ug_emitente'].unique().tolist()
        
        estado_data = []
        for ug in unique_ugs:
            
            data_from_api = obter_dados_financeiros(ug)
            
            # Se houver dados da API, eles precisam ser associados ao ID_UNICO.
            if data_from_api:
                print(f"Dados encontrados para a UG: {ug}. Total de registros: {len(data_from_api)}")
                
                # Associa o ID_UNICO a todos os registros de saldo
                for item in data_from_api:
                    # Encontra o ID_UNICO associado a esta UG no DataFrame de pares (pode haver mais de um)
                    associated_ids = ug_id_pairs_df[ug_id_pairs_df['ug_emitente'] == ug]['id_unico'].tolist()
                    
                    # Para simplificar, duplicamos o registro de saldo para cada ID de projeto associado a essa UG.
                    # Isso garante a rastreabilidade 1:N (1 UG para N IDs)
                    for id_projeto in associated_ids:
                        new_item = item.copy()
                        new_item['id_unico'] = id_projeto
                        estado_data.append(new_item)

            else:
                # Mantém a lógica de placeholder para UGs sem dados.
                print(f"Nenhum dado encontrado para a UG: {ug}. Criando registro placeholder...")
                associated_ids = ug_id_pairs_df[ug_id_pairs_df['ug_emitente'] == ug]['id_unico'].tolist()
                
                # Cria um placeholder para CADA ID de projeto associado a esta UG
                for id_projeto in associated_ids:
                    placeholder_record = {col: '-' for col in column_names}
                    placeholder_record['ugEmitente'] = ug
                    placeholder_record['id_unico'] = id_projeto 
                    estado_data.append(placeholder_record)
            
            # --- NOVO AJUSTE: Atraso maior entre cada UG ---
            time.sleep(random.uniform(2, 3)) 
            # ------------------------------------------------

        if not estado_data:
            print(f"Nenhum dado encontrado para o estado {estado}. Nenhuma tabela de saldo contábil será modificada.")
            continue

        # Criação do DataFrame com os dados coletados
        df = pd.DataFrame(estado_data)

        # Ajusta os nomes das colunas para o formato snake_case
        df = df.rename(columns={
            'ugEmitente': 'ug_emitente',
            'nrNotaEmpenho': 'nr_nota_empenho',
            'vlTransferidoExercicioAnterior': 'vl_transferido_exercicio_anterior',
            'vlTransferido': 'vl_transferido',
            'vlRestosAPagar': 'vl_restos_a_pagar',
            'vlReinscritoRp': 'vl_reinscrito_rp',
            'vlReforcado': 'vl_reforcado',
            'vlRecebidoTransferido': 'vl_recebido_transferido',
            'vlRecebidoExercicioAnterior': 'vl_recebido_exercicio_anterior',
            'vlPago': 'vl_pago',
            'vlLiquidadoAPagar': 'vl_liquidado_a_pagar',
            'vlInscritoRp': 'vl_inscrito_rp',
            'vlIncluido': 'vl_incluido',
            'unidadeOrcamentaria': 'unidade_orcamentaria',
            'vlEmLiquidacao': 'vl_em_liquidacao',
            'vlCanceladoExercicioAnterior': 'vl_cancelado_exercicio_anterior',
            'vlAnuladoCancelado': 'vl_anulado_cancelado',
            'vlALiquidar': 'vl_a_liquidar',
        })

        # NOVO: Adiciona a coluna de timestamp
        df['data_execucao'] = current_timestamp

        # Define o nome da tabela de destino
        target_table_name = f'estados_{estado.lower()}_saldo_contabil'

        try:
            print(f"\nAnexando {len(df)} registros (UGs e IDs de Projeto) à tabela histórica '{target_table_name}'...")
            df.to_sql(name=target_table_name, con=engine, if_exists='append', index=False)
            print(f"Dados de Saldo Contábil de {estado} anexados com sucesso na tabela '{target_table_name}'.")
        except Exception as e:
            print(f"ERRO ao salvar dados na tabela '{target_table_name}': {e}")
    
    print("\nProcessamento de todos os estados concluído.")

if __name__ == "__main__":
    process_and_load_data()