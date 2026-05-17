# ==============================================================================
# --- IMPORTAÇÕES ---
# Ferramentas necessárias para banco de dados, web e tabelas.
# ==============================================================================
import psycopg2  # Adaptador para o Python conversar com o PostgreSQL
import requests  # Para acessar a API do Governo na web
import pandas as pd  # Para manipular os dados em formato de tabela
from sqlalchemy import create_engine  # O motor que conecta o Pandas ao banco de dados
from psycopg2 import OperationalError  # Captura de erros de banco
import time  # Para pausar o script (esperas fixas)
import sys  # Para comandos do sistema (como fechar o programa)
import random # Para adicionar um atraso randômico (humanizar o robô)

# ==============================================================================
# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# ==============================================================================
DB_HOST = "localhost" # O servidor de banco de dados (sua máquina)
DB_USER = "postgres" # Usuário administrador
DB_PASSWORD = "cb2907cb"  # Senha de acesso
DB_PORT = "5432" # Porta de comunicação padrão
TARGET_DB_NAME = "minhas_obras" # Nome do banco onde as tabelas estão/serão criadas

# ==============================================================================
# --- URL DA API ---
# ==============================================================================
# Novo endpoint focado nos CONTRATOS da execução financeira
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira/contrato"
API_HEADERS = {"accept": "*/*"} # Aceitamos qualquer formato de resposta

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
        # String de conexão usando SQLAlchemy
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
        print("Conexão com o banco de dados estabelecida com sucesso.")
        return engine # Devolve o motor pronto para uso
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados '{TARGET_DB_NAME}': {e}")
        return None

# ==============================================================================
# --- FUNÇÃO: BUSCAR IDs DOS PROJETOS NO BANCO ---
# ==============================================================================
def get_project_ids_by_state(engine, estado):
    """Vai na tabela base do estado e extrai a lista de Identificadores Únicos (Obras)."""
    source_table_name = f'estados_{estado}'.lower() # Monta o nome da tabela (ex: estados_ac)
    print(f"Buscando identificadores únicos na tabela '{source_table_name}'...")
    
    # Query SQL para pegar só a coluna que importa
    query = f'SELECT "identificador_único" FROM {source_table_name}'
    
    try:
        # Puxa os dados do banco e transforma num DataFrame (Tabela Pandas)
        df_ids = pd.read_sql(query, con=engine)
        print(f"Encontrados {len(df_ids)} identificadores para o estado de {estado}.")
        return df_ids['identificador_único'].tolist() # Converte a coluna numa lista simples do Python
    except Exception as e:
        print(f"Erro ao consultar a tabela '{source_table_name}': {e}")
        return []

# ==============================================================================
# --- FUNÇÃO: CONSULTAR A API DE CONTRATOS ---
# ==============================================================================
def fetch_financial_data(project_id):
    """Bate na API do governo pedindo os contratos de UM projeto (obra) específico."""
    all_data = [] # Caixinha vazia para guardar as páginas da API
    page = 0 # Controle da página atual
    clean_pid = str(project_id).strip() # Limpa o número do ID (tira espaços)
    
    while True: # Loop infinito de paginação
        # Parâmetros enviados na URL da requisição
        params = {
            "idProjetoInvestimento": clean_pid,
            "pagina": page,
            "tamanhoDaPagina": 100 # Pede 100 de uma vez
        }
        try:
            # Dispara a requisição GET
            response = requests.get(API_URL, params=params, headers=API_HEADERS, timeout=30)
            
            # --- PROTEÇÃO DE BLOQUEIO (RATE LIMIT) ---
            if response.status_code == 429: # Se a API reclamar que estamos muito rápidos
                print(f"!!! ERRO 429 - LIMITE ATINGIDO para {clean_pid}. Esperando 60 segundos...")
                time.sleep(60) # Espera 1 minuto para o firewall acalmar
                continue # Tenta de novo a mesma página
            # -------------------------------------------

            response.raise_for_status() # Grita se der erro 500 ou 404
            data = response.json() # Converte a resposta pra Dicionário
            
            content = data.get("content", []) # Pega o miolo dos dados
            if not content: # Se não vier nada, acabou
                break
            
            # Injeta o ID da obra dentro de cada contrato, pra sabermos de quem é depois
            for item in content:
                item['id_unico'] = clean_pid
            
            all_data.extend(content) # Junta os contratos novos com os velhos
            
            if data.get("last", False): # Se for a última página...
                break # Quebra o loop
            
            page += 1 # Vai pra página 2, 3, 4...
            time.sleep(random.uniform(1, 2)) # Pausa curta pra não dar Erro 429 nas páginas

        except requests.exceptions.RequestException as e: # Se a net cair
            print(f"AVISO: Erro na requisição para o ID {clean_pid} (página {page}): {e}")
            break
    
    return all_data # Devolve o pacotão de contratos dessa obra

# ==============================================================================
# --- FUNÇÃO PRINCIPAL: ORQUESTRAÇÃO GERAL ---
# ==============================================================================
def process_and_load_data():
    """Função mestre: pega ID no banco, pesquisa contrato na web, salva contrato no banco."""
    engine = get_db_connection() # Liga o motor
    if not engine:
        sys.exit(1)

    # Nomes das colunas esperadas (Específicas de Contratos)
    column_names = [
        'id_unico', 'idProjetoInvestimento', 'numeroContrato', 'vigenciaInicio', 'vigenciaFim',
        'dataAssinatura', 'dataPublicacao', 'objeto', 'processo',
        'receitaDespesa', 'codigoOrgao', 'orgaoNome', 'fornecedorCnpjCpfIdgener',
        'fornecedorNome', 'categoria', 'licitacaoNumero', 'valorGlobal',
        'valorAcumulado', 'codigoContrato', 'foraVigencia', 'nrCtrlePncpCompra'
    ]

    # Inicia a varredura por Estado
    for estado in estados:
        print(f"\n--- Iniciando processamento para o estado: {estado} ---")
        
        project_ids = get_project_ids_by_state(engine, estado) # Pega os IDs no banco
        if not project_ids:
            print(f"Nenhum ID de projeto encontrado para o estado {estado}. Pulando para o próximo.")
            continue
        
        estado_data = [] # Bolsão para guardar os contratos do Estado inteiro
        
        for pid in project_ids:
            
            # A limpeza do ID é feita dentro da função fetch_financial_data, mas aqui ele limpa pro print
            clean_pid = str(pid).strip() 
            data_from_api = fetch_financial_data(pid) # Manda buscar na web
            
            if data_from_api: # Se vieram contratos...
                print(f"Dados encontrados para o projeto ID: {clean_pid}. Total de registros: {len(data_from_api)}")
                estado_data.extend(data_from_api) # Guarda no bolsão
            else:
                # Se não vier ABSOLUTAMENTE NADA de contrato, cria uma linha "fantasma" de marcação
                print(f"Nenhum dado encontrado para o projeto ID: {clean_pid}. Criando registro placeholder...")
                # Preenche todas as colunas com '-'
                placeholder_record = {col: '-' for col in column_names}
                # Preenche os IDs corretos pra linha não ficar órfã
                placeholder_record['id_unico'] = clean_pid
                placeholder_record['idProjetoInvestimento'] = clean_pid
                estado_data.append(placeholder_record) # Guarda a linha fantasma no bolsão
            
            # --- PAUSA DE SEGURANÇA ---
            # Tempo de espera de 2 a 3 segundos entre obras (evitar Erro 429)
            time.sleep(random.uniform(2, 3)) 
            # --------------------------------------------------------

        if not estado_data:
            print(f"Nenhum dado, nem registro placeholder, encontrado para o estado {estado}. Nenhuma tabela será criada.")
            continue

        # Transforma a sacola gigante de contratos do Estado num DataFrame oficial
        df = pd.DataFrame(estado_data)

        # --- PADRONIZAÇÃO DE COLUNAS ---
        # Troca o padrão da web (camelCase) para o padrão banco de dados (snake_case)
        df = df.rename(columns={
            'idProjetoInvestimento': 'id_projeto_investimento',
            'numeroContrato': 'numero_contrato',
            'vigenciaInicio': 'vigencia_inicio',
            'vigenciaFim': 'vigencia_fim',
            'dataAssinatura': 'data_assinatura',
            'dataPublicacao': 'data_publicacao',
            'receitaDespesa': 'receita_despesa',
            'codigoOrgao': 'codigo_orgao',
            'orgaoNome': 'orgao_nome',
            'fornecedorCnpjCpfIdgener': 'fornecedor_cnpj_cpf_idgener',
            'fornecedorNome': 'fornecedor_nome',
            'licitacaoNumero': 'licitacao_numero',
            'valorGlobal': 'valor_global',
            'valorAcumulado': 'valor_acumulado',
            'codigoContrato': 'codigo_contrato',
            'foraVigencia': 'fora_vigencia',
            'nrCtrlePncpCompra': 'nr_ctrle_pncp_compra',
            'id_unico': 'id_unico'
        })

        # Define o nome da tabela que vai nascer no banco. (Ex: estados_sp_execucaofinanceiracontrato)
        target_table_name = f'estados_{estado.lower()}_execucaofinanceiracontrato'

        try:
            print(f"\nSalvando {len(df)} registros na tabela '{target_table_name}'...")
            # Envia a tabela inteira do Pandas pro banco de dados.
            # if_exists='replace' -> Deleta a tabela velha (se existir) e cria a nova por cima
            df.to_sql(name=target_table_name, con=engine, if_exists='replace', index=False)
            print(f"Dados financeiros de {estado} salvos com sucesso na tabela '{target_table_name}'.")
        except Exception as e:
            print(f"ERRO ao salvar dados na tabela '{target_table_name}': {e}")
    
    print("\nProcessamento de todos os estados concluído.")

# Ponto de partida do Python
if __name__ == "__main__":
    process_and_load_data()