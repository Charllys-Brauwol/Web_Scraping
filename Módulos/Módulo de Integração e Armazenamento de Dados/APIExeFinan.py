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
PASTA_DESTINO_ROOT = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiExecucaoFinanceira"
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

estados = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

COLUNAS_CSV = [
    'id_unico', 'nome_esfera_orcamentaria', 'nome_tipo_empenho', 'fonte_recurso', 'natureza_despesa',
    'numero_processo', 'descricao_empenho', 'plano_interno', 'resultado_primario',
    'tipo_credito', 'ug_emitente', 'codigo_amparo_legal', 'informacoes_complementares',
    'nome_favorecido', 'unidade_orcamentaria', 'ug_responsavel', 'plano_orcamentario',
    'autor_emenda', 'numero_nota_empenho_gerada', 'local_entrega', 'valor_empenho',
    'nr_ptres', 'id_projeto_investimento', 'data_execucao_script'
]

def get_headers():
    return {"accept": "*/*", "User-Agent": random.choice(USER_AGENTS), "Connection": "keep-alive"}

def obter_ids_do_arquivo_local(estado):
    padrao_busca = os.path.join(PASTA_ORIGEM_ROOT, f"*_{estado}_*.csv")
    arquivos = glob.glob(padrao_busca)
    
    if not arquivos:
        print(f"   [AVISO] Arquivo fonte não encontrado para {estado}")
        return []

    arquivo_recente = max(arquivos, key=os.path.getmtime)
    
    try:
        with open(arquivo_recente, 'r', encoding='utf-8') as f:
            sep = ';' if ';' in f.readline() else ','
        
        def is_id_column(c): return c.lower().strip() in ['identificador_unico', 'identificador único', 'id_unico']
        
        try: df = pd.read_csv(arquivo_recente, sep=sep, usecols=is_id_column, dtype=str, low_memory=True)
        except: df = pd.read_csv(arquivo_recente, sep=sep, dtype=str)
        
        if not df.empty:
            ids = df.iloc[:, 0].dropna().astype(str).str.strip()
            return ids[~ids.isin(['nan', 'NaN', '-', ''])].unique().tolist()
    except: pass
    return []

def carregar_ids_ja_processados(caminho_csv):
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
            # CORREÇÃO: Usando 'idUnico' conforme solicitado
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
    
    mapeamento = {
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
        
        pasta_estado = os.path.join(PASTA_DESTINO_ROOT, estado)
        if not os.path.exists(pasta_estado):
            os.makedirs(pasta_estado)

        ids_origem = obter_ids_do_arquivo_local(estado)
        
        if not ids_origem: 
            print(f"   Nenhum ID encontrado.")
            continue
        
        nome_arq = f"execucao_financeira_{estado}_CONSOLIDADO.csv"
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
                ph['id_projeto_investimento'] = clean_pid
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