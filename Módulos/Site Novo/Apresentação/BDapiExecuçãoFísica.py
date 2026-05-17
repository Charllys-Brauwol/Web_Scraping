# ==============================================================================
# --- IMPORTAÇÕES ---
# Ferramentas necessárias para conectar ao banco, acessar a web e manipular dados.
# ==============================================================================
import psycopg2  # Adaptador para o Python conversar com o PostgreSQL
import requests  # Para acessar a API do Governo na web
import pandas as pd  # Para manipular os dados no formato de tabela
from sqlalchemy import create_engine  # O motor que conecta o Pandas ao banco de dados
from psycopg2 import OperationalError  # Captura falhas na conexão com o banco
import time  # Para pausar o script temporariamente
import sys  # Para comandos de sistema (como forçar a parada do script)
import random # Para gerar pausas com tempo aleatório (humaniza o robô)
from datetime import datetime # Para registrar o exato momento (carimbo de data/hora) em que o script rodou

# ==============================================================================
# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# Informações para acessar o seu PostgreSQL local.
# ==============================================================================
DB_HOST = "localhost" # O banco de dados está na sua própria máquina
DB_USER = "postgres" # Usuário administrador do banco
DB_PASSWORD = "cb2907cb"  # Sua senha
DB_PORT = "5432" # Porta padrão do Postgres
TARGET_DB_NAME = "minhas_obras" # Nome do banco onde os dados serão salvos

# ==============================================================================
# --- URL DA API ---
# ==============================================================================
# Endpoint da API específico para a Execução FÍSICA das obras
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-fisica"
API_HEADERS = {"accept": "*/*"} # Diz à API que aceitamos qualquer formato que ela retornar

# Lista com a sigla de todos os estados do Brasil para o loop percorrer
estados = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

# ==============================================================================
# --- FUNÇÃO: CONEXÃO COM O BANCO ---
# ==============================================================================
def get_db_connection():
    """Cria a ponte (engine) entre o Python e o banco de dados PostgreSQL."""
    try:
        # Monta a string de conexão no formato exigido pelo SQLAlchemy
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
        print("Conexão com o banco de dados estabelecida com sucesso.")
        return engine # Devolve o motor ligado
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados '{TARGET_DB_NAME}': {e}")
        return None

# ==============================================================================
# --- FUNÇÃO: BUSCAR IDs DOS PROJETOS NO BANCO ---
# ==============================================================================
def get_project_ids_by_state(engine, estado):
    """Lê a tabela principal do estado no banco e extrai todos os IDs únicos de obras."""
    source_table_name = f'estados_{estado}'.lower() # Monta o nome da tabela (ex: estados_rj)
    print(f"Buscando identificadores únicos na tabela '{source_table_name}'...")
    
    # Query SQL para pegar somente a coluna do identificador
    query = f'SELECT "identificador_único" FROM {source_table_name}'
    
    try:
        # Executa a query e devolve o resultado como um DataFrame (tabela) do Pandas
        df_ids = pd.read_sql(query, con=engine)
        print(f"Encontrados {len(df_ids)} identificadores para o estado de {estado}.")
        return df_ids['identificador_único'].tolist() # Transforma a coluna da tabela numa lista do Python
    except Exception as e:
        print(f"Erro ao consultar a tabela '{source_table_name}': {e}")
        return []

# ==============================================================================
# --- FUNÇÃO: CONSULTAR A API DE EXECUÇÃO FÍSICA ---
# ==============================================================================
def fetch_physical_data(project_id):
    """Bate na API pedindo os dados de execução física de UMA obra específica."""
    all_data = [] # Caixinha para guardar as respostas da API
    page = 0 # Controle de paginação (começa na página 0)
    clean_pid = str(project_id).strip() # Converte o ID pra texto e tira espaços em branco nas pontas
    
    while True: # Loop infinito para varrer todas as páginas daquela obra
        # Parâmetros que vão na URL (atenção: nesta API o nome do parâmetro é 'idUnico')
        params = {
            "idUnico": clean_pid,
            "pagina": page,
            "tamanhoDaPagina": 100 # Pede até 100 registros de uma vez
        }
        try:
            # Faz a chamada na web
            response = requests.get(API_URL, params=params, headers=API_HEADERS, timeout=30)
            
            # --- PROTEÇÃO CONTRA BLOQUEIO (RATE LIMIT) ---
            if response.status_code == 429: # Se a API disser "Too Many Requests"
                print(f"!!! ERRO 429 - LIMITE ATINGIDO para {clean_pid}. Esperando 60 segundos...")
                time.sleep(60) # Dorme por 1 minuto inteiro
                continue # Tenta fazer a requisição desta mesma página novamente
            # -------------------------------------------

            response.raise_for_status() # Verifica se deu algum outro erro (500, 404)
            data = response.json() # Transforma o texto da web em um Dicionário Python
            
            content = data.get("content", []) # Pega só o miolo dos dados
            if not content: # Se o miolo estiver vazio, não tem mais dados
                break
            
            # Percorre os dados retornados e injeta a nossa coluna 'id_unico' em cada linha
            # Isso é fundamental para não perdermos a rastreabilidade da obra no banco
            for item in content:
                item['id_unico'] = clean_pid
            
            all_data.extend(content) # Junta os dados dessa página com os dados totais da obra
            
            if data.get("last", False): # A própria API avisa se a página atual é a última.
                break # Se for, quebra o loop
            
            page += 1 # Vai pra página seguinte
            time.sleep(random.uniform(1, 2)) # Pausa aleatória para evitar tomar bloqueio (Erro 429)

        except requests.exceptions.RequestException as e: # Se a internet oscilar ou o site cair
            print(f"AVISO: Erro na requisição para o ID {clean_pid} (página {page}): {e}")
            break
    
    return all_data # Devolve a lista final com todos os dados daquela obra

# ==============================================================================
# --- CORAÇÃO DO SCRIPT: FUNÇÃO PRINCIPAL ---
# ==============================================================================
def process_and_load_data():
    """Função que gerencia o fluxo: pega ID -> vai na web -> processa -> salva no banco."""
    engine = get_db_connection() # Liga a conexão com o banco
    if not engine:
        sys.exit(1)

    # NOVO: Pega a data e hora exata em que este script começou a rodar
    current_timestamp = datetime.now()

    # Nomes das colunas esperadas especificamente para a Execução Física
    column_names = [
        'id_unico', 'idUnico', 'percentual', 'dataSituacao', 'situacao', 'observacoes', 
        'emOperacao', 'justificativaEmOperacao', 'cancelamentosParalisacoes', 'documentos'
    ]

    # Inicia a leitura estado por estado
    for estado in estados:
        print(f"\n--- Iniciando processamento para o estado: {estado} ---")
        
        project_ids = get_project_ids_by_state(engine, estado) # Pede pro banco os IDs do estado
        if not project_ids:
            print(f"Nenhum ID de projeto encontrado para o estado {estado}. Pulando para o próximo.")
            continue
        
        estado_data = [] # Caixinha geral que vai acumular os dados do estado todo
        
        # Loop passando por cada obra (ID) daquele estado
        for pid in project_ids:
            
            clean_pid = str(pid).strip()
            data_from_api = fetch_physical_data(clean_pid) # Chama a função que busca na web
            
            if data_from_api: # Se a API devolveu informações de execução física
                print(f"Dados encontrados para o projeto ID: {clean_pid}. Total de registros: {len(data_from_api)}")
                estado_data.extend(data_from_api) # Guarda na caixinha do estado
            else:
                # Se não houver nada, cria uma linha "fantasma" (placeholder) cheia de traços '-'
                print(f"Nenhum dado encontrado para o projeto ID: {clean_pid}. Criando registro placeholder...")
                placeholder_record = {col: '-' for col in column_names}
                
                # Preenche com o ID real pra linha não ficar órfã no banco
                placeholder_record['id_unico'] = clean_pid
                placeholder_record['idUnico'] = clean_pid
                estado_data.append(placeholder_record)
            
            # --- PAUSA DE SEGURANÇA ---
            # Espera de 2 a 3 segundos antes de bater na API de novo pedindo a próxima obra
            time.sleep(random.uniform(2, 3)) 
            # --------------------------------------------------------

        if not estado_data: # Se no final não tiver nem linhas reais nem fantasmas
            print(f"Nenhum dado, nem registro placeholder, encontrado para o estado {estado}. Nenhuma tabela será criada.")
            continue

        # Transforma a lista de dados brutos numa tabela estruturada (DataFrame) do Pandas
        df = pd.DataFrame(estado_data)

        # --- PADRONIZAÇÃO DE COLUNAS ---
        # Troca os nomes do formato web (camelCase) para o formato do banco de dados (snake_case)
        df = df.rename(columns={
            'id_unico': 'id_unico',
            'idUnico': 'id_unico_api',
            'dataSituacao': 'data_situacao',
            'emOperacao': 'em_operacao',
            'justificativaEmOperacao': 'justificativa_em_operacao',
            'cancelamentosParalisacoes': 'cancelamentos_paralisacoes'
            # A coluna 'documentos' (que geralmente vem como um array/lista) é mantida com o mesmo nome
        })

        # --- A GRANDE ADIÇÃO DESTE SCRIPT ---
        # Cria uma coluna nova na tabela com o carimbo de tempo da extração.
        # Isso permite diferenciar dados extraídos hoje de dados extraídos no mês passado.
        df['data_execucao'] = current_timestamp

        # Define o nome da tabela no banco (Ex: estados_mg_execucao_fisica)
        target_table_name = f'estados_{estado.lower()}_execucao_fisica'

        try:
            print(f"\nAnexando {len(df)} registros à tabela histórica '{target_table_name}'...")
            
            # MUDANÇA CRUCIAL: 'if_exists='append''
            # Em vez de apagar a tabela e recriar ('replace'), o Pandas vai colocar as linhas novas 
            # no FINAL da tabela existente. Isso constrói o seu histórico ao longo dos meses!
            df.to_sql(name=target_table_name, con=engine, if_exists='append', index=False)
            
            print(f"Dados de Execução Física de {estado} anexados com sucesso na tabela '{target_table_name}'.")
        except Exception as e:
            print(f"ERRO ao salvar dados na tabela '{target_table_name}': {e}")
    
    print("\nProcessamento de todos os estados concluído.")

# Gatilho que inicia a execução do script
if __name__ == "__main__":
    process_and_load_data()