import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
import os
import glob
import sys

# --- Configurações do Banco de Dados ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb"
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras"

# --- Mapeamento: Pasta no Disco -> Prefixo da Tabela no Banco ---
# O script vai procurar as pastas dos estados (AC, SP, etc) DENTRO destes caminhos.
MAPA_APIS = {
    r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiExeFisica": "api_execucao_fisica",
    r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiProjetoInvestimento": "api_projeto_investimento",
    r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiExecucaoFinanceiraContrato": "api_execucao_financeira_contrato",
    r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiExecucaoFinanceira": "api_execucao_financeira",
    r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiSaldoContabil": "api_saldo_contabil"
}

def create_target_database():
    """Cria o banco de dados se ele não existir."""
    try:
        # Conecta no banco default 'postgres' para poder criar o novo banco
        conn = psycopg2.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, database="postgres"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB_NAME}'")
        if not cursor.fetchone():
            print(f"--- Criando banco de dados: {TARGET_DB_NAME} ---")
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME}")
        else:
            print(f"--- Banco de dados '{TARGET_DB_NAME}' já existe. Conectando... ---")
            
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"ERRO CRÍTICO ao criar/conectar no banco: {e}")
        return False

def get_engine():
    """Retorna a engine do SQLAlchemy para o banco alvo."""
    return create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')

def limpar_nomes_colunas(df):
    """Padroniza nomes das colunas para snake_case (evita erros no PostgreSQL)."""
    df.columns = [
        str(col).lower()
        .replace(' ', '_')
        .replace('.', '')
        .replace('-', '_')
        .replace('/', '_')
        .replace('(', '').replace(')', '')
        .strip()
        for col in df.columns
    ]
    return df

def ler_arquivo_csv(caminho_arquivo):
    """Tenta ler o CSV detectando o separador automaticamente (; ou ,)."""
    try:
        # Tenta ler a primeira linha para descobrir o separador
        with open(caminho_arquivo, 'r', encoding='utf-8-sig') as f:
            primeira_linha = f.readline()
            separador = ';' if ';' in primeira_linha else ','
            
        return pd.read_csv(caminho_arquivo, sep=separador, encoding='utf-8-sig', low_memory=False)
    except Exception as e:
        print(f"      Erro ao ler CSV: {e}")
        return None

def processar_apis():
    if not create_target_database():
        return

    engine = get_engine()
    
    print("\n=== INICIANDO IMPORTAÇÃO DAS APIs ===")

    for caminho_api, prefixo_tabela in MAPA_APIS.items():
        print(f"\n>>> Processando API: {prefixo_tabela.upper()}")
        print(f"    Pasta raiz: {caminho_api}")

        if not os.path.exists(caminho_api):
            print(f"    [AVISO] Pasta não encontrada: {caminho_api}. Pulando.")
            continue

        # Lista todas as subpastas (que devem ser os ESTADOS: AC, AL, AP...)
        subpastas = [f.path for f in os.scandir(caminho_api) if f.is_dir()]
        
        if not subpastas:
            print("    [AVISO] Nenhuma subpasta de estado encontrada.")
            continue

        for pasta_estado in subpastas:
            # O nome da pasta é a UF (ex: .../apiExeFisica/CE -> UF = CE)
            uf = os.path.basename(pasta_estado).upper()
            
            # Define o nome da tabela: api_nome_UF (ex: api_execucao_financeira_ce)
            nome_tabela = f"{prefixo_tabela}_{uf}".lower()

            # Busca arquivos CSV na pasta do estado
            arquivos_csv = glob.glob(os.path.join(pasta_estado, "*.csv"))
            
            if not arquivos_csv:
                # print(f"    - Estado {uf}: Nenhum CSV encontrado.")
                continue

            # Pega o arquivo mais recente pela data de modificação
            arquivo_recente = max(arquivos_csv, key=os.path.getmtime)
            nome_arquivo = os.path.basename(arquivo_recente)
            
            print(f"    - Estado {uf}: Importando '{nome_arquivo}' -> Tabela '{nome_tabela}'")

            # Lê o DataFrame
            df = ler_arquivo_csv(arquivo_recente)
            
            if df is not None and not df.empty:
                # Tratamento básico
                df = limpar_nomes_colunas(df)
                
                # Adiciona coluna de controle (opcional)
                df['arquivo_origem'] = nome_arquivo
                df['uf_referencia'] = uf

                try:
                    # Salva no Banco (if_exists='replace' recria a tabela com o arquivo mais novo)
                    df.to_sql(name=nome_tabela, con=engine, if_exists='replace', index=False)
                    print(f"      [SUCESSO] {len(df)} registros salvos em '{nome_tabela}'.")
                except Exception as e:
                    print(f"      [ERRO] Falha ao salvar no banco: {e}")
            else:
                print(f"      [AVISO] Arquivo vazio ou inválido.")

    print("\n=== PROCESSO CONCLUÍDO ===")

if __name__ == "__main__":
    processar_apis()