import psycopg2
from sqlalchemy import create_engine
from psycopg2 import OperationalError
import sys

# --- Configurações do Banco de Dados ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb" 
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras"

# --- Gerar lista completa de tabelas para limpeza ---
ESTADOS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

TABELA_TIPOS = [
    "saldo_contabil",
    "execucao_fisica"
]

TABLES_TO_CLEAN = [
    f"estados_{estado.lower()}_{tipo}"
    for estado in ESTADOS
    for tipo in TABELA_TIPOS
]

def get_db_connection():
    """Cria e retorna uma conexão bruta com o psycopg2 para comandos DML/DDL."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            database=TARGET_DB_NAME
        )
        return conn
    except OperationalError as e:
        print(f"Erro de conexão com o banco de dados '{TARGET_DB_NAME}': {e}")
        sys.exit(1)

def get_comparison_columns(table_name):
    """
    Retorna a lista de colunas a serem comparadas para cada tipo de tabela.
    Esta lista define o que é considerado uma 'mudança' no registro.
    """
    if 'saldo_contabil' in table_name:
        # Colunas de saldo contábil:
        return [
            "nr_nota_empenho", "ug_emitente", # Incluímos UG e Nota para que a mudança em UGs ou Notas seja registrada!
            "vl_transferido_exercicio_anterior", "vl_transferido", 
            "vl_restos_a_pagar", "vl_reinscrito_rp", "vl_reforcado", "vl_recebido_transferido", 
            "vl_recebido_exercicio_anterior", "vl_pago", "vl_liquidado_a_pagar", 
            "vl_inscrito_rp", "vl_incluido", "unidade_orcamentaria", "vl_em_liquidacao", 
            "vl_cancelado_exercicio_anterior", "vl_anulado_cancelado", "vl_a_liquidar"
        ]
    elif 'execucao_fisica' in table_name:
        # Colunas de execução física:
        return [
            "percentual", "data_situacao", "situacao", "observacoes", 
            "em_operacao", "justificativa_em_operacao", "cancelamentos_paralisacoes"
        ]
    return []


def clean_redundant_history(conn, table_name):
    """
    Executa a query SQL para deletar os registros redundantes de uma tabela específica,
    particionando exclusivamente pelo id_unico.
    """
    cursor = conn.cursor()
    columns = get_comparison_columns(table_name)
    
    if not columns:
        print(f"AVISO: Nenhuma coluna de comparação definida para a tabela '{table_name}'. Pulando.")
        return 0

    # A PARTITION KEY é FIXA: APENAS o id_unico
    partition_key = "id_unico" 

    # 1. Constrói a lista de comparações (Ex: 'c.col1 = c.prev_col1 AND c.col2 = c.prev_col2')
    comparison_conditions = " AND ".join(
        f"c.\"{col}\" = c.prev_{col}" for col in columns
    )

    # 2. Constrói a lista de colunas anteriores para a função LAG
    # PARTITION BY id_unico é a única chave de agrupamento
    lag_columns = ", ".join(
        f"LAG(\"{col}\", 1) OVER (PARTITION BY {partition_key} ORDER BY data_execucao) AS prev_{col}"
        for col in columns
    )
    
    # Query Final (Deleta todas as linhas onde o estado é igual ao anterior)
    delete_query = f"""
        DELETE FROM "{table_name}"
        WHERE ctid IN (
            WITH ComparisonData AS (
                SELECT 
                    ctid,
                    data_execucao,
                    -- Chave de Partição
                    {partition_key},
                    -- Campos atuais
                    {", ".join(f"\"{col}\"" for col in columns)},
                    -- Campos anteriores (prev_) usando LAG()
                    {lag_columns}
                FROM 
                    "{table_name}"
            )
            SELECT 
                ctid
            FROM 
                ComparisonData c
            WHERE 
                -- O primeiro campo de comparação não pode ser NULL (ignora o primeiro registro de cada grupo)
                c.prev_{columns[0]} IS NOT NULL 
                AND {comparison_conditions}
        );
    """
    
    try:
        cursor.execute(delete_query)
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"   SUCESSO: {deleted_count} registros redundantes deletados de '{table_name}'.")
        return deleted_count
    except Exception as e:
        conn.rollback()
        print(f"   ERRO CRÍTICO ao limpar a tabela '{table_name}': {e}")
        return 0
    finally:
        cursor.close()

if __name__ == "__main__":
    total_deleted = 0
    
    # 1. Obtém a conexão com o banco de dados
    connection = get_db_connection()
    
    print(f"\n--- INICIANDO LIMPEZA HISTÓRICA DE {len(TABLES_TO_CLEAN)} TABELAS (PARTIÇÃO: ID_UNICO) ---")
    
    # 2. Itera sobre a lista de tabelas e executa a limpeza
    for table in TABLES_TO_CLEAN:
        print(f"Processando tabela: {table}")
        deleted = clean_redundant_history(connection, table)
        total_deleted += deleted

    # 3. Fecha a conexão
    connection.close()
    
    print(f"\n--- LIMPEZA CONCLUÍDA ---")
    print(f"Total de registros redundantes removidos: {total_deleted}")
    print("O histórico agora contém apenas as mudanças reais por ID do Projeto.")