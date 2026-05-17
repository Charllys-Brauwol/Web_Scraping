# ==============================================================================
# --- IMPORTAÇÕES ---
# Ferramentas para conectar ao banco, manipular arquivos e ler dados.
# ==============================================================================
import psycopg2  # Biblioteca para conectar o Python ao PostgreSQL
from psycopg2 import OperationalError  # Para capturar erros de conexão no banco
import pandas as pd  # A poderosa biblioteca para ler e manipular planilhas
from sqlalchemy import create_engine  # O motor que empurra os dados do Pandas para o Postgres
import os  # Para navegar e manipular pastas no Windows
import glob  # Para buscar arquivos usando padrões (como '*.csv')

# ==============================================================================
# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# ==============================================================================
DB_HOST = "localhost" # O banco de dados roda na sua própria máquina
DB_USER = "postgres" # Usuário administrador
DB_PASSWORD = "cb2907cb"  # Senha de acesso
DB_PORT = "5432" # Porta padrão de comunicação do Postgres
TARGET_DB_NAME = "minhas_obras"  # O banco de dados que vai receber as tabelas

# ==============================================================================
# --- MAPEAMENTO DE PASTAS E ESTADOS ---
# ==============================================================================
# Caminho raiz onde ficam as pastas dos seus projetos
CAMINHO_BASE_ARQUIVOS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD"

# As duas pastas principais que o robô vai investigar
PASTAS_ALVO = ["ModExtUF", "ModExtUFID"]

# A lista de todas as subpastas (Estados) que ele deve procurar dentro das pastas alvo
ESTADOS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", 
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

# ==============================================================================
# --- FUNÇÃO: VERIFICAR/CRIAR O BANCO DE DADOS ---
# ==============================================================================
def create_target_database():
    """Garante que o banco de dados 'minhas_obras' exista antes de tentar usá-lo."""
    try:
        # Conecta no banco de fábrica ('postgres') para poder olhar o sistema de fora
        conn = psycopg2.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, database="postgres"
        )
        conn.autocommit = True # Exigência para rodar comandos estruturais (como criar banco)
        cursor = conn.cursor()
        
        # Pergunta ao sistema se o banco alvo já está na lista
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB_NAME}'")
        
        if not cursor.fetchone(): # Se não existir...
            print(f"Criando banco de dados: {TARGET_DB_NAME}")
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME}") # Cria ele do zero
        else:
            print(f"Banco de dados '{TARGET_DB_NAME}' já existe.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar DB: {e}")
        exit() # Mata o script se não conseguir criar/conectar, pois nada mais vai funcionar

# ==============================================================================
# --- FUNÇÃO: HIGIENIZAR COLUNAS ---
# ==============================================================================
def limpar_nomes_colunas(df):
    """Padroniza os nomes das colunas para evitar que o PostgreSQL rejeite a tabela."""
    df.columns = [
        str(col).lower() # Força letras minúsculas
        .replace(' ', '_') # Troca espaços por underline (snake_case)
        .replace('.', '') # Remove pontos
        .replace('-', '_') # Troca traços por underline
        .replace('/', '_') # Troca barras por underline
        .replace('(', '').replace(')', '') # Arranca fora parênteses
        .strip() # Remove espaços vazios perdidos nas pontas
        for col in df.columns # Roda isso para cada coluna existente na planilha
    ]
    return df

# ==============================================================================
# --- FUNÇÃO: LEITOR INTELIGENTE (À PROVA DE FALHAS) ---
# ==============================================================================
def ler_arquivo_robusto(filepath):
    """Descobre a extensão do arquivo e tenta ler da melhor forma possível."""
    if filepath.endswith('.xlsx'): # Se for Excel moderno
        return pd.read_excel(filepath)
        
    elif filepath.endswith('.csv'): # Se for arquivo de texto (CSV)
        try:
            # 1ª Tentativa: Ponto e vírgula (padrão brasileiro/europeu e do Excel PT-BR)
            return pd.read_csv(filepath, sep=';', low_memory=False)
        except:
            # 2ª Tentativa: Vírgula (padrão original americano)
            return pd.read_csv(filepath, sep=',', low_memory=False)
            
    return pd.DataFrame() # Se for um PDF ou txt, devolve uma tabela vazia para o script não quebrar

# ==============================================================================
# --- FUNÇÃO PRINCIPAL: ORQUESTRAÇÃO DE LEITURA E CARGA ---
# ==============================================================================
def processar_pastas_estados():
    
    print(f"\nConectando ao banco: {TARGET_DB_NAME}")
    try:
        # Liga o motor do SQLAlchemy na rota do seu banco de dados
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return # Sai da função se o banco estiver desligado

    print("\nIniciando processamento dos Estados...")

    # --- LOOP 1: NÍVEL DA PASTA RAIZ (ModExtUF, ModExtUFID) ---
    for pasta_raiz in PASTAS_ALVO:
        print(f"\n==========================================")
        print(f">>> PROCESSANDO DIRETÓRIO: {pasta_raiz}")
        print(f"==========================================")

        # --- LOOP 2: NÍVEL DO ESTADO (AC, AL, AP...) ---
        for estado in ESTADOS:
            
            # Monta o caminho exato onde o Windows deve procurar a pasta.
            # Exemplo: C:\Users\...\Arquivos_BD\ModExtUF\SP
            caminho_estado = os.path.join(CAMINHO_BASE_ARQUIVOS, pasta_raiz, estado)
            
            # A genialidade do script: o nome da tabela nasce automaticamente da combinação da pasta com o estado!
            # Exemplo: A tabela vai se chamar ModExtUF_SP
            nome_tabela = f"{pasta_raiz}_{estado}"

            # Confere se a pasta desse estado realmente existe no seu HD
            if not os.path.isdir(caminho_estado):
                print(f"   [PULANDO] Pasta não encontrada: {caminho_estado}")
                continue # Se não existir, pula pro próximo estado

            # Procura por qualquer CSV ou XLSX lá dentro, e junta as duas buscas numa única lista
            arquivos = glob.glob(os.path.join(caminho_estado, '*.csv')) + \
                       glob.glob(os.path.join(caminho_estado, '*.xlsx'))
            
            if not arquivos: # Se a pasta existir, mas estiver vazia
                print(f"   [VAZIO] Nenhum arquivo em {pasta_raiz}/{estado}")
                continue

            # --- INTELIGÊNCIA DE ATUALIZAÇÃO ---
            # Se você tiver feito o download de 5 planilhas do Ceará ao longo do mês, 
            # ele olha a data do Windows e pega apenas a mais nova (max getmtime).
            arquivo_recente = max(arquivos, key=os.path.getmtime)
            print(f"   Lendo: {os.path.basename(arquivo_recente)} -> Tabela: {nome_tabela}")

            try:
                # Manda o arquivo pro nosso leitor à prova de falhas
                df = ler_arquivo_robusto(arquivo_recente)
                
                if df.empty: # Se a planilha só tiver o título e nenhuma linha de dado
                    print(f"   [AVISO] Arquivo vazio. Ignorando.")
                    continue

                # Passa a vassoura nos nomes das colunas
                df = limpar_nomes_colunas(df)
                
                # --- RASTREABILIDADE ---
                # Cria uma coluna indicando o nome do arquivo original (ótimo para auditar os dados depois)
                df['arquivo_origem'] = os.path.basename(arquivo_recente)

                # --- SALVAMENTO NO BANCO (LOAD) ---
                # Empurra a tabela pro PostgreSQL. 
                # O if_exists='replace' garante que se você rodar o script no mês que vem, ele apaga a tabela velha do estado e sobe a nova.
                df.to_sql(name=nome_tabela, con=engine, if_exists='replace', index=False)
                
                print(f"   SUCESSO: Tabela '{nome_tabela}' criada com {len(df)} registros.")

            except Exception as e:
                # Se acontecer algum bug bizarro (ex: arquivo corrompido), avisa e segue pro próximo estado sem travar o script inteiro.
                print(f"   ERRO CRÍTICO ao processar {estado}: {e}")

    print("\nProcessamento concluído. 🎉")

# Ordem de execução do script
if __name__ == "__main__":
    create_target_database() # Primeiro certifica o banco
    processar_pastas_estados() # Depois processa os arquivos