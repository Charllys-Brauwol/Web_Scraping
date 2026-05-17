# ==============================================================================
# --- IMPORTAÇÕES ---
# Ferramentas para conectar ao banco, ler pastas e manipular tabelas.
# ==============================================================================
import psycopg2  # Conector nativo do Python para o PostgreSQL
import pandas as pd  # A super biblioteca para ler e manipular as planilhas CSV
from sqlalchemy import create_engine, text  # O motor que empurra os dados do Pandas pro Banco
import os  # Para ler e navegar pelas pastas do Windows
import glob  # Para buscar arquivos específicos (ex: "*.csv") dentro das pastas
import sys  # Para comandos do sistema (como abortar o script)

# ==============================================================================
# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# ==============================================================================
DB_HOST = "localhost" # O banco está rodando na sua máquina
DB_USER = "postgres" # Usuário mestre
DB_PASSWORD = "cb2907cb" # Senha
DB_PORT = "5432" # Porta padrão
TARGET_DB_NAME = "minhas_obras" # O banco de dados que vai receber as tabelas

# ==============================================================================
# --- MAPEAMENTO: PASTA NO DISCO -> PREFIXO DA TABELA ---
# Dicionário genial: O Python olha para a chave (caminho da pasta) e já sabe 
# qual vai ser o prefixo do nome da tabela (valor) lá no banco de dados.
# ==============================================================================
MAPA_APIS = {
    r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiExeFisica": "api_execucao_fisica",
    r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiProjetoInvestimento": "api_projeto_investimento",
    r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiExecucaoFinanceiraContrato": "api_execucao_financeira_contrato",
    r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiExecucaoFinanceira": "api_execucao_financeira",
    r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiSaldoContabil": "api_saldo_contabil"
}

# ==============================================================================
# --- FUNÇÃO: CRIAR O BANCO DE DADOS (SE NÃO EXISTIR) ---
# Garante que o script rode liso mesmo se você instalar ele num computador "zerado"
# ==============================================================================
def create_target_database():
    """Conecta no banco 'postgres' original para verificar e criar o banco 'minhas_obras'."""
    try:
        # Conecta no banco default de fábrica ('postgres') porque não dá pra conectar 
        # num banco ('minhas_obras') que talvez ainda não exista!
        conn = psycopg2.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, database="postgres"
        )
        conn.autocommit = True # Exigência do Postgres para rodar comandos como CREATE DATABASE
        cursor = conn.cursor() # Abre o canal para enviar comandos SQL
        
        # Pergunta ao Postgres se o banco 'minhas_obras' já está registrado no sistema
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB_NAME}'")
        
        if not cursor.fetchone(): # Se a resposta for vazia (banco não existe)
            print(f"--- Criando banco de dados: {TARGET_DB_NAME} ---")
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME}") # Cria o banco de dados do zero
        else:
            print(f"--- Banco de dados '{TARGET_DB_NAME}' já existe. Conectando... ---")
            
        cursor.close() # Fecha o canal do cursor
        conn.close() # Fecha a conexão com o banco 'postgres' genérico
        return True
    except Exception as e:
        print(f"ERRO CRÍTICO ao criar/conectar no banco: {e}")
        return False

# ==============================================================================
# --- FUNÇÃO: MOTOR DE CONEXÃO ---
# ==============================================================================
def get_engine():
    """Retorna o motor do SQLAlchemy apontando para o seu banco alvo pronto."""
    return create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')

# ==============================================================================
# --- FUNÇÃO: HIGIENIZAR NOMES DE COLUNAS ---
# O PostgreSQL odeia colunas com espaços, letras maiúsculas e acentos.
# Essa função limpa a sujeira do CSV antes de mandar pro banco.
# ==============================================================================
def limpar_nomes_colunas(df):
    """Padroniza nomes das colunas para snake_case (evita erros no PostgreSQL)."""
    # Usa "List Comprehension" para varrer todas as colunas de uma vez
    df.columns = [
        str(col).lower() # Transforma tudo em minúsculo
        .replace(' ', '_') # Troca espaços por underline
        .replace('.', '') # Tira pontos
        .replace('-', '_') # Troca traços por underline
        .replace('/', '_') # Troca barras por underline
        .replace('(', '').replace(')', '') # Arranca fora os parênteses
        .strip() # Remove espaços vazios nas pontas
        for col in df.columns # Faz isso para cada coluna existente no DataFrame
    ]
    return df

# ==============================================================================
# --- FUNÇÃO: LER CSV COM INTELIGÊNCIA ---
# Diferentes sistemas exportam CSV com separadores diferentes. 
# Essa função descobre qual é o separador antes de ler o arquivo!
# ==============================================================================
def ler_arquivo_csv(caminho_arquivo):
    """Lê a primeira linha para adivinhar se o arquivo usa vírgula ou ponto-e-vírgula."""
    try:
        # Abre o arquivo em modo leitura só de texto
        with open(caminho_arquivo, 'r', encoding='utf-8-sig') as f:
            primeira_linha = f.readline() # Lê a primeiríssima linha do arquivo
            # Se tiver ponto e vírgula na primeira linha, o separador é ';'. Se não, é ','.
            separador = ';' if ';' in primeira_linha else ','
            
        # Agora sim, manda o Pandas ler a tabela inteira usando o separador correto!
        return pd.read_csv(caminho_arquivo, sep=separador, encoding='utf-8-sig', low_memory=False)
    except Exception as e:
        print(f"      Erro ao ler CSV: {e}")
        return None

# ==============================================================================
# --- CORAÇÃO DO SCRIPT: ORQUESTRAÇÃO DE IMPORTAÇÃO ---
# ==============================================================================
def processar_apis():
    # 1. Verifica/Cria o banco de dados
    if not create_target_database():
        return # Se falhar, encerra o programa

    engine = get_engine() # Liga o motor oficial do Pandas
    
    print("\n=== INICIANDO IMPORTAÇÃO DAS APIs ===")

    # 2. Percorre aquele Dicionário 'MAPA_APIS' lá do topo do código
    for caminho_api, prefixo_tabela in MAPA_APIS.items():
        print(f"\n>>> Processando API: {prefixo_tabela.upper()}")
        print(f"    Pasta raiz: {caminho_api}")

        # Se a pasta daquela API não existir no seu PC, ignora e vai pra próxima
        if not os.path.exists(caminho_api):
            print(f"    [AVISO] Pasta não encontrada: {caminho_api}. Pulando.")
            continue

        # 3. Manda o Windows listar apenas as pastas de Estados que estão lá dentro
        subpastas = [f.path for f in os.scandir(caminho_api) if f.is_dir()]
        
        if not subpastas:
            print("    [AVISO] Nenhuma subpasta de estado encontrada.")
            continue

        # 4. Loop varrendo pasta por pasta (Estado por Estado)
        for pasta_estado in subpastas:
            
            # Pega só o nome final da pasta (Ex: "CE") e transforma em maiúsculo
            uf = os.path.basename(pasta_estado).upper()
            
            # Monta o nome da tabela juntando o Prefixo com o Estado (Ex: api_execucao_fisica_ce)
            nome_tabela = f"{prefixo_tabela}_{uf}".lower()

            # Busca todos os arquivos .csv que estão dentro daquela pasta do estado
            arquivos_csv = glob.glob(os.path.join(pasta_estado, "*.csv"))
            
            if not arquivos_csv: # Se a pasta estiver vazia
                continue

            # 5. Inteligência de Versão: Descobre qual é o arquivo mais NOVO na pasta (getmtime)
            arquivo_recente = max(arquivos_csv, key=os.path.getmtime)
            nome_arquivo = os.path.basename(arquivo_recente) # Extrai o nome do arquivo pra usar no log
            
            print(f"    - Estado {uf}: Importando '{nome_arquivo}' -> Tabela '{nome_tabela}'")

            # 6. Lê o arquivo escolhido
            df = ler_arquivo_csv(arquivo_recente)
            
            if df is not None and not df.empty: # Se leu certinho e a tabela não estiver vazia
                
                # Lava os nomes das colunas
                df = limpar_nomes_colunas(df)
                
                # --- ENRIQUECIMENTO DE DADOS ---
                # Adiciona duas colunas no final da tabela para você saber a origem daquele dado lá no banco
                df['arquivo_origem'] = nome_arquivo
                df['uf_referencia'] = uf

                # 7. Carga no Banco (Load)
                try:
                    # Manda o dataframe (df) pro PostgreSQL. 
                    # if_exists='replace' significa que a cada semana/mês que você rodar isso,
                    # ele apaga a tabela velha do estado e sobe essa nova, mais atualizada.
                    df.to_sql(name=nome_tabela, con=engine, if_exists='replace', index=False)
                    print(f"      [SUCESSO] {len(df)} registros salvos em '{nome_tabela}'.")
                except Exception as e:
                    print(f"      [ERRO] Falha ao salvar no banco: {e}")
            else:
                print(f"      [AVISO] Arquivo vazio ou inválido.")

    print("\n=== PROCESSO CONCLUÍDO ===")

# Ponto de partida
if __name__ == "__main__":
    processar_apis()