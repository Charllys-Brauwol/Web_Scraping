# ==============================================================================
# --- IMPORTAÇÕES ---
# Módulos para conectar ao banco, ler planilhas do Excel e navegar nas pastas.
# ==============================================================================
import psycopg2  # Para se comunicar com o banco de dados PostgreSQL
from psycopg2 import OperationalError  # Para lidar com erros de conexão
import pandas as pd  # Para abrir o Excel, higienizar e empilhar os dados
from sqlalchemy import create_engine  # O motor que exporta o Pandas para o banco
import os  # Para manipular caminhos de pastas no Windows
import glob  # Para buscar arquivos usando um padrão (ex: '*.xlsx')

# ==============================================================================
# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# ==============================================================================
DB_HOST = "localhost" # O banco roda no seu próprio computador
DB_USER = "postgres" # Usuário padrão
DB_PASSWORD = "cb2907cb"  # Sua senha
DB_PORT = "5432" # Porta padrão do Postgres
TARGET_DB_NAME = "minhas_obras" # O banco que receberá as tabelas consolidadas

# ==============================================================================
# --- CAMINHO RAIZ ---
# A pasta principal onde todas as subpastas dos ministérios estão salvas
# ==============================================================================
PASTA_RAIZ_DADOS = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\Site_Legado" 

# ==============================================================================
# --- MAPEAMENTO DE TABELAS E PASTAS (DICIONÁRIO MESTRE) ---
# A chave (lado esquerdo) é como a tabela vai se chamar lá no Banco de Dados.
# O valor (lado direito, entre colchetes) é a lista de pastas que compõem essa tabela.
# ==============================================================================
MAPA_MINISTERIOS = {
    # --- Casos Simples: 1 Pasta -> 1 Tabela ---
    # Exemplo: A tabela vai se chamar 'ministerio_da_defesa' e os dados vêm da pasta homônima
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

    # --- Casos Agrupados: Várias Pastas -> 1 Única Tabela ---
    # Exemplo: O Pandas vai abrir as 4 pastas das Cidades, ler os 4 Excels, colar um
    # embaixo do outro e só depois mandar para o banco na tabela 'MINISTERIO_DAS_CIDADES'
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

# ==============================================================================
# --- FUNÇÃO: VERIFICAR E CRIAR O BANCO DE DADOS ---
# ==============================================================================
def create_target_database():
    """Garante que o banco 'minhas_obras' exista antes de tentar jogar tabelas lá."""
    try:
        # Tenta conectar no banco padrão de fábrica para verificar o resto do sistema
        conn = psycopg2.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, database="postgres"
        )
        conn.autocommit = True # Necessário para rodar o comando CREATE DATABASE
        cursor = conn.cursor()
        
        # Pergunta ao sistema se o banco alvo já está cadastrado
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB_NAME}'")
        
        if not cursor.fetchone(): # Se a resposta for vazia (o banco não existe)
            print(f"Criando banco de dados: {TARGET_DB_NAME}")
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME}") # Cria do zero
        else:
            print(f"Banco de dados '{TARGET_DB_NAME}' já existe.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar DB: {e}")
        exit() # Aborta o script se não conseguir criar nem conectar

# ==============================================================================
# --- FUNÇÃO: PADRONIZAR NOMES DE COLUNAS ---
# ==============================================================================
def limpar_nomes_colunas(df):
    """
    Higieniza o nome das colunas transformando em snake_case (letras minúsculas com underline).
    Essencial para evitar que as 4 partes do Excel fiquem desalinhadas na hora de empilhar.
    """
    df.columns = [
        str(col).lower() # Tudo minúsculo
        .replace(' ', '_') # Espaço vira _
        .replace('.', '') # Tira ponto
        .replace('-', '_') # Traço vira _
        .replace('(', '').replace(')', '') # Tira parênteses
        .replace('[', '').replace(']', '') # Tira colchetes
        .strip() # Remove espaços sobrando no final
        for col in df.columns # Faz isso em todas as colunas
    ]
    
    # Se houver alguma coluna que o nome ficou totalmente em branco após a limpeza, 
    # renomeia ela com um nome genérico (ex: 'col_5') para o banco não dar erro.
    df = df.rename(columns={c: f'col_{i}' for i, c in enumerate(df.columns) if not c.strip()})
    return df

# ==============================================================================
# --- FUNÇÃO PRINCIPAL: ORQUESTRAÇÃO DE CARGA ---
# ==============================================================================
def process_and_load_ministry_data():
    """Lê as pastas, empilha as planilhas parciais e envia para o PostgreSQL."""
    
    print(f"\nConectando ao banco: {TARGET_DB_NAME}")
    try:
        # Inicia o motor do SQLAlchemy apontando pro banco de dados oficial
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return  # Sai da função se falhar

    print("\nIniciando processamento...")

    # .items() divide o dicionário em duas partes pra gente usar:
    # nome_tabela = A Chave (Ex: 'MINISTERIO_DAS_CIDADES')
    # lista_pastas = O Valor (Ex: ['pasta_1', 'pasta_2', 'pasta_3'...])
    for nome_tabela, lista_pastas in MAPA_MINISTERIOS.items():
        print(f"\n>>> Preparando tabela: {nome_tabela}")
        
        # Caixinha que vai acumular as planilhas abertas na memória antes de juntar tudo
        dfs_para_combinar = [] 

        # Começa a varrer as pastas que compõem essa tabela
        for pasta in lista_pastas:
            # Junta o diretório raiz com o nome da pasta
            caminho_pasta = os.path.join(PASTA_RAIZ_DADOS, pasta)

            if not os.path.isdir(caminho_pasta): # Se a pasta não existir no seu HD
                print(f"   AVISO: Pasta '{pasta}' não encontrada. Pulando...")
                continue # Vai pra próxima pasta

            # Procura qualquer arquivo que termine com .xlsx dentro da pasta
            arquivos = glob.glob(os.path.join(caminho_pasta, '*.xlsx'))
            
            if not arquivos: # Se a pasta estiver vazia
                print(f"   AVISO: Nenhum arquivo .xlsx em '{pasta}'.")
                continue

            # --- INTELIGÊNCIA DE VERSÃO ---
            # Se houver vários arquivos Excel (porque você baixou várias vezes),
            # ele pega o que tem a data de modificação mais recente (max getmtime).
            arquivo_recente = max(arquivos, key=os.path.getmtime)
            print(f"   Lendo: {os.path.basename(arquivo_recente)} (da pasta {pasta})")

            try:
                # --- LEITURA E PREPARAÇÃO ---
                df_temp = pd.read_excel(arquivo_recente) # O Pandas abre a planilha
                
                if df_temp.empty: # Se a planilha tiver apenas o cabeçalho
                    print(f"   AVISO: Arquivo vazio. Ignorando.")
                    continue

                # Chama a função de higienização das colunas
                # Fazer isso ANTES de empilhar garante que uma coluna 'Valor' e outra ' Valor ' se alinhem perfeitamente
                df_temp = limpar_nomes_colunas(df_temp)
                
                # --- RASTREABILIDADE ---
                # Cria uma coluna extra na tabela dizendo de qual pasta (parte 1, 2, 3...) aquela linha veio.
                df_temp['pasta_origem'] = pasta
                
                # Guarda a planilha limpa dentro da nossa caixinha de consolidação
                dfs_para_combinar.append(df_temp)

            except Exception as e:
                print(f"   ERRO ao ler arquivo {arquivo_recente}: {e}")

        # --- CONSOLIDAÇÃO E CARGA (MERGE E LOAD) ---
        # Se a caixinha tiver pelo menos uma planilha dentro...
        if dfs_para_combinar:
            try:
                # A mágica do Pandas: pd.concat pega todas as planilhas da caixinha e 
                # "costura" uma embaixo da outra criando um Super DataFrame (df_final).
                # ignore_index=True refaz a numeração das linhas (1, 2, 3...) de forma contínua.
                df_final = pd.concat(dfs_para_combinar, ignore_index=True)
                
                print(f"   Salvando {len(df_final)} registros na tabela '{nome_tabela}'...")
                
                # Manda a super tabela pro banco de dados de uma vez só. 
                # if_exists='replace' deleta a tabela velha do mês passado e sobe a nova.
                df_final.to_sql(name=nome_tabela.lower(), con=engine, if_exists='replace', index=False)
                
                print(f"   SUCESSO: Tabela '{nome_tabela}' atualizada.")
            except Exception as e:
                print(f"   ERRO ao salvar no banco para '{nome_tabela}': {e}")
        else: # Se a caixinha ficou vazia (pastas vazias ou com erro)
            print(f"   ALERTA: Nenhum dado válido encontrado para gerar a tabela '{nome_tabela}'.")

    print("\nProcessamento concluído.")

# Chama as duas funções na ordem correta
if __name__ == "__main__":
    create_target_database()
    process_and_load_ministry_data()