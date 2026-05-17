# ==============================================================================
# --- IMPORTAÇÕES ---
# Módulos necessários para banco de dados, requisições HTTP e tabelas.
# ==============================================================================
import psycopg2  # Adaptador para conectar o Python ao PostgreSQL
import requests  # Para realizar chamadas na API do Governo
import pandas as pd  # Para manipular os dados no formato de tabela (DataFrame)
from sqlalchemy import create_engine  # Motor que traduz a linguagem do Pandas para o banco de dados
from psycopg2 import OperationalError  # Para capturar problemas na conexão do banco
import time  # Para gerar pausas no código
import sys  # Para comandos do sistema (como encerrar a execução)
import random # Para gerar tempos aleatórios nas pausas (evita padrão robótico)

# ==============================================================================
# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# ==============================================================================
DB_HOST = "localhost" # O banco roda no próprio computador
DB_USER = "postgres" # Usuário administrador
DB_PASSWORD = "cb2907cb"  # Senha do banco
DB_PORT = "5432" # Porta de conexão padrão do PostgreSQL
TARGET_DB_NAME = "minhas_obras" # Nome do banco de dados alvo

# ==============================================================================
# --- URL DA API ---
# ==============================================================================
# URL apontando especificamente para os dados gerais do Projeto de Investimento
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/projeto-investimento"
API_HEADERS = {"accept": "*/*"} # Informa ao servidor que aceitamos qualquer formato de resposta

# Lista completa de estados brasileiros que o robô vai percorrer
estados = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

# ==============================================================================
# --- FUNÇÃO: CONEXÃO COM O BANCO ---
# ==============================================================================
def get_db_connection():
    """Cria e devolve o motor de conexão com o PostgreSQL."""
    try:
        # Monta a rota de conexão que o SQLAlchemy vai usar
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
        print("Conexão com o banco de dados estabelecida com sucesso.")
        return engine # Devolve a conexão pronta
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados '{TARGET_DB_NAME}': {e}")
        return None

# ==============================================================================
# --- FUNÇÃO: BUSCAR IDs DOS PROJETOS NO BANCO ---
# ==============================================================================
def get_project_ids_by_state(engine, estado):
    """Acessa a tabela base do estado e extrai a lista de Identificadores Únicos."""
    source_table_name = f'estados_{estado}'.lower() # Monta o nome da tabela (ex: estados_mt)
    print(f"Buscando identificadores únicos na tabela '{source_table_name}'...")
    
    # Query SQL: seleciona apenas a coluna que precisamos
    query = f'SELECT "identificador_único" FROM {source_table_name}'
    
    try:
        # Puxa os dados e joga numa tabela (DataFrame) do Pandas
        df_ids = pd.read_sql(query, con=engine)
        print(f"Encontrados {len(df_ids)} identificadores para o estado de {estado}.")
        return df_ids['identificador_único'].tolist() # Retorna os números formatados como uma lista do Python
    except Exception as e:
        print(f"Erro ao consultar a tabela '{source_table_name}': {e}")
        return []

# ==============================================================================
# --- FUNÇÃO: CONSULTAR A API DE PROJETOS DE INVESTIMENTO ---
# ==============================================================================
def fetch_project_data(project_id):
    """Bate na API pedindo os detalhes cadastrais de uma obra específica."""
    all_data = [] # Lista que vai acumular todos os retornos
    page = 0 # Define a página inicial como 0
    
    while True: # Inicia o loop para buscar página por página
        clean_pid = str(project_id).strip() # Converte o ID pra string e remove espaços ocultos
        
        # Parâmetros enviados na URL para a API do Governo
        params = {
            "idUnico": clean_pid, # ID da obra
            "pagina": page, # Número da página
            "tamanhoDaPagina": 100 # Quantidade de registros por vez
        }
        try:
            # Chama a API com tempo máximo de espera de 30 segundos
            response = requests.get(API_URL, params=params, headers=API_HEADERS, timeout=30)
            
            # --- TRATAMENTO DE BLOQUEIO (RATE LIMIT) ---
            if response.status_code == 429: # Se o governo barrar por excesso de velocidade
                print(f"!!! ERRO 429 - LIMITE ATINGIDO para {clean_pid}. Esperando 60 segundos...")
                time.sleep(60) # Espera o tempo de "castigo" de 1 minuto
                continue # Volta ao topo do "while" para tentar a mesma página de novo
            # -------------------------------------------------------

            response.raise_for_status() # Verifica falhas severas de conexão (como Erro 500)
            data = response.json() # Transforma o formato web num Dicionário Python legível
            
            content = data.get("content", []) # Isola só a lista de dados brutos
            if not content: # Se não vier conteúdo nenhum...
                break # Sai do loop infinito
            
            # Percorre a resposta inserindo o ID original para mantermos a referência no nosso banco
            for item in content:
                item['id_unico'] = clean_pid
            
            all_data.extend(content) # Anexa o conteúdo da página atual no "bolsão" geral da obra
            
            if data.get("last", False): # A API retorna "last: true" quando for a última página
                break # E então quebramos o loop
            
            page += 1 # Prepara o loop para puxar a próxima página
            time.sleep(random.uniform(1, 2)) # Pausa rápida entre páginas para evitar ser pego no Erro 429

        except requests.exceptions.RequestException as e: # Se a internet cair ou der erro de rede
            print(f"AVISO: Erro na requisição para o ID {clean_pid} (página {page}): {e}")
            break
    
    return all_data # Devolve a lista final com todos os dados da obra

# ==============================================================================
# --- CORAÇÃO DO SCRIPT: FUNÇÃO PRINCIPAL ---
# ==============================================================================
def process_and_load_data():
    """Gerencia toda a esteira: Lê banco -> Lê Web -> Prepara tabela -> Salva banco."""
    engine = get_db_connection() # Liga a conexão do PostgreSQL
    if not engine:
        sys.exit(1)

    # Nomes esperados de TODAS as colunas que a API de Projeto de Investimento retorna
    column_names = [
        'id_unico', 'idUnico', 'nome', 'cep', 'endereco', 'descricao', 'funcaoSocial', 
        'metaGlobal', 'dataInicialPrevista', 'dataFinalPrevista', 'dataInicialEfetiva', 
        'dataFinalEfetiva', 'dataCadastro', 'especie', 'natureza', 'naturezaOutras', 
        'situacao', 'descPlanoNacionalPoliticaVinculado', 'uf', 'qdtEmpregosGerados', 
        'descPopulacaoBeneficiada', 'populacaoBeneficiada', 'observacoesPertinentes', 
        'isModeladaPorBim', 'dataSituacao', 'tomadores', 'executores', 'repassadores', 
        'eixos', 'tipos', 'subtipos', 'geometrias', 'fontesDeRecurso'
    ]

    # Inicia a leitura do país, estado por estado
    for estado in estados:
        print(f"\n--- Iniciando processamento para o estado: {estado} ---")
        
        # Chama a função que lê os IDs das obras na tabela daquele estado
        project_ids = get_project_ids_by_state(engine, estado)
        if not project_ids: # Se a tabela não tiver nada
            print(f"Nenhum ID de projeto encontrado para o estado {estado}. Pulando para o próximo.")
            continue
        
        estado_data = [] # Caixinha mestra para guardar as obras do estado inteiro
        
        for pid in project_ids: # Inicia o loop para processar obra por obra
            
            # Chama a função que busca os detalhes na API
            data_from_api = fetch_project_data(pid)
            
            clean_pid = str(pid).strip() # Limpa o ID para as mensagens no terminal

            if data_from_api: # Se a obra existir e vier com dados
                print(f"Dados encontrados para o projeto ID: {clean_pid}. Total de registros: {len(data_from_api)}")
                estado_data.extend(data_from_api) # Joga na caixinha do estado
            else:
                # Se não vier nada da API, criamos um registro "fantasma" (placeholder)
                print(f"Nenhum dado encontrado para o projeto ID: {clean_pid}. Criando registro placeholder...")
                placeholder_record = {col: '-' for col in column_names} # Preenche as colunas com traço '-'
                placeholder_record['id_unico'] = clean_pid # Preserva o ID limpo
                placeholder_record['idUnico'] = clean_pid # Preserva na coluna original da API também
                estado_data.append(placeholder_record) # Joga na caixinha

            # --- CORREÇÃO APLICADA AQUI: Atraso maior entre cada ID de projeto ---
            # Pausa de 2 a 3 segundos antes da próxima obra para dar "respiro" à API do governo
            time.sleep(random.uniform(2, 3)) 
            # --------------------------------------------------------------------

        if not estado_data: # Se no final do loop não existir nem dado real nem fantasma
            print(f"Nenhum dado encontrado para o estado {estado}. Nenhuma tabela será criada.")
            continue

        # Transforma a grande lista de dicionários em uma Tabela do Pandas
        df = pd.DataFrame(estado_data)

        # --- PADRONIZAÇÃO DE COLUNAS ---
        # Converte as colunas de "camelCase" (padrão de programadores web) 
        # para "snake_case" (padrão oficial de banco de dados relacional).
        df = df.rename(columns={
            'id_unico': 'id_unico',
            'idUnico': 'id_unico_api',
            'funcaoSocial': 'funcao_social',
            'metaGlobal': 'meta_global',
            'dataInicialPrevista': 'data_inicial_prevista',
            'dataFinalPrevista': 'data_final_prevista',
            'dataInicialEfetiva': 'data_inicial_efetiva',
            'dataFinalEfetiva': 'data_final_efetiva',
            'dataCadastro': 'data_cadastro',
            'naturezaOutras': 'natureza_outras',
            'descPlanoNacionalPoliticaVinculado': 'desc_plano_nacional_politica_vinculado',
            'qdtEmpregosGerados': 'qdt_empregos_gerados',
            'descPopulacaoBeneficiada': 'desc_populacao_beneficiada',
            'populacaoBeneficiada': 'populacao_beneficiada',
            'observacoesPertinentes': 'observacoes_pertinentes',
            'isModeladaPorBim': 'is_modelada_por_bim',
            'dataSituacao': 'data_situacao',
            'fontesDeRecurso': 'fontes_de_recurso'
            # Note que colunas simples como 'nome', 'cep', 'uf' e arrays/listas 
            # como 'tipos' e 'executores' ficam com os nomes que vieram de fábrica
        })

        # Define o nome da tabela alvo (ex: estados_pe_projeto_investimento)
        target_table_name = f'estados_{estado.lower()}_projeto_investimento'

        try:
            print(f"\nSalvando {len(df)} registros na tabela '{target_table_name}'...")
            
            # --- CARGA (LOAD) NO BANCO DE DADOS ---
            # Se a tabela existir no banco, ele vai deletar e recriar com esses novos dados ('replace')
            df.to_sql(name=target_table_name, con=engine, if_exists='replace', index=False)
            
            print(f"Dados cadastrais de {estado} salvos com sucesso na tabela '{target_table_name}'.")
        except Exception as e:
            print(f"ERRO ao salvar dados na tabela '{target_table_name}': {e}")
    
    print("\nProcessamento de todos os estados concluído.")

# Chama a função que inicia todo o processo
if __name__ == "__main__":
    process_and_load_data()