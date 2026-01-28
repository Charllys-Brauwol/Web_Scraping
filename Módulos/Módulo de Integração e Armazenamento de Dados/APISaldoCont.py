import requests
import pandas as pd
import os
import glob
import time
import sys
import random
from datetime import datetime

# --- CONFIGURAÇÕES ---
# Onde buscar as UGs (Pasta gerada pelo script anterior)
PASTA_ORIGEM_ROOT = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiExecucaoFinanceira"

# Onde salvar os Saldos Contábeis
PASTA_DESTINO_ROOT = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\apiSaldoContabil"

# URL da API
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira/saldo-contabil"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

estados = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

# Colunas baseadas no retorno JSON da API
COLUNAS_CSV = [
    'ug_emitente_filtro', # Coluna extra para saber qual UG buscamos
    'ug_emitente', 'nr_nota_empenho', 'vl_transferido_exercicio_anterior', 
    'vl_transferido', 'vl_restos_a_pagar', 'vl_reinscrito_rp', 'vl_reforcado', 
    'vl_recebido_transferido', 'vl_recebido_exercicio_anterior', 'vl_pago', 
    'vl_liquidado_a_pagar', 'vl_inscrito_rp', 'vl_incluido', 'unidade_orcamentaria', 
    'vl_em_liquidacao', 'vl_cancelado_exercicio_anterior', 'vl_anulado_cancelado', 
    'vl_a_liquidar', 'data_execucao_script'
]

def get_headers():
    return {"accept": "*/*", "User-Agent": random.choice(USER_AGENTS), "Connection": "keep-alive"}

def obter_ugs_do_arquivo_local(estado):
    """
    Entra na pasta do estado, pega o CSV mais recente e extrai as UGs únicas.
    """
    # Agora a origem é hierárquica: apiExecucaoFinanceira/AC/*.csv
    pasta_estado_origem = os.path.join(PASTA_ORIGEM_ROOT, estado)
    
    if not os.path.exists(pasta_estado_origem):
        print(f"   [AVISO] Pasta do estado {estado} não encontrada na origem.")
        return []

    padrao_busca = os.path.join(pasta_estado_origem, "*.csv")
    arquivos = glob.glob(padrao_busca)
    
    if not arquivos:
        print(f"   [AVISO] Nenhum CSV encontrado em {pasta_estado_origem}")
        return []

    # Pega o arquivo mais recente
    arquivo_recente = max(arquivos, key=os.path.getmtime)
    
    try:
        # Detecta separador
        with open(arquivo_recente, 'r', encoding='utf-8') as f:
            line = f.readline()
            sep = ';' if ';' in line else ','

        # Filtra apenas a coluna 'ug_emitente'
        def is_ug_column(c): return c.lower().strip() == 'ug_emitente'
        
        # Lê apenas a coluna necessária
        df = pd.read_csv(arquivo_recente, sep=sep, usecols=is_ug_column, dtype=str, low_memory=True)
        
        if not df.empty:
            # Pega valores únicos e remove nulos
            ugs = df.iloc[:, 0].dropna().astype(str).str.strip()
            lista_ugs = ugs[~ugs.isin(['nan', 'NaN', '-', ''])].unique().tolist()
            return lista_ugs
            
    except Exception as e:
        print(f"   Erro ao ler arquivo {os.path.basename(arquivo_recente)}: {e}")
        pass
        
    return []

def carregar_ugs_ja_processadas(caminho_csv):
    """Verifica quais UGs já foram baixadas."""
    if not os.path.exists(caminho_csv): return set()
    try:
        # Lê a coluna de controle 'ug_emitente_filtro'
        df = pd.read_csv(caminho_csv, sep=';', usecols=['ug_emitente_filtro'], dtype=str)
        return set(df['ug_emitente_filtro'].dropna().str.strip().tolist())
    except: return set()

def fetch_data(session, clean_ug):
    page = 0
    buffer = []
    
    while True:
        try:
            params = {
                "ugEmitente": clean_ug,
                "pagina": page,
                "tamanhoDaPagina": 10
            }
            
            resp = session.get(API_URL, params=params, headers=get_headers(), timeout=15)
            
            if resp.status_code == 429:
                print(f"\n   !!! 429 (Limite). Pausa de 25s...")
                time.sleep(25)
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
            # Se der erro (ex: 404 ou timeout), paramos este UG e seguimos
            break
            
    return buffer

def salvar_lote(dados, caminho_csv):
    existe = os.path.exists(caminho_csv)
    df = pd.DataFrame(dados)
    
    # Mapeamento API -> CSV Snake Case
    mapeamento = {
        'ugEmitente': 'ug_emitente',
        'nrNotaEmpenho': 'nr_nota_empenho',
        'vlTransferidoExercicioAnterior': 'vl_transferido_exercicio_anterior',
        'vlTransferido': 'vl_transferido',
        'vlRestosAPagar': 'vl_restos_a_pagar',
        'vlReinscritoRp': 'vl_reinscrito_rp',
        'vlReforcado': 'vl_reforcado',
        'vlRecebidoTransferido': 'vl_recebido_transferido',
        'vlRecebidoExercicioAnterior': 'vl_recebido_exercicio_anterior',
        'vlPago': 'vl_pago',
        'vlLiquidadoAPagar': 'vl_liquidado_a_pagar',
        'vlInscritoRp': 'vl_inscrito_rp',
        'vlIncluido': 'vl_incluido',
        'unidadeOrcamentaria': 'unidade_orcamentaria',
        'vlEmLiquidacao': 'vl_em_liquidacao',
        'vlCanceladoExercicioAnterior': 'vl_cancelado_exercicio_anterior',
        'vlAnuladoCancelado': 'vl_anulado_cancelado',
        'vlALiquidar': 'vl_a_liquidar'
    }
    df = df.rename(columns=mapeamento)
    
    # Garante colunas
    for col in COLUNAS_CSV:
        if col not in df.columns: df[col] = None
    
    df = df[COLUNAS_CSV]
    df.to_csv(caminho_csv, mode='a', header=not existe, index=False, sep=';', encoding='utf-8-sig')

def process_saldo_contabil():
    if not os.path.exists(PASTA_DESTINO_ROOT):
        os.makedirs(PASTA_DESTINO_ROOT)

    session = requests.Session() 
    
    for estado in estados:
        print(f"\n>>> PROCESSANDO: {estado}")
        
        # 1. Preparar pastas
        pasta_destino_estado = os.path.join(PASTA_DESTINO_ROOT, estado)
        if not os.path.exists(pasta_destino_estado):
            os.makedirs(pasta_destino_estado)

        # 2. Obter UGs do arquivo baixado anteriormente
        ugs_origem = obter_ugs_do_arquivo_local(estado)
        
        if not ugs_origem: 
            print(f"   Nenhuma UG encontrada nos arquivos de {estado}.")
            continue
        
        nome_arq = f"saldo_contabil_{estado}_CONSOLIDADO.csv"
        caminho_final = os.path.join(pasta_destino_estado, nome_arq)
        
        # 3. Filtrar o que já foi feito
        ugs_feitas = carregar_ugs_ja_processadas(caminho_final)
        ugs_pendentes = [u for u in ugs_origem if u not in ugs_feitas]
        
        print(f"   Total UGs: {len(ugs_origem)} | Feitas: {len(ugs_feitas)} | Pendentes: {len(ugs_pendentes)}")
        
        if not ugs_pendentes: continue
        
        lote_buffer = []
        contador_lote = 0
        total_pendentes = len(ugs_pendentes)
        
        for i, ug in enumerate(ugs_pendentes, 1):
            clean_ug = str(ug).strip()
            
            sys.stdout.write(f"\r   [{i}/{total_pendentes}] Baixando UG: {clean_ug}   ")
            sys.stdout.flush()
            
            api_data = fetch_data(session, clean_ug)
            
            if api_data:
                for item in api_data: 
                    # Adiciona a UG usada na busca para controle
                    item['ug_emitente_filtro'] = clean_ug 
                    item['data_execucao_script'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                lote_buffer.extend(api_data)
            else:
                # Placeholder para registrar que a UG foi consultada
                ph = {c: '-' for c in COLUNAS_CSV}
                ph['ug_emitente_filtro'] = clean_ug
                ph['ug_emitente'] = clean_ug # Preenche visualmente
                ph['data_execucao_script'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                lote_buffer.append(ph)
            
            contador_lote += 1
            if contador_lote >= 20: 
                salvar_lote(lote_buffer, caminho_final)
                lote_buffer = []
                contador_lote = 0
            
            # Delay equilibrado
            time.sleep(random.uniform(0.8, 1.2))

        if lote_buffer:
            salvar_lote(lote_buffer, caminho_final)

        print(f"\n   Estado {estado} concluído.")

if __name__ == "__main__":
    process_saldo_contabil()