import psycopg2
from psycopg2 import OperationalError
import pandas as pd
from sqlalchemy import create_engine
import os 
import glob 

# --- Configurações do Banco ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb" 
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras" 

# --- Novo Caminho da Pasta Raiz ---
PASTA_RAIZ_DADOS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\Site_Legado" 

# --- MAPEAMENTO DE TABELAS E PASTAS ---
# Formato: "NOME_DA_TABELA_NO_BANCO": ["Pasta_1", "Pasta_2", ...]
MAPA_MINISTERIOS = {
    # --- Casos Simples (1 Pasta -> 1 Tabela) ---
    "ministerio_da_defesa": ["ministerio_da_defesa"],
    "ministerio_da_pesca_e_aquicultura": ["ministerio_da_pesca_e_aquicultura"],
    "ministerio_da_ciencia_tecnologia_e_inovacao": ["ministerio_da_ciencia_tecnologia_e_inovacao"],
    "ministerio_da_gestao_e_da_inovacao_em_servicos_publicos": ["ministerio_da_gestao_e_da_inovacao_em_servicos_publicos"],
    "ministerio_da_cultura": ["ministerio_da_cultura"],
    "ministerio_da_justica_e_seguranca_publica": ["ministerio_da_justica_e_seguranca_publica"],
    "ministerio_do_turismo": ["ministerio_do_turismo"],
    "ministerio_da_economia": ["ministerio_da_economia"],
    "ministerio_das_comunicacoes": ["ministerio_das_comunicacoes"],
    "ministerio_das_mulheres": ["ministerio_das_mulheres"],
    "ministerio_de_minas_e_energia": ["ministerio_de_minas_e_energia"],
    "ministerio_de_portos_e_aeroportos": ["ministerio_de_portos_e_aeroportos"],
    "ministerio_da_infraestrutura": ["ministerio_da_infraestrutura"],
    "ministerio_do_esporte": ["ministerio_do_esporte"],
    "presidencia_da_republica": ["presidencia_da_republica"],
    "sec_esp_de_agric_fam_e_desenv_agrario": ["sec_esp_de_agric_fam_e_desenv_agrario"],
    "ministerio_do_desenvolvimento_e_assistencia_social_familiar_e_combate_a_fome": ["ministerio_do_desenvolvimento_e_assistencia_social_familiar_e_combate_a_fome"],
    "ministerio_do_desenvolvimento_agrario_e_da_agricultura_familiar": ["ministerio_do_desenvolvimento_agrario_e_da_agricultura_familiar"],
    "ministerio_do_desenvolvimento_industria_comercio_e_servicos": ["ministerio_do_desenvolvimento_industria_comercio_e_servicos"],
    "ministerio_do_meio_ambiente": ["ministerio_do_meio_ambiente"],
    "ministerio_do_trabalho_e_emprego": ["ministerio_do_trabalho_e_emprego"],
    "ministerio_do_desenvolvimento_regional": ["ministerio_do_desenvolvimento_regional"],

    # --- Casos Agrupados (Várias Pastas -> 1 Tabela) ---
    "MINISTERIO_DAS_CIDADES": [
        "MINISTERIO_DAS_CIDADES_1", 
        "MINISTERIO_DAS_CIDADES_1.1", 
        "MINISTERIO_DAS_CIDADES_2", 
        "MINISTERIO_DAS_CIDADES_3"
    ],
    "MINISTERIO_DA_EDUCACAO": [
        "MINISTERIO_DA_EDUCACAO_1", 
        "MINISTERIO_DA_EDUCACAO_2"
    ],
    "MINISTERIO_DA_SAUDE": [
        "MINISTERIO_DA_SAUDE_1", 
        "MINISTERIO_DA_SAUDE_2", 
        "MINISTERIO_DA_SAUDE_3", 
        "MINISTERIO_DA_SAUDE_4"
    ]
}

def create_target_database():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, database="postgres"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB_NAME}'")
        if not cursor.fetchone():
            print(f"Criando banco de dados: {TARGET_DB_NAME}")
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME}")
        else:
            print(f"Banco de dados '{TARGET_DB_NAME}' já existe.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar DB: {e}")
        exit()

def limpar_nomes_colunas(df):
    """Padroniza nomes das colunas para evitar erros no PostgreSQL"""
    df.columns = [
        str(col).lower()
        .replace(' ', '_')
        .replace('.', '')
        .replace('-', '_')
        .replace('(', '').replace(')', '')
        .replace('[', '').replace(']', '')
        .strip()
        for col in df.columns
    ]
    # Remove colunas vazias ou inválidas
    df = df.rename(columns={c: f'col_{i}' for i, c in enumerate(df.columns) if not c.strip()})
    return df

def process_and_load_ministry_data():
    print(f"\nConectando ao banco: {TARGET_DB_NAME}")
    try:
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return 

    print("\nIniciando processamento...")

    # Itera sobre o Dicionário (Nome da Tabela -> Lista de Pastas)
    for nome_tabela, lista_pastas in MAPA_MINISTERIOS.items():
        print(f"\n>>> Preparando tabela: {nome_tabela}")
        
        dfs_para_combinar = [] # Lista para guardar os dados de cada pasta antes de salvar

        for pasta in lista_pastas:
            caminho_pasta = os.path.join(PASTA_RAIZ_DADOS, pasta)

            if not os.path.isdir(caminho_pasta):
                print(f"   AVISO: Pasta '{pasta}' não encontrada. Pulando...")
                continue

            # Procura Excel
            arquivos = glob.glob(os.path.join(caminho_pasta, '*.xlsx'))
            
            if not arquivos:
                print(f"   AVISO: Nenhum arquivo .xlsx em '{pasta}'.")
                continue

            # Pega o MAIS RECENTE daquela pasta
            arquivo_recente = max(arquivos, key=os.path.getmtime)
            print(f"   Lendo: {os.path.basename(arquivo_recente)} (da pasta {pasta})")

            try:
                df_temp = pd.read_excel(arquivo_recente)
                
                if df_temp.empty:
                    print(f"   AVISO: Arquivo vazio. Ignorando.")
                    continue

                # Limpa as colunas AGORA para garantir que o 'concat' funcione se os headers forem levemente diferentes
                df_temp = limpar_nomes_colunas(df_temp)
                
                # Adiciona coluna de origem para rastreabilidade (opcional, ajuda a saber de qual pasta veio)
                df_temp['pasta_origem'] = pasta
                
                dfs_para_combinar.append(df_temp)

            except Exception as e:
                print(f"   ERRO ao ler arquivo {arquivo_recente}: {e}")

        # Se tiver dados acumulados (seja de 1 pasta ou de 4 pastas), salva no banco
        if dfs_para_combinar:
            try:
                # Junta todos os DataFrames em um só (empilha um embaixo do outro)
                df_final = pd.concat(dfs_para_combinar, ignore_index=True)
                
                print(f"   Salvando {len(df_final)} registros na tabela '{nome_tabela}'...")
                df_final.to_sql(name=nome_tabela, con=engine, if_exists='replace', index=False)
                print(f"   SUCESSO: Tabela '{nome_tabela}' atualizada.")
            except Exception as e:
                print(f"   ERRO ao salvar no banco para '{nome_tabela}': {e}")
        else:
            print(f"   ALERTA: Nenhum dado válido encontrado para gerar a tabela '{nome_tabela}'.")

    print("\nProcessamento concluído.")

if __name__ == "__main__":
    create_target_database()
    process_and_load_ministry_data()