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
PASTA_DESTINO_ROOT = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiProjetoInvestimento"
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/projeto-investimento"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

estados = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

# Definição das colunas finais do CSV (Baseado no seu script original)
COLUNAS_CSV = [
    'id_unico', 'id_unico_api', 'nome', 'cep', 'endereco', 'descricao', 'funcao_social', 
    'meta_global', 'data_inicial_prevista', 'data_final_prevista', 'data_inicial_efetiva', 
    'data_final_efetiva', 'data_cadastro', 'especie', 'natureza', 'natureza_outras', 
    'situacao', 'desc_plano_nacional_politica_vinculado', 'uf', 'qdt_empregos_gerados', 
    'desc_populacao_beneficiada', 'populacao_beneficiada', 'observacoes_pertinentes', 
    'is_modelada_por_bim', 'data_situacao', 'tomadores', 'executores', 'repassadores', 
    'eixos', 'tipos', 'subtipos', 'geometrias', 'fontes_de_recurso', 'data_execucao_script'
]

def get_headers():
    return {"accept": "*/*", "User-Agent": random.choice(USER_AGENTS), "Connection": "keep-alive"}

def obter_ids_do_arquivo_local(estado):
    """Leitura OTIMIZADA (apenas coluna ID)"""
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
            time.sleep(0.1) 

        except Exception as e:
            break
            
    return buffer

def salvar_lote(dados, caminho_csv):
    existe = os.path.exists(caminho_csv)
    df = pd.DataFrame(dados)
    
    # Mapeamento dos campos da API para o CSV
    mapeamento = {
        'idUnico': 'id_unico_api', 
        'funcaoSocial': 'funcao_social',
        'metaGlobal': 'meta_global', 
        'dataInicialPrevista': 'data_inicial_prevista',
        'dataFinalPrevista': 'data_final_prevista', 
        'dataInicialEfetiva': 'data_inicial_efetiva',
        'dataFinalEfetiva': 'data_final_efetiva', 
        'dataCadastro': 'data_cadastro',
        'naturezaOutras': 'natureza_outras', 
        'descPlanoNacionalPoliticaVinculado': 'desc_plano_nacional_politica_vinculado',
        'qdtEmpregosGerados': 'qdt_empregos_gerados', 
        'descPopulacaoBeneficiada': 'desc_populacao_beneficiada',
        'populacaoBeneficiada': 'populacao_beneficiada', 
        'observacoesPertinentes': 'observacoes_pertinentes',
        'isModeladaPorBim': 'is_modelada_por_bim', 
        'dataSituacao': 'data_situacao', 
        'fontesDeRecurso': 'fontes_de_recurso'
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
        
        nome_arq = f"projeto_investimento_{estado}_CONSOLIDADO.csv"
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
            
            # Feedback Visual
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
                ph['id_unico'] = clean_pid; ph['id_unico_api'] = clean_pid
                ph['data_execucao_script'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                lote_buffer.append(ph)
            
            contador_lote += 1
            
            # Salva a cada 20
            if contador_lote >= 20: 
                salvar_lote(lote_buffer, caminho_final)
                lote_buffer = []
                contador_lote = 0
            
            # Delay Seguro (0.8 a 1.2s)
            time.sleep(random.uniform(0.8, 1.2))

        # Salva o restante
        if lote_buffer:
            salvar_lote(lote_buffer, caminho_final)

        print(f"\n   Estado {estado} concluído.")

if __name__ == "__main__":
    process_safe()