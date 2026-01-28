import psycopg2
import pandas as pd
from sqlalchemy import create_engine
import os
import glob
import re
import sys
from datetime import datetime
import warnings

# Ignora avisos
warnings.simplefilter(action='ignore', category=UserWarning)

# --- CONFIGURAÇÕES ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb"
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras"
PASTA_RAIZ_PAD = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ExtPAD"

def get_engine():
    return create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')

def limpar_valor_monetario(valor):
    if pd.isna(valor): return 0.0
    if isinstance(valor, (float, int)): return float(valor)
    
    val_str = str(valor).strip()
    val_str = val_str.replace('R$', '').replace('"', '').replace("'", "").strip()
    if not val_str: return 0.0
    
    # Lógica BR (1.000,00)
    if ',' in val_str:
        if '.' in val_str:
            if val_str.rfind(',') > val_str.rfind('.'):
                val_str = val_str.replace('.', '').replace(',', '.')
        else:
            val_str = val_str.replace(',', '.')
            
    try: return float(val_str)
    except: return 0.0

def extrair_texto_flexivel(linha, chave):
    if chave in linha:
        try:
            resto = linha.split(chave, 1)[1]
            partes = [p.strip() for p in resto.replace('nan', '').split(':') if p.strip()]
            if partes:
                return partes[0].strip().strip('"').strip(',').strip()
        except: pass
    return None

def cacar_valor_regex_avancado(linha, chave):
    try:
        chave_escapada = re.escape(chave)
        padrao = chave_escapada + r'.*?(?:R\$)?\s*([\d\.,]+)'
        match = re.search(padrao, linha, re.IGNORECASE)
        if match:
            valor_texto = match.group(1)
            if re.search(r'\d', valor_texto):
                return limpar_valor_monetario(valor_texto)
    except: pass
    return 0.0

def processar_arquivo_hibrido(caminho_arquivo):
    nome_arquivo = os.path.basename(caminho_arquivo)
    
    # ID Único
    match_id = re.search(r'(\d+\.\d+-\d+)', nome_arquivo)
    id_unico = match_id.group(1) if match_id else 'NAO_IDENTIFICADO'

    metadados = {
        'id_unico': id_unico,
        'arquivo_origem': nome_arquivo,
        'codigo_instrumento': None, 'concedente': None, 'convenente': None, 
        'situacao': None, 'data_geracao_relatorio': None,
        
        'cabecalho_valor_total_previsto': 0.0,
        'cabecalho_valor_previsto_custeio': 0.0,
        'cabecalho_valor_previsto_investimento': 0.0,
        'cabecalho_valor_total_executado': 0.0,
        'cabecalho_valor_executado_custeio': 0.0,
        'cabecalho_valor_executado_investimento': 0.0,
        'cabecalho_saldo_total': 0.0,
        'cabecalho_saldo_custeio': 0.0,
        'cabecalho_saldo_investimento': 0.0
    }

    df_bruto = None
    
    # Leitura Híbrida (Excel -> CSV)
    try:
        df_bruto = pd.read_excel(caminho_arquivo, header=None, engine='xlrd')
    except:
        try:
            df_bruto = pd.read_excel(caminho_arquivo, header=None)
        except:
            try:
                df_bruto = pd.read_csv(caminho_arquivo, header=None, sep=None, engine='python', encoding='latin-1')
            except:
                return None

    if df_bruto is None: return None

    linha_inicio_tabela = -1
    
    # --- SCAN DE METADADOS ---
    for i, row in df_bruto.head(50).iterrows():
        linha_txt = " ".join(row.astype(str))
        
        # --- CORREÇÃO: VERIFICA TABELA ANTES DE LER VALORES ---
        # Se achar a linha da tabela, PARA IMEDIATAMENTE.
        # Isso evita que ele leia "Valor Total Previsto" na linha de colunas da tabela.
        if "Tipo Despesa" in linha_txt and "Descri" in linha_txt:
            linha_inicio_tabela = i
            break
        
        # Só tenta ler metadados se NÃO for a linha da tabela
        if "Código do Instrumento" in linha_txt: metadados['codigo_instrumento'] = extrair_texto_flexivel(linha_txt, "Código do Instrumento")
        if "Concedente" in linha_txt: metadados['concedente'] = extrair_texto_flexivel(linha_txt, "Concedente")
        if "Convenente" in linha_txt: metadados['convenente'] = extrair_texto_flexivel(linha_txt, "Convenente")
        if "Situação" in linha_txt: metadados['situacao'] = extrair_texto_flexivel(linha_txt, "Situação")
        if "Gerado dia" in linha_txt: metadados['data_geracao_relatorio'] = extrair_texto_flexivel(linha_txt, "Gerado dia")
        
        # Valores (REGEX)
        if "Valor Total Previsto" in linha_txt: metadados['cabecalho_valor_total_previsto'] = cacar_valor_regex_avancado(linha_txt, "Valor Total Previsto")
        if "Valor Previsto Custeio" in linha_txt: metadados['cabecalho_valor_previsto_custeio'] = cacar_valor_regex_avancado(linha_txt, "Valor Previsto Custeio")
        if "Valor Previsto Investimento" in linha_txt: metadados['cabecalho_valor_previsto_investimento'] = cacar_valor_regex_avancado(linha_txt, "Valor Previsto Investimento")
        
        if "Valor Total Executado" in linha_txt: metadados['cabecalho_valor_total_executado'] = cacar_valor_regex_avancado(linha_txt, "Valor Total Executado")
        if "Valor Executado Custeio" in linha_txt: metadados['cabecalho_valor_executado_custeio'] = cacar_valor_regex_avancado(linha_txt, "Valor Executado Custeio")
        if "Valor Executado Investimento" in linha_txt: metadados['cabecalho_valor_executado_investimento'] = cacar_valor_regex_avancado(linha_txt, "Valor Executado Investimento")
        
        if "Saldo Total" in linha_txt: metadados['cabecalho_saldo_total'] = cacar_valor_regex_avancado(linha_txt, "Saldo Total")
        if "Saldo Custeio" in linha_txt: metadados['cabecalho_saldo_custeio'] = cacar_valor_regex_avancado(linha_txt, "Saldo Custeio")
        if "Saldo Investimento" in linha_txt: metadados['cabecalho_saldo_investimento'] = cacar_valor_regex_avancado(linha_txt, "Saldo Investimento")

    if linha_inicio_tabela == -1: return None

    # --- MONTAGEM DA TABELA ---
    try:
        df_tabela = df_bruto.iloc[linha_inicio_tabela+1:].copy()
        df_tabela.columns = df_bruto.iloc[linha_inicio_tabela].tolist()
        
        df_tabela.columns = [str(c).lower().replace(' ', '_').replace('.', '').replace('ç', 'c').replace('ã', 'a').strip() for c in df_tabela.columns]
        
        if 'tipo_despesa' in df_tabela.columns:
            df_tabela = df_tabela[df_tabela['tipo_despesa'].notna()]
            df_tabela = df_tabela[~df_tabela['tipo_despesa'].astype(str).str.contains('Total Geral', case=False)]

        for col, val in metadados.items(): df_tabela[col] = val

        if not metadados['codigo_instrumento']:
             match_inst = re.search(r'(\d+)\.(xls|csv)', nome_arquivo, re.IGNORECASE)
             if match_inst: df_tabela['codigo_instrumento'] = match_inst.group(1)

        cols_tabela = ['valor_unit', 'valor_total_previsto', 'valor_total_executado', 'saldo']
        for c in cols_tabela:
            if c in df_tabela.columns: df_tabela[c] = df_tabela[c].apply(limpar_valor_monetario)

        df_tabela['data_carga_bd'] = datetime.now()
        return df_tabela
        
    except:
        return None

def main():
    try:
        engine = get_engine()
    except Exception as e:
        print(f"Erro BD: {e}")
        return

    subpastas = [f.path for f in os.scandir(PASTA_RAIZ_PAD) if f.is_dir()]
    print(f"Processando {len(subpastas)} estados (Correção Sobrescrita)...")

    for pasta_estado in subpastas:
        uf = os.path.basename(pasta_estado).upper()
        nome_tabela = f"pad_completo_{uf.lower()}"
        print(f"\n>>> ESTADO: {uf}")
        
        arquivos = glob.glob(os.path.join(pasta_estado, "*.*"))
        arquivos = [f for f in arquivos if f.lower().endswith(('.xls', '.xlsx', '.csv'))]
        
        if not arquivos: continue

        salvos = 0
        total = len(arquivos)

        for i, arq in enumerate(arquivos, 1):
            sys.stdout.write(f"\r    {i}/{total}: {os.path.basename(arq)[:30]}... ")
            sys.stdout.flush()
            
            df = processar_arquivo_hibrido(arq)
            
            if df is not None:
                try:
                    df.to_sql(name=nome_tabela, con=engine, if_exists='append', index=False)
                    salvos += len(df)
                except: pass

        print(f"\n    [FIM] +{salvos} linhas em {nome_tabela}")

if __name__ == "__main__":
    main()