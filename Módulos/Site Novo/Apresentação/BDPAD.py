# ==============================================================================
# --- IMPORTAÇÕES ---
# ==============================================================================
import psycopg2  # Conector do PostgreSQL
import pandas as pd  # A biblioteca mestre para manipular as tabelas
from sqlalchemy import create_engine  # Motor de exportação para o banco de dados
import os  # Para manipular caminhos e arquivos no Windows
import glob  # Para listar arquivos em massa
import re  # NOVIDADE: Biblioteca de Expressões Regulares (Regex) para achar padrões de texto avançados
import sys  # Para comandos do sistema (como a barra de progresso no terminal)
from datetime import datetime  # Para registrar a hora da extração
import warnings  # Para controlar os avisos amarelos chatos do Python

# Ignora avisos inúteis (ex: o Pandas reclamando que o Excel antigo não suporta formatação)
warnings.simplefilter(action='ignore', category=UserWarning)

# ==============================================================================
# --- CONFIGURAÇÕES GERAIS ---
# ==============================================================================
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb"
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras"
PASTA_RAIZ_PAD = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD\ExtPAD" # Pasta com os downloads brutos do PAD

def get_engine():
    """Cria a conexão com o banco de dados via SQLAlchemy."""
    return create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')

# ==============================================================================
# --- FUNÇÃO: LIMPADOR DE MOEDA BRASILEIRA ---
# Transforma coisas como 'R$ 1.500,50' ou '1000' em float puro: 1500.50
# ==============================================================================
def limpar_valor_monetario(valor):
    if pd.isna(valor): return 0.0 # Se for nulo, vira zero
    if isinstance(valor, (float, int)): return float(valor) # Se já for número, ótimo
    
    # Transforma em texto, remove 'R$', aspas simples e duplas, e espaços vazios
    valor_texto = str(valor).strip()
    valor_texto = valor_texto.replace('R$', '').replace('"', '').replace("'", "").strip()
    if not valor_texto: return 0.0 # Se ficou vazio depois de limpar, vira zero
    
    # Lógica brilhante para o formato BR (Ex: 1.000,00)
    if ',' in valor_texto:
        if '.' in valor_texto: # Se tem ponto E vírgula (ex: 1.000,00)
            # Se a vírgula está depois do ponto, é padrão BR. Troca ponto por nada, e vírgula por ponto.
            if valor_texto.rfind(',') > valor_texto.rfind('.'):
                valor_texto = valor_texto.replace('.', '').replace(',', '.')
        else: # Se tem só vírgula (ex: 1000,00), troca a vírgula por ponto
            valor_texto = valor_texto.replace(',', '.')
            
    try: return float(valor_texto) # Tenta converter o texto limpo para número decimal (float)
    except: return 0.0 # Se der erro (ex: texto aleatório), vira zero

# ==============================================================================
# --- FUNÇÃO: EXTRATOR DE TEXTO FLEXÍVEL ---
# Caça palavras-chave no meio de textos bagunçados (Ex: acha o nome do "Concedente")
# ==============================================================================
def extrair_texto_flexivel(linha, chave):
    if chave in linha: # Se a palavra-chave existir na linha
        try:
            # Corta a linha ao meio a partir da palavra-chave e pega a segunda metade (o valor)
            resto = linha.split(chave, 1)[1]
            # Divide por dois pontos ':', tira lixos como 'nan' e espaços
            partes = [p.strip() for p in resto.replace('nan', '').split(':') if p.strip()]
            if partes: # Se sobrou algo válido
                return partes[0].strip().strip('"').strip(',').strip() # Retorna super limpo
        except: pass
    return None # Se não achar nada, retorna nulo

# ==============================================================================
# --- FUNÇÃO: CAÇADOR DE VALORES (REGEX) ---
# Usa Expressões Regulares para achar números financeiros escondidos no texto
# ==============================================================================
def cacar_valor_regex_avancado(linha, chave):
    try:
        chave_escapada = re.escape(chave) # Protege a palavra-chave contra caracteres especiais
        # A MÁGICA: Procura a chave + Qualquer coisa no meio + Opcionalmente um R$ + O Número com pontos e vírgulas
        padrao = chave_escapada + r'.*?(?:R\$)?\s*([\d\.,]+)'
        match = re.search(padrao, linha, re.IGNORECASE) # Executa a caçada ignorando maiúsculas/minúsculas
        if match:
            valor_texto = match.group(1) # Pega exatamente o grupo do número que o Regex achou
            if re.search(r'\d', valor_texto): # Confirma se realmente tem dígitos ali
                return limpar_valor_monetario(valor_texto) # Manda pro limpador de moeda
    except: pass
    return 0.0 # Se não achar, assume zero

# ==============================================================================
# --- FUNÇÃO: PROCESSADOR HÍBRIDO DE PLANILHAS (O CORAÇÃO DO SCRIPT) ---
# ==============================================================================
def processar_arquivo_hibrido(caminho_arquivo):
    nome_arquivo = os.path.basename(caminho_arquivo)
    
    # Caça o ID Único diretamente no nome do arquivo salvo! (Ex: procura o padrão '123.456-78')
    match_id = re.search(r'(\d+\.\d+-\d+)', nome_arquivo)
    id_unico = match_id.group(1) if match_id else 'NAO_IDENTIFICADO'

    # Cria uma "ficha" vazia para anotar os dados encontrados no cabeçalho bagunçado do Excel
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
    
    # --- LEITURA HÍBRIDA (À Prova de Falhas) ---
    try:
        # 1ª Tentativa: Tenta ler como Excel antigo (.xls) usando o motor xlrd
        df_bruto = pd.read_excel(caminho_arquivo, header=None, engine='xlrd')
    except:
        try:
            # 2ª Tentativa: Tenta ler como Excel novo (.xlsx)
            df_bruto = pd.read_excel(caminho_arquivo, header=None)
        except:
            try:
                # 3ª Tentativa: Se o governo salvou um CSV com a extensão errada de Excel (muito comum!), 
                # o motor 'python' tenta descobrir os separadores sozinho.
                df_bruto = pd.read_csv(caminho_arquivo, header=None, sep=None, engine='python', encoding='latin-1')
            except:
                return None # Se tudo falhar, abandona o arquivo

    if df_bruto is None: return None

    linha_inicio_tabela = -1 # Marcador de onde começa a tabela real dentro da planilha
    
    # --- SCAN DE METADADOS ---
    # Lê as 50 primeiras linhas da planilha (onde fica aquele cabeçalho de texto livre)
    for i, row in df_bruto.head(50).iterrows():
        linha_txt = " ".join(row.astype(str)) # Transforma a linha inteira numa string zona
        
        # --- A SACADA DE MESTRE ---
        # Se achar as palavras das colunas da tabela, o cabeçalho acabou!
        if "Tipo Despesa" in linha_txt and "Descri" in linha_txt:
            linha_inicio_tabela = i # Anota o número da linha onde a tabela de verdade começa
            break # PARA A LEITURA. Isso impede que o Regex abaixo leia as colunas da tabela por acidente.
        
        # Usa a nossa função flexível para preencher a ficha com os textos
        if "Código do Instrumento" in linha_txt: metadados['codigo_instrumento'] = extrair_texto_flexivel(linha_txt, "Código do Instrumento")
        if "Concedente" in linha_txt: metadados['concedente'] = extrair_texto_flexivel(linha_txt, "Concedente")
        if "Convenente" in linha_txt: metadados['convenente'] = extrair_texto_flexivel(linha_txt, "Convenente")
        if "Situação" in linha_txt: metadados['situacao'] = extrair_texto_flexivel(linha_txt, "Situação")
        if "Gerado dia" in linha_txt: metadados['data_geracao_relatorio'] = extrair_texto_flexivel(linha_txt, "Gerado dia")
        
        # Usa o Caçador Regex para preencher a ficha com os valores financeiros
        if "Valor Total Previsto" in linha_txt: metadados['cabecalho_valor_total_previsto'] = cacar_valor_regex_avancado(linha_txt, "Valor Total Previsto")
        if "Valor Previsto Custeio" in linha_txt: metadados['cabecalho_valor_previsto_custeio'] = cacar_valor_regex_avancado(linha_txt, "Valor Previsto Custeio")
        if "Valor Previsto Investimento" in linha_txt: metadados['cabecalho_valor_previsto_investimento'] = cacar_valor_regex_avancado(linha_txt, "Valor Previsto Investimento")
        
        if "Valor Total Executado" in linha_txt: metadados['cabecalho_valor_total_executado'] = cacar_valor_regex_avancado(linha_txt, "Valor Total Executado")
        if "Valor Executado Custeio" in linha_txt: metadados['cabecalho_valor_executado_custeio'] = cacar_valor_regex_avancado(linha_txt, "Valor Executado Custeio")
        if "Valor Executado Investimento" in linha_txt: metadados['cabecalho_valor_executado_investimento'] = cacar_valor_regex_avancado(linha_txt, "Valor Executado Investimento")
        
        if "Saldo Total" in linha_txt: metadados['cabecalho_saldo_total'] = cacar_valor_regex_avancado(linha_txt, "Saldo Total")
        if "Saldo Custeio" in linha_txt: metadados['cabecalho_saldo_custeio'] = cacar_valor_regex_avancado(linha_txt, "Saldo Custeio")
        if "Saldo Investimento" in linha_txt: metadados['cabecalho_saldo_investimento'] = cacar_valor_regex_avancado(linha_txt, "Saldo Investimento")

    if linha_inicio_tabela == -1: return None # Se varreu 50 linhas e não achou a tabela, abandona.

    # --- MONTAGEM DA TABELA OFICIAL ---
    try:
        # Pega a planilha apenas a partir da linha debaixo de onde as colunas foram achadas
        df_tabela = df_bruto.iloc[linha_inicio_tabela+1:].copy()
        # Define que o nome das colunas vai ser exatamente a linha onde a tabela começou
        df_tabela.columns = df_bruto.iloc[linha_inicio_tabela].tolist()
        
        # Limpa os nomes das colunas da tabela para o padrão snake_case do banco de dados
        df_tabela.columns = [str(c).lower().replace(' ', '_').replace('.', '').replace('ç', 'c').replace('ã', 'a').strip() for c in df_tabela.columns]
        
        # --- LIMPEZA DE LIXO DA TABELA ---
        if 'tipo_despesa' in df_tabela.columns:
            # Apaga linhas onde a Tipo de Despesa for nula (geralmente linhas em branco no meio do Excel)
            df_tabela = df_tabela[df_tabela['tipo_despesa'].notna()]
            # Apaga as linhas de soma/totais que vêm no final da tabela (o banco de dados deve somar isso sozinho depois)
            df_tabela = df_tabela[~df_tabela['tipo_despesa'].astype(str).str.contains('Total Geral', case=False)]

        # --- FUSÃO (BROADCAST) ---
        # Pega toda a ficha de metadados do cabeçalho e insere como colunas novas copiadas em TODAS as linhas da tabela
        for col, val in metadados.items(): df_tabela[col] = val

        # Tratativa extra: se falhou em achar o Código do Instrumento no texto, tenta extrair do nome do arquivo
        if not metadados['codigo_instrumento']:
             match_inst = re.search(r'(\d+)\.(xls|csv)', nome_arquivo, re.IGNORECASE)
             if match_inst: df_tabela['codigo_instrumento'] = match_inst.group(1)

        # Trata os valores monetários que ficam DENTRO da própria tabela
        cols_tabela = ['valor_unit', 'valor_total_previsto', 'valor_total_executado', 'saldo']
        for c in cols_tabela:
            if c in df_tabela.columns: df_tabela[c] = df_tabela[c].apply(limpar_valor_monetario)

        df_tabela['data_carga_bd'] = datetime.now() # Carimbo de data/hora
        return df_tabela # Devolve a tabela perfeitamente lapidada!
        
    except:
        return None # Se explodir montando a tabela, abandona

# ==============================================================================
# --- FUNÇÃO PRINCIPAL: ORQUESTRADOR ---
# ==============================================================================
def main():
    try:
        engine = get_engine() # Liga o banco
    except Exception as e:
        print(f"Erro BD: {e}")
        return

    # Lista as pastas dos estados
    subpastas = [f.path for f in os.scandir(PASTA_RAIZ_PAD) if f.is_dir()]
    print(f"Processando {len(subpastas)} estados (Correção Sobrescrita)...")

    for pasta_estado in subpastas:
        uf = os.path.basename(pasta_estado).upper() # Pega a UF
        nome_tabela = f"pad_completo_{uf.lower()}" # Define o nome da tabela (ex: pad_completo_sp)
        print(f"\n>>> ESTADO: {uf}")
        
        # Pega qualquer formato de arquivo salvo lá dentro
        arquivos = glob.glob(os.path.join(pasta_estado, "*.*"))
        # Mas filtra apenas os que são planilhas/csv
        arquivos = [f for f in arquivos if f.lower().endswith(('.xls', '.xlsx', '.csv'))]
        
        if not arquivos: continue # Se não tiver planilha, pula a UF

        salvos = 0 # Contador de quantas linhas deram certo
        total = len(arquivos)

        for i, arq in enumerate(arquivos, 1):
            # A incrível barra de progresso no terminal usando \r (Return)
            # Ele escreve na mesma linha repetidamente, substituindo o texto anterior, sem dar enter!
            sys.stdout.write(f"\r    {i}/{total}: {os.path.basename(arq)[:30]}... ")
            sys.stdout.flush() # Força a tela a atualizar no mesmo segundo
            
            df = processar_arquivo_hibrido(arq) # Manda a planilha pro nosso fatiador/limpador
            
            if df is not None:
                try:
                    # Anexa (append) os dados daquela planilha na tabela gigantesca do estado no PostgreSQL
                    df.to_sql(name=nome_tabela, con=engine, if_exists='append', index=False)
                    salvos += len(df) # Atualiza o contador de linhas
                except: pass # Se o banco recusar, ignora

        # Pula pra linha de baixo no terminal e mostra o resultado da UF
        print(f"\n    [FIM] +{salvos} linhas em {nome_tabela}")

# Gatilho
if __name__ == "__main__":
    main()