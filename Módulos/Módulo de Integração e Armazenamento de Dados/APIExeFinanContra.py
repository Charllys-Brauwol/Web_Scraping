import requests
import pandas as pd
import os
import glob
import time
import sys
import random
from datetime import datetime

# --- CONFIGURAÇÕES ---
PASTA_ORIGEM_ROOT = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ModExtraUFID_CODIGOS"
PASTA_DESTINO_ROOT = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiExecucaoFinanceiraContrato"
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira/contrato"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

estados = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

# Definição das colunas finais do CSV
COLUNAS_CSV = [
    'id_unico', 'id_projeto_investimento', 'numero_contrato', 'vigencia_inicio', 'vigencia_fim',
    'data_assinatura', 'data_publicacao', 'objeto', 'processo',
    'receita_despesa', 'codigo_orgao', 'orgao_nome', 'fornecedor_cnpj_cpf_idgener',
    'fornecedor_nome', 'categoria', 'licitacao_numero', 'valor_global',
    'valor_acumulado', 'codigo_contrato', 'fora_vigencia', 'nr_ctrle_pncp_compra',
    'data_execucao_script'
]

def get_headers():
    return {"accept": "*/*", "User-Agent": random.choice(USER_AGENTS), "Connection": "keep-alive"}

def obter_ids_do_arquivo_local(estado):
    """Lê apenas a coluna identificador_unico do arquivo CSV."""
    padrao_busca = os.path.join(PASTA_ORIGEM_ROOT, f"*_{estado}_*.csv")
    arquivos = glob.glob(padrao_busca)
    
    if not arquivos:
        print(f"   [AVISO] Arquivo fonte não encontrado para {estado}")
        return []

    arquivo_recente = max(arquivos, key=os.path.getmtime)
    
    try:
        with open(arquivo_recente, 'r', encoding='utf-8') as f:
            sep = ';' if ';' in f.readline() else ','
        
        # Filtra apenas colunas que pareçam ser o ID Único
        def is_id_column(c): return c.lower().strip() in ['identificador_unico', 'identificador único', 'id_unico']
        
        try: df = pd.read_csv(arquivo_recente, sep=sep, usecols=is_id_column, dtype=str, low_memory=True)
        except: df = pd.read_csv(arquivo_recente, sep=sep, dtype=str)
        
        if not df.empty:
            ids = df.iloc[:, 0].dropna().astype(str).str.strip()
            # Remove lixo comum (traços, nulos)
            return ids[~ids.isin(['nan', 'NaN', '-', ''])].unique().tolist()
    except: pass
    return []

def carregar_ids_ja_processados(caminho_csv):
    """Verifica quais IDs já foram baixados para não repetir."""
    if not os.path.exists(caminho_csv): return set()
    try:
        df = pd.read_csv(caminho_csv, sep=';', usecols=['id_unico'], dtype=str)
        return set(df['id_unico'].dropna().str.strip().tolist())
    except: return set()

def fetch_data(session, clean_pid):
    page = 0
    buffer = []
    
    while True:
        try:
            # --- CORREÇÃO FINAL: Usando idUnico ---
            # Isso é obrigatório pois é a única informação que temos no CSV de origem.
            params = {
                "idUnico": clean_pid, 
                "pagina": page, 
                "tamanhoDaPagina": 100
            }
            
            resp = session.get(API_URL, params=params, headers=get_headers(), timeout=15)
            
            if resp.status_code == 429:
                print(f"\n   !!! 429 (Limite). Pausa de 45s...")
                time.sleep(45)
                continue 

            resp.raise_for_status()
            data = resp.json()
            content = data.get("content", [])
            
            if not content: break
            buffer.extend(content)
            
            if data.get("last", False): break
            page += 1
            time.sleep(0.5) 

        except Exception as e:
            break
            
    return buffer

def salvar_lote(dados, caminho_csv):
    existe = os.path.exists(caminho_csv)
    df = pd.DataFrame(dados)
    
    # Mapeamento: API -> CSV Snake Case
    mapeamento = {
        'idProjetoInvestimento': 'id_projeto_investimento', # A API retorna isso, salvamos se vier
        'numeroContrato': 'numero_contrato',
        'vigenciaInicio': 'vigencia_inicio',
        'vigenciaFim': 'vigencia_fim',
        'dataAssinatura': 'data_assinatura',
        'dataPublicacao': 'data_publicacao',
        'objeto': 'objeto',
        'processo': 'processo',
        'receitaDespesa': 'receita_despesa',
        'codigoOrgao': 'codigo_orgao',
        'orgaoNome': 'orgao_nome',
        'fornecedorCnpjCpfIdgener': 'fornecedor_cnpj_cpf_idgener',
        'fornecedorNome': 'fornecedor_nome',
        'categoria': 'categoria',
        'licitacaoNumero': 'licitacao_numero',
        'valorGlobal': 'valor_global',
        'valorAcumulado': 'valor_acumulado',
        'codigoContrato': 'codigo_contrato',
        'foraVigencia': 'fora_vigencia',
        'nrCtrlePncpCompra': 'nr_ctrle_pncp_compra'
    }
    df = df.rename(columns=mapeamento)
    
    for col in COLUNAS_CSV:
        if col not in df.columns: df[col] = None
    
    df = df[COLUNAS_CSV]
    df.to_csv(caminho_csv, mode='a', header=not existe, index=False, sep=';', encoding='utf-8-sig')

def process_safe():
    if not os.path.exists(PASTA_DESTINO_ROOT):
        os.makedirs(PASTA_DESTINO_ROOT)

    session = requests.Session() 
    
    for estado in estados:
        print(f"\n>>> PROCESSANDO: {estado}")
        
        # Cria pastas organizadas
        pasta_estado = os.path.join(PASTA_DESTINO_ROOT, estado)
        if not os.path.exists(pasta_estado):
            os.makedirs(pasta_estado)

        ids_origem = obter_ids_do_arquivo_local(estado)
        
        if not ids_origem: 
            print(f"   Nenhum ID encontrado.")
            continue
        
        nome_arq = f"execucao_financeira_contrato_{estado}_CONSOLIDADO.csv"
        caminho_final = os.path.join(pasta_estado, nome_arq)
        
        ids_feitos = carregar_ids_ja_processados(caminho_final)
        ids_pendentes = [i for i in ids_origem if i not in ids_feitos]
        
        print(f"   Total: {len(ids_origem)} | Feitos: {len(ids_feitos)} | Pendentes: {len(ids_pendentes)}")
        
        if not ids_pendentes: continue
        
        lote_buffer = []
        contador_lote = 0
        total_pendentes = len(ids_pendentes)
        
        for i, pid in enumerate(ids_pendentes, 1):
            clean_pid = str(pid).strip()
            
            sys.stdout.write(f"\r   [{i}/{total_pendentes}] Baixando: {clean_pid}   ")
            sys.stdout.flush()
            
            api_data = fetch_data(session, clean_pid)
            
            if api_data:
                for item in api_data: 
                    item['id_unico'] = clean_pid
                    item['data_execucao_script'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                lote_buffer.extend(api_data)
            else:
                ph = {c: '-' for c in COLUNAS_CSV}
                ph['id_unico'] = clean_pid
                # ph['id_projeto_investimento'] = clean_pid # Removido pois pode confundir se for vazio
                ph['data_execucao_script'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                lote_buffer.append(ph)
            
            contador_lote += 1
            if contador_lote >= 20: 
                salvar_lote(lote_buffer, caminho_final)
                lote_buffer = []
                contador_lote = 0
            
            time.sleep(random.uniform(1.5, 3.0))

        if lote_buffer:
            salvar_lote(lote_buffer, caminho_final)

        print(f"\n   Estado {estado} concluído.")

if __name__ == "__main__":
    process_safe()