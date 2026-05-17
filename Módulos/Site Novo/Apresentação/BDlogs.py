# ==============================================================================
# --- IMPORTAÇÕES ---
# Ferramentas para manipular textos complexos, pastas, tabelas e banco de dados.
# ==============================================================================
import os  # Para navegar pelas pastas e arquivos do Windows
import re  # Expressões Regulares (Regex) para identificar os padrões dos textos de log
import pandas as pd  # Para criar a tabela final que será enviada ao banco
from datetime import datetime  # Para trabalhar com datas e horas
from sqlalchemy import create_engine, text  # O motor de conexão e execução de comandos SQL no banco

# ==============================================================================
# --- CONFIGURAÇÕES GERAIS ---
# ==============================================================================
DB_HOST = "localhost" # O banco roda no seu computador
DB_USER = "postgres" # Usuário administrador
DB_PASSWORD = "cb2907cb" # Senha de acesso
DB_PORT = "5432" # Porta padrão do Postgres
TARGET_DB_NAME = "minhas_obras" # Nome do banco de dados alvo

# Caminho raiz onde todas as pastas de logs estão salvas (cada robô tem a sua subpasta aqui)
PASTA_LOGS_RAIZ = r"D:\Mestrado\Logs"

# ==============================================================================
# --- FUNÇÃO: MOTOR DE CONEXÃO ---
# ==============================================================================
def get_engine():
    """Cria e devolve o motor de conexão do SQLAlchemy."""
    return create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')

# ==============================================================================
# --- FUNÇÃO 1: LIMPAR NOME DA TABELA ---
# ==============================================================================
def sanitizar_nome_tabela(nome_pasta):
    """
    Pega o nome da pasta (Ex: 'Site Legado') e transforma num nome válido para
    o PostgreSQL (Ex: 'logs_site_legado'). O banco odeia espaços e acentos.
    """
    # Regex: Substitui tudo que NÃO for letra (a-z, A-Z) ou número (0-9) por um underline '_'
    limpo = re.sub(r'[^a-zA-Z0-9]', '_', nome_pasta)
    
    # Regex: Se tiverem ficado vários underlines juntos (ex: '__'), transforma em um só '_'
    limpo = re.sub(r'_+', '_', limpo)
    
    # Retorna com o prefixo 'logs_' e tudo em letras minúsculas
    return f"logs_{limpo.lower()}"

# ==============================================================================
# --- FUNÇÃO 2: CRIAÇÃO DA TABELA DINÂMICA ---
# ==============================================================================
def criar_tabela_dinamica(engine, nome_tabela):
    """Cria a tabela no banco de dados automaticamente caso ela ainda não exista."""
    
    # Monta o comando SQL bruto que cria as colunas e define os tipos de dados
    sql_create = f"""
    CREATE TABLE IF NOT EXISTS {nome_tabela} (
        id SERIAL PRIMARY KEY,  -- Um número automático e único para cada linha (1, 2, 3...)
        arquivo_origem VARCHAR(255),  -- O nome do arquivo .log lido
        data_hora TIMESTAMP,  -- A hora exata que o erro aconteceu lá no robô
        nivel VARCHAR(20),  -- O nível do erro (INFO, ERROR, WARNING)
        mensagem TEXT,  -- O texto do erro
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- A hora em que essa linha foi salva no banco
    );
    """
    # Abre a conexão com o banco
    with engine.connect() as conn:
        # Executa o comando SQL criado acima
        conn.execute(text(sql_create))
        # Confirma (salva) a operação no banco
        conn.commit()

# ==============================================================================
# --- FUNÇÃO 3: LÓGICA DE FATIAMENTO DO LOG (PARSE) ---
# ==============================================================================
def extrair_dados_linha(linha):
    """Lê uma linha de texto do bloco de notas e separa quem é a Data, o Nível e a Mensagem."""
    
    # Padrão Regex que lê a estrutura: "Data Hora - Nível - Mensagem"
    # Exemplo que ele lê: "2023-10-25 15:30:00,123 - ERROR - Falha de conexão"
    padrao = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?) - (\w+) - (.*)'
    
    # Tenta casar a linha de texto com o padrão acima
    match = re.match(padrao, linha)
    
    if match: # Se a linha bateu com o padrão perfeitamente...
        data_str = match.group(1) # Extrai o 1º grupo (A Data e Hora)
        nivel = match.group(2) # Extrai o 2º grupo (A palavra 'ERROR', 'INFO', etc)
        mensagem = match.group(3) # Extrai o 3º grupo (O texto do erro em si)
        
        # Verifica se a hora tem vírgula (milissegundos). Se tiver, usa um formato, senão usa outro.
        formato = '%Y-%m-%d %H:%M:%S,%f' if ',' in data_str else '%Y-%m-%d %H:%M:%S'
        
        try:
            # Tenta converter o texto da data para um objeto oficial de Data/Hora do Python
            data_obj = datetime.strptime(data_str, formato)
        except ValueError:
            # Se falhar (ex: milissegundos bugados), ele arranca a vírgula fora e pega só a hora principal
            data_obj = datetime.strptime(data_str.split(',')[0], '%Y-%m-%d %H:%M:%S')
            
        return data_obj, nivel, mensagem # Devolve os três pedaços fatiados
    
    # Se a linha não tem aquele padrão, devolve nulo (Isso é útil para linhas de quebra de erro)
    return None, None, None

# ==============================================================================
# --- FUNÇÃO 4: PROCESSAMENTO PRINCIPAL ---
# ==============================================================================
def processar_arquivos():
    """Varre as pastas, lê os logs de hoje e salva no PostgreSQL."""
    engine = get_engine() # Liga o banco
    
    # Pega a data de hoje formatada (Ex: '2023-10-25')
    data_hoje_str = datetime.now().strftime("%Y-%m-%d")

    print(f"Iniciando varredura em: {PASTA_LOGS_RAIZ}")
    print(f"Buscando apenas arquivos com a data: {data_hoje_str}")
    print("-" * 50)

    # O os.walk entra na pasta raiz e vasculha todas as pastas e subpastas automaticamente
    for raiz, pastas, arquivos in os.walk(PASTA_LOGS_RAIZ):
        
        # Ignora a pasta principal, porque os arquivos estão separados dentro das subpastas dos robôs
        if raiz == PASTA_LOGS_RAIZ:
            continue
            
        # Pega o nome da subpasta atual (Ex: 'Site Legado')
        nome_pasta_sistema = os.path.basename(raiz)
        
        # Chama a função para criar o nome da tabela (Ex: 'logs_site_legado')
        nome_tabela = sanitizar_nome_tabela(nome_pasta_sistema)
        
        # Garante que a tabela do banco exista, caso seja a primeira vez rodando
        criar_tabela_dinamica(engine, nome_tabela)

        logs_para_salvar = [] # Caixinha para acumular as linhas de log dessa pasta
        
        for arquivo in arquivos:
            # FILTRO: O arquivo precisa terminar em '.log' E o nome dele deve conter a data de hoje!
            # Isso garante que você não re-leia arquivos de log de ontem ou meses atrás.
            if arquivo.endswith(".log") and data_hoje_str in arquivo:
                caminho_completo = os.path.join(raiz, arquivo) # Monta o caminho
                print(f"Lendo: [{nome_pasta_sistema}] -> {arquivo}")
                
                try:
                    # Abre o arquivo de log no modo leitura de texto ('r') com acentos suportados
                    with open(caminho_completo, 'r', encoding='utf-8') as f:
                        log_atual = None # Reseta a variável de controle
                        
                        for linha in f: # Lê o arquivo linha por linha
                            linha_limpa = linha.rstrip() # Tira quebras de linha invísiveis do final
                            if not linha_limpa: continue # Se for uma linha vazia, ignora
                            
                            # Tenta fatiar a linha
                            data, nivel, msg = extrair_dados_linha(linha_limpa)
                            
                            # Excelente lógica para capturar erros de múltiplas linhas (Tracebacks):
                            if data: # Se ele achou uma data na linha (é uma linha nova de log)
                                if log_atual: # Se já tinha um log antigo guardado na variável...
                                    logs_para_salvar.append(log_atual) # ...Manda ele pra caixinha de salvar
                                
                                # Inicia um novo registro de log
                                log_atual = {
                                    'arquivo_origem': arquivo,
                                    'data_hora': data,
                                    'nivel': nivel,
                                    'mensagem': msg
                                }
                            else:
                                # Se a linha NÃO tem data, ela é a continuação do erro anterior!
                                if log_atual:
                                    # Então ele "cola" esse texto embaixo da mensagem do log anterior
                                    log_atual['mensagem'] += "\n" + linha_limpa
                        
                        # Quando acabar o arquivo, salva o último registro que ficou preso na memória
                        if log_atual:
                            logs_para_salvar.append(log_atual)
                            
                except Exception as e:
                    print(f"Erro ao ler arquivo {arquivo}: {e}")

        # --- SALVAMENTO NO BANCO DE DADOS ---
        if logs_para_salvar: # Se encontrou logs nas pastas...
            print(f"--> Salvando {len(logs_para_salvar)} registros na tabela '{nome_tabela}'...")
            
            # Transforma a lista de logs em uma tabela do Pandas
            df = pd.DataFrame(logs_para_salvar)
            
            # Empurra a tabela pro PostgreSQL (if_exists='append' adiciona as linhas de hoje no final)
            df.to_sql(nome_tabela, engine, if_exists='append', index=False)
            
            print("--> Sucesso!")
        else:
            print(f"--> Nenhum log novo encontrado para '{nome_pasta_sistema}' com a data de hoje.")
        
        print("-" * 50) # Divisória visual no terminal para a próxima pasta

    print("Importação concluída.")

# Gatilho inicial
if __name__ == "__main__":
    processar_arquivos()