# ==============================================================================
# --- IMPORTAÇÕES ---
# Ferramentas necessárias para banco de dados, web e tabelas.
# ==============================================================================
import psycopg2  # Adaptador de conexão para o PostgreSQL
import requests  # Para acessar a API do Governo na web
import pandas as pd  # A estrela do show, manipula as tabelas (DataFrames)
from sqlalchemy import create_engine  # O motor que conecta o Pandas ao PostgreSQL
from psycopg2 import OperationalError  # Captura falhas específicas de conexão do banco
import time  # Para pausar o robô
import sys  # Para comandos do sistema (como fechar o script)
import random  # Para pausas aleatórias (humanização/evitar bloqueio)
from datetime import datetime  # Para registrar o exato momento (carimbo de data/hora) da extração

# ==============================================================================
# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# ==============================================================================
DB_HOST = "localhost" # Servidor de banco de dados na sua própria máquina
DB_USER = "postgres" # Usuário mestre do banco
DB_PASSWORD = "cb2907cb"  # Senha do banco
DB_PORT = "5432" # Porta padrão do PostgreSQL
TARGET_DB_NAME = "minhas_obras" # Nome do seu banco de dados criado no PgAdmin

# ==============================================================================
# --- CONFIGURAÇÕES DA API ---
# ==============================================================================
# Nova URL da API do governo. Repare que agora o foco é o "saldo-contabil"
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira/saldo-contabil"
API_HEADERS = {"accept": "*/*"} # Diz pra API que aceitamos o formato padrão que ela enviar

# Lista de todos os estados do Brasil para o loop percorrer
estados = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

# ==============================================================================
# --- FUNÇÃO: CONEXÃO COM O BANCO ---
# ==============================================================================
def get_db_connection():
    """Cria a ponte entre o Python e o banco de dados PostgreSQL."""
    try:
        # String de conexão usando SQLAlchemy. O Pandas precisa desse 'engine' para ler/escrever.
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
        print("Conexão com o banco de dados estabelecida com sucesso.")
        return engine # Devolve o motor ligado
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados '{TARGET_DB_NAME}': {e}")
        return None

# ==============================================================================
# --- FUNÇÃO: BUSCAR PARES (UG, ID) NO BANCO DE DADOS ---
# ==============================================================================
def obter_ug(engine, estado):
    """
    Vai na tabela anterior que você gerou no banco (a de detalhes financeiros)
    e extrai quem é a Unidade Gestora (UG) responsável por cada Obra (ID).
    """
    # Ex: se o estado for 'SC', vira 'estados_sc_execucaofinanceira_detalhes'
    nome_tabela_origem = f'estados_{estado.lower()}_execucaofinanceira_detalhes'
    print(f"Buscando pares (UG, ID_UNICO) na tabela '{nome_tabela_origem}'...")
    
    # Query (Consulta) em linguagem SQL
    # DISTINCT: Garante que não vai trazer linhas repetidas da mesma UG cuidando da mesma Obra duas vezes
    query = f"""
        SELECT 
            DISTINCT ug_emitente, 
            id_projeto_investimento AS id_unico 
        FROM {nome_tabela_origem} 
        WHERE ug_emitente != '-' AND id_projeto_investimento != '-' 
    """ # A cláusula WHERE ignora as obras "fantasmas" (os placeholders '-') do script anterior
    
    try:
        # Manda a query pro banco e devolve um DataFrame (Tabela do Pandas)
        df_pares = pd.read_sql(query, con=engine)
        
        # Limpeza fina: Garante que os números que vieram do banco são tratos como texto (str) 
        # e o 'strip()' remove os espaços em branco que possam estar em volta deles.
        df_pares['ug_emitente'] = df_pares['ug_emitente'].astype(str).str.strip()
        df_pares['id_unico'] = df_pares['id_unico'].astype(str).str.strip()
        
        print(f"Encontrados {len(df_pares)} pares (UG, ID_UNICO) distintos para o estado de {estado}.")
        return df_pares # Devolve a tabela limpinha pro loop
        
    except Exception as e: # Se a tabela não existir (ex: não rodou o script anterior pra esse estado)
        print(f"Erro ao consultar a tabela '{nome_tabela_origem}'. Verifique se o script anterior foi executado: {e}")
        return pd.DataFrame() # Devolve uma tabela vazia e o script segue sem travar

# ==============================================================================
# --- FUNÇÃO: BATER NA API DO GOVERNO ---
# ==============================================================================
def obter_dados_financeiros(ug_emitente):
    """Bate na API pedindo o extrato/saldo daquela Unidade Gestora (Prefeitura, Ministério, etc)."""
    dados = [] # Caixinha para guardar as páginas da resposta
    pag = 0 # Inicia na página 0 (na web as páginas costumam começar do zero)
    limpar_ug = str(ug_emitente).strip() # Limpa o código da UG
    
    while True: # Loop infinito que só para quando a API disser "acabaram as páginas"
        params = {
            "ugEmitente": limpar_ug, # O código que será pesquisado
            "pagina": pag, # Qual página eu quero ver agora
            "tamanhoDaPagina": 100 # Me dê até 100 itens por página
        }
        try:
            # Envia a requisição GET para o governo
            response = requests.get(API_URL, params=params, headers=API_HEADERS, timeout=30)
            
            # --- PROTEÇÃO ANTI-BLOQUEIO (ERRO 429) ---
            if response.status_code == 429: # "Too Many Requests" (Fomos muito rápidos)
                print(f"!!! ERRO 429 - LIMITE ATINGIDO para a UG {limpar_ug}. Esperando 60 segundos...")
                time.sleep(60) # Tira o pé do acelerador por 1 minuto
                continue # Volta para o "while True" sem avançar a página
            # -------------------------------------------

            response.raise_for_status() # Verifica outros erros bizarros da web (Ex: 500 erro de servidor)
            data = response.json() # Traduz a resposta para um formato lido pelo Python (Dicionário)
            
            content = data.get("content", []) # Puxa o "miolo" dos dados
            if not content: # Se o miolo estiver vazio, acabou.
                break

            dados.extend(content) # Junta o miolo novo com o que já foi guardado nas páginas anteriores

            if data.get("last", False): # Se o miolo vier com o aviso "last: true" (última página)...
                break # Quebra o loop infinito
            
            pag += 1 # Vai pra próxima página
            time.sleep(random.uniform(1, 2)) # Pausa curta pra não dar erro 429 nas páginas

        except requests.exceptions.RequestException as e: # Se a internet oscilar forte
            print(f"AVISO: Erro na requisição para a UG {limpar_ug} (página {pag}): {e}")
            break # Abandona a busca dessa UG e segue a vida
    
    return dados # Devolve tudo o que achou daquela UG

# ==============================================================================
# --- CORAÇÃO DO SCRIPT: FUNÇÃO PRINCIPAL ---
# ==============================================================================
def process_and_load_data():
    """Função mestre: lê os dados velhos no banco, consulta a API e salva os dados novos no banco."""
    engine = get_db_connection() # Liga o motor do banco
    if not engine: # Sem banco não dá pra trabalhar
        sys.exit(1) # Mata o script

    # Marca exata de que horas o script rodou (vai virar uma coluna no banco depois)
    current_timestamp = datetime.now() 

    # Uma lista fixa das colunas que a API promete devolver
    column_names = [
        'ugEmitente', 'nrNotaEmpenho', 'vlTransferidoExercicioAnterior', 'vlTransferido', 
        'vlRestosAPagar', 'vlReinscritoRp', 'vlReforcado', 'vlRecebidoTransferido', 
        'vlRecebidoExercicioAnterior', 'vlPago', 'vlLiquidadoAPagar', 'vlInscritoRp', 
        'vlIncluido', 'unidadeOrcamentaria', 'vlEmLiquidacao', 
        'vlCanceladoExercicioAnterior', 'vlAnuladoCancelado', 'vlALiquidar', 
        'id_unico' # Essa coluna não vem na API, fomos nós que inventamos!
    ]

    # --- INÍCIO DO LOOP DOS ESTADOS ---
    for estado in estados:
        print(f"\n--- Iniciando processamento para o estado: {estado} ---")
        
        # Pede pro banco as UGs daquele estado
        ug_id_pairs_df = obter_ug(engine, estado) 
        
        if ug_id_pairs_df.empty: # Se a tabela vier vazia
            print(f"Nenhum par (UG, ID_UNICO) encontrado para o estado {estado}. Pulando.")
            continue # Vai pro próximo estado
        
        # SACA AQUI: O Pandas olha a coluna das UGs e tira todas as repetições (unique).
        # Assim, se uma Prefeitura cuida de 10 escolas, a gente só pesquisa ela na API UMA vez. Genial.
        unique_ugs = ug_id_pairs_df['ug_emitente'].unique().tolist()
        
        estado_data = [] # Caixinha geral dos dados do estado
        
        # --- INÍCIO DO LOOP DAS UNIDADES GESTORAS (UGs) ---
        for ug in unique_ugs:
            
            # Vai na web pesquisar a UG
            data_from_api = obter_dados_financeiros(ug)
            
            # Se vier dinheiro (dados) da API...
            if data_from_api:
                print(f"Dados encontrados para a UG: {ug}. Total de registros: {len(data_from_api)}")
                
                # ...Agora precisamos espalhar esse saldo para TODAS as obras vinculadas a ela.
                
                # 1º Passo: Olha naquela primeira tabela do banco quais são os "id_unico" (obras) amarrados a essa 'ug'
                associated_ids = ug_id_pairs_df[ug_id_pairs_df['ug_emitente'] == ug]['id_unico'].tolist()
                
                # 2º Passo: Para CADA item financeiro que a API devolveu...
                for item in data_from_api:
                    # 3º Passo: ...Eu duplico esse item financeiro para CADA obra (ID) que a UG administra.
                    for id_projeto in associated_ids:
                        new_item = item.copy() # Tira uma "xerox" do dado financeiro
                        new_item['id_unico'] = id_projeto # Cola o ID da obra na "xerox"
                        estado_data.append(new_item) # E guarda na caixinha do estado
                        
            # Se a API disser que essa UG não tem nada...
            else:
                print(f"Nenhum dado encontrado para a UG: {ug}. Criando registro placeholder...")
                # Pega as obras associadas a ela
                associated_ids = ug_id_pairs_df[ug_id_pairs_df['ug_emitente'] == ug]['id_unico'].tolist()
                
                # Para cada obra, eu crio uma linha "fantasma" cheia de '-' (placeholder)
                for id_projeto in associated_ids:
                    placeholder_record = {col: '-' for col in column_names} # Preenche de '-'
                    placeholder_record['ugEmitente'] = ug # Salva a UG
                    placeholder_record['id_unico'] = id_projeto # Salva a obra (ID)
                    estado_data.append(placeholder_record) # Guarda a linha fantasma
            
            # --- PAUSA DE SEGURANÇA ---
            # O robô dorme uns segundinhos antes de pesquisar a próxima UG para não irritar o firewall do governo.
            time.sleep(random.uniform(2, 3)) 
            # ------------------------------------------------

        if not estado_data: # Se no final de tudo o estado inteiro não tiver tido 1 real de saldo...
            print(f"Nenhum dado encontrado para o estado {estado}. Nenhuma tabela de saldo contábil será modificada.")
            continue # Vai pro próximo estado

        # Pega a super caixinha com as linhas duplicadas/fantasmas e vira um DataFrame (tabela oficial)
        df = pd.DataFrame(estado_data)

        # --- PADRONIZAÇÃO DE COLUNAS ---
        # Renomeia tudo do padrão web (camelCase) para o padrão banco de dados (snake_case)
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

        # --- O CARIMBO DO TEMPO ---
        # Adiciona uma coluna nova no banco indicando a hora exata que essa linha foi salva lá.
        df['data_execucao'] = current_timestamp

        # Define qual será o nome da tabela que vai receber tudo isso no PostgreSQL
        target_table_name = f'estados_{estado.lower()}_saldo_contabil'

        try:
            print(f"\nAnexando {len(df)} registros (UGs e IDs de Projeto) à tabela histórica '{target_table_name}'...")
            
            # --- A MÁGICA FINAL DO PANDAS ---
            # Manda a tabela pro banco de dados. 
            # IMPORTANTE: if_exists='append'. Ao contrário do script anterior (que deletava e recriava), 
            # esse aqui ADICIONA (anexa) os dados novos no final da tabela que já existe! 
            # É assim que se constrói um histórico/linha do tempo em bancos de dados.
            df.to_sql(name=target_table_name, con=engine, if_exists='append', index=False)
            
            print(f"Dados de Saldo Contábil de {estado} anexados com sucesso na tabela '{target_table_name}'.")
        except Exception as e: # Se o banco de dados travar
            print(f"ERRO ao salvar dados na tabela '{target_table_name}': {e}")
    
    print("\nProcessamento de todos os estados concluído.")

# Ordem do sistema operacional para iniciar o código aqui.
if __name__ == "__main__":
    process_and_load_data()