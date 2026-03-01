import os
import re
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text

# --- CONFIGURAÇÕES ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb"
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras"

# Caminho onde estão as pastas (Site Legado, APIs, PAD, Site Novo)
PASTA_LOGS_RAIZ = r"D:\Mestrado\Logs"

def get_engine():
    return create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')

# --- 1. FUNÇÃO AUXILIAR: LIMPAR NOME DA TABELA ---
def padronizar_nome_tabela(nome_pasta):
    """
    Transforma 'Site Legado' em 'logs_site_legado'.
    Remove espaços, caracteres especiais e deixa minúsculo para o Postgres.
    """
    # Remove acentos e caracteres especiais, mantendo apenas letras, numeros e underscore
    limpo = re.sub(r'[^a-zA-Z0-9]', '_', nome_pasta)
    # Remove underscores duplicados (ex: Site  Novo -> site__novo -> site_novo)
    limpo = re.sub(r'_+', '_', limpo)
    return f"logs_{limpo.lower()}"

# --- 2. CRIAÇÃO DA TABELA DINÂMICA ---
def criar_tabela_dinamica(engine, nome_tabela):
    """Cria uma tabela específica para o sistema se ela não existir."""
    
    # Atenção: Usamos f-string aqui. Em produção, cuidado com SQL Injection,
    # mas para script local de mestrado com nomes de pastas controlados, é seguro.
    sql_create = f"""
    CREATE TABLE IF NOT EXISTS {nome_tabela} (
        id SERIAL PRIMARY KEY,
        arquivo_origem VARCHAR(255),
        data_hora TIMESTAMP,
        nivel VARCHAR(20),
        mensagem TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    with engine.connect() as conn:
        conn.execute(text(sql_create))
        conn.commit()
    # print(f"Tabela '{nome_tabela}' verificada/criada.")

# --- 3. LÓGICA DE PARSE ---
def extrair_dados_linha(linha):
    padrao = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?) - (\w+) - (.*)'
    match = re.match(padrao, linha)
    if match:
        data_str = match.group(1)
        nivel = match.group(2)
        mensagem = match.group(3)
        
        formato = '%Y-%m-%d %H:%M:%S,%f' if ',' in data_str else '%Y-%m-%d %H:%M:%S'
        try:
            data_obj = datetime.strptime(data_str, formato)
        except ValueError:
            data_obj = datetime.strptime(data_str.split(',')[0], '%Y-%m-%d %H:%M:%S')
            
        return data_obj, nivel, mensagem
    return None, None, None

# --- 4. PROCESSAMENTO PRINCIPAL ---
def processar_arquivos():
    engine = get_engine()
    
    # Obtém a data de hoje no formato usado nos nomes dos arquivos (YYYY-MM-DD)
    data_hoje = datetime.now().strftime("%Y-%m-%d")

    print(f"Iniciando varredura em: {PASTA_LOGS_RAIZ}")
    print(f"Buscando apenas arquivos com a data: {data_hoje}")
    print("-" * 50)

    # Percorre pastas e subpastas
    for raiz, pastas, arquivos in os.walk(PASTA_LOGS_RAIZ):
        
        # Pula a pasta raiz (só nos interessa as subpastas: Site Legado, etc.)
        if raiz == PASTA_LOGS_RAIZ:
            continue
            
        # Define o nome do sistema baseado na pasta atual
        nome_pasta_sistema = os.path.basename(raiz)
        
        # Gera o nome da tabela no Postgres (ex: logs_site_legado)
        nome_tabela = padronizar_nome_tabela(nome_pasta_sistema)
        
        # Garante que a tabela existe antes de inserir
        criar_tabela_dinamica(engine, nome_tabela)

        logs_para_salvar = []
        
        for arquivo in arquivos:
            # FILTRO: Verifica se é .log E se o nome do arquivo contém a data de hoje
            if arquivo.endswith(".log") and data_hoje in arquivo:
                caminho_completo = os.path.join(raiz, arquivo)
                print(f"Lendo: [{nome_pasta_sistema}] -> {arquivo}")
                
                try:
                    with open(caminho_completo, 'r', encoding='utf-8') as f:
                        log_atual = None
                        
                        for linha in f:
                            linha_limpa = linha.rstrip()
                            if not linha_limpa: continue
                            
                            data, nivel, msg = extrair_dados_linha(linha_limpa)
                            
                            if data:
                                if log_atual:
                                    logs_para_salvar.append(log_atual)
                                log_atual = {
                                    'arquivo_origem': arquivo,
                                    'data_hora': data,
                                    'nivel': nivel,
                                    'mensagem': msg
                                }
                            else:
                                if log_atual:
                                    log_atual['mensagem'] += "\n" + linha_limpa
                        
                        if log_atual:
                            logs_para_salvar.append(log_atual)
                            
                except Exception as e:
                    print(f"Erro ao ler arquivo {arquivo}: {e}")

        # Inserção em lote NA TABELA ESPECÍFICA
        if logs_para_salvar:
            print(f"--> Salvando {len(logs_para_salvar)} registros na tabela '{nome_tabela}'...")
            df = pd.DataFrame(logs_para_salvar)
            
            # Removemos a coluna 'sistema' do DataFrame pois a tabela já representa o sistema
            # df['sistema'] = nome_pasta_sistema (Não precisa mais)
            
            df.to_sql(nome_tabela, engine, if_exists='append', index=False)
            print("--> Sucesso!")
        else:
            print(f"--> Nenhum log novo encontrado para '{nome_pasta_sistema}' com a data de hoje.")
        
        print("-" * 50)

    print("Importação concluída.")

if __name__ == "__main__":
    processar_arquivos()