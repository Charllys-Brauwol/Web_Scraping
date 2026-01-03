import psycopg2
import requests
import pandas as pd
from sqlalchemy import create_engine
from psycopg2 import OperationalError
import time
import sys
import random # Importa para atraso randômico

# --- Configurações do Banco de Dados ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb" 
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras"

# --- URL da API de Execução Financeira (detalhada) ---
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira"
API_HEADERS = {"accept": "*/*"}

# Lista de estados a serem processados
estados = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

def conexaobd():
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

def obter_id_uf(engine, estado):
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

def buscar_dados_financeiros(id_projeto):
    """
    Faz a requisição à nova API para um ID de projeto e gerencia a paginação, tratando o erro 429.
    """
    todos_dados = []
    pag = 0
    limpar_pid = str(id_projeto).strip() # Garante a limpeza do ID
    
    while True:
        params = {
            "idProjetoInvestimento": limpar_pid,
            "pagina": pag,
            "tamanhoDaPagina": 100
        }
        try:
            response = requests.get(API_URL, params=params, headers=API_HEADERS, timeout=30)
            
            # --- Tratamento de Erro 429 (Rate Limit) ---
            if response.status_code == 429:
                print(f"!!! ERRO 429 - LIMITE ATINGIDO para {limpar_pid}. Esperando 60 segundos...")
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
                item['id_unico'] = limpar_pid
            
            todos_dados.extend(content)
            
            if data.get("last", False):
                break
            
            pag += 1
            time.sleep(random.uniform(1, 2)) # Atraso menor entre as páginas

        except requests.exceptions.RequestException as e:
            print(f"AVISO: Erro na requisição para o ID {limpar_pid} (página {pag}): {e}")
            break
    
    return todos_dados

def processar_carregar_dados():
    """
    Função principal para orquestrar o processo.
    """
    engine = conexaobd()
    if not engine:
        sys.exit(1)

    # Nomes das colunas para os registros placeholder
    nomes_colunas = [
        'id_unico', 'nomeEsferaOrcamentaria', 'nomeTipoEmpenho', 'fonteRecurso', 'naturezaDespesa',
        'numeroProcesso', 'descricaoEmpenho', 'planoInterno', 'resultadoPrimario',
        'tipoCredito', 'ugEmitente', 'codigoAmparoLegal', 'informacoesComplementares',
        'nomeFavorecido', 'unidadeOrcamentaria', 'ugResponsavel', 'planoOrcamentario',
        'autorEmenda', 'numeroNotaEmpenhoGerada', 'localEntrega', 'valorEmpenho',
        'nrPtres', 'idProjetoInvestimento'
    ]

    for estado in estados:
        print(f"\n--- Iniciando processamento para o estado: {estado} ---")
        
        ids_projetos = obter_id_uf(engine, estado)
        if not ids_projetos:
            print(f"Nenhum ID de projeto encontrado para o estado {estado}. Pulando para o próximo.")
            continue
        
        estado_dados = []
        for pid in ids_projetos:
            
            # Limpa o ID antes de passar para a função de fetch e para o placeholder
            limpar_pid = str(pid).strip()
            
            dados_da_api = buscar_dados_financeiros(limpar_pid)
            
            if dados_da_api:
                print(f"Dados encontrados para o projeto ID: {limpar_pid}. Total de registros: {len(dados_da_api)}")
                estado_dados.extend(dados_da_api)
            else:
                print(f"Nenhum dado encontrado para o projeto ID: {limpar_pid}. Criando registro placeholder...")
                # Cria um registro com '-' em todas as colunas
                registro_vazio = {col: '-' for col in nomes_colunas}
                # Garante que o ID do projeto esteja correto
                registro_vazio['id_unico'] = limpar_pid
                registro_vazio['idProjetoInvestimento'] = limpar_pid
                estado_dados.append(registro_vazio)
            
            # --- NOVO AJUSTE: Atraso maior entre cada ID de projeto ---
            # Tempo de espera de 2 a 3 segundos para evitar o erro 429
            time.sleep(random.uniform(2, 3)) 
            # --------------------------------------------------------

        if not estado_dados:
            print(f"Nenhum dado, nem registro placeholder, encontrado para o estado {estado}. Nenhuma tabela será criada.")
            continue

        # Criação do DataFrame com os dados coletados
        df = pd.DataFrame(estado_dados)

        # Ajusta os nomes das colunas para o formato snake_case
        df = df.rename(columns={
            'id_unico': 'id_unico',
            'nomeEsferaOrcamentaria': 'nome_esfera_orcamentaria',
            'nomeTipoEmpenho': 'nome_tipo_empenho',
            'fonteRecurso': 'fonte_recurso',
            'naturezaDespesa': 'natureza_despesa',
            'numeroProcesso': 'numero_processo',
            'descricaoEmpenho': 'descricao_empenho',
            'planoInterno': 'plano_interno',
            'resultadoPrimario': 'resultado_primario',
            'tipoCredito': 'tipo_credito',
            'ugEmitente': 'ug_emitente',
            'codigoAmparoLegal': 'codigo_amparo_legal',
            'informacoesComplementares': 'informacoes_complementares',
            'nomeFavorecido': 'nome_favorecido',
            'unidadeOrcamentaria': 'unidade_orcamentaria',
            'ugResponsavel': 'ug_responsavel',
            'planoOrcamentario': 'plano_orcamentario',
            'autorEmenda': 'autor_emenda',
            'numeroNotaEmpenhoGerada': 'numero_nota_empenho_gerada',
            'localEntrega': 'local_entrega',
            'valorEmpenho': 'valor_empenho',
            'nrPtres': 'nr_ptres',
            'idProjetoInvestimento': 'id_projeto_investimento'
        })

        # Define o nome da tabela de destino com o padrão 'estados_sigla_...'
        nome_tabela = f'estados_{estado.lower()}_execucaofinanceira_detalhes'

        try:
            print(f"\nSalvando {len(df)} registros na tabela '{nome_tabela}'...")
            df.to_sql(name=nome_tabela, con=engine, if_exists='replace', index=False)
            print(f"Dados financeiros de {estado} salvos com sucesso na tabela '{nome_tabela}'.")
        except Exception as e:
            print(f"ERRO ao salvar dados na tabela '{nome_tabela}': {e}")
    
    print("\nProcessamento de todos os estados concluído.")

if __name__ == "__main__":
    processar_carregar_dados()