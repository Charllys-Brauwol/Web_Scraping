import psycopg2             # Importa o driver de conexão para o banco de dados PostgreSQL
import os                   # Importa biblioteca para funções do sistema (caminhos, variáveis)
import traceback            # Permite rastrear e imprimir o erro detalhado caso o código falhe
import re                   # Importa Expressões Regulares para limpeza de textos e busca de padrões
import math                 # Importa funções matemáticas (usada para validar valores nulos/NaN)
from flask import Flask, render_template, jsonify, request # Importa o framework Web e utilitários de API
from psycopg2.extras import RealDictCursor # Configura o banco para retornar dados como Dicionários
from datetime import date   # Importa manipulação de datas para cálculos de prazos e hoje

# Inicializa a instância da aplicação Flask
app = Flask(__name__)

# ====================================================================
# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# ====================================================================
# Dicionário contendo as credenciais de acesso ao servidor PostgreSQL
DB_CONFIG = {
    "dbname": "minhas_obras",
    "user": "postgres", 
    "password": "your_password",
    "host": "localhost",
    "port": "5432"
}

# Mapeamento geográfico de estados por região para os filtros do Dashboard
REGIOES = {
    'Norte': ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'],
    'Nordeste': ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
    'Centro-Oeste': ['DF', 'GO', 'MT', 'MS'],
    'Sudeste': ['ES', 'MG', 'RJ', 'SP'],
    'Sul': ['PR', 'RS', 'SC']
}

def obter_conexao_db():
    """ Função que abre e retorna uma conexão ativa com o banco PostgreSQL """
    return psycopg2.connect(**DB_CONFIG)

# ====================================================================
# --- FUNÇÕES DE LIMPEZA (PYTHON E SQL) ---
# ====================================================================
def extrair_ano(data_str):
    """ Tenta isolar o ano de uma string de data (ex: '2023/01/01' -> '2023') """
    if not data_str: return None # Se não houver dado, retorna nulo
    data_str = str(data_str).strip() # Remove espaços em branco nas bordas
    if '/' in data_str: # Se for formato brasileiro com barras
        partes = data_str.split(' ')[0].split('/') # Divide por espaços e depois por barras
        if len(partes) == 3: return partes[2] # Retorna o terceiro elemento (o ano)
    elif '-' in data_str: # Se for formato internacional com hífens
        partes = data_str.split(' ')[0].split('-') # Divide por hífens
        if len(partes) >= 1 and len(partes[0]) == 4: return partes[0] # Retorna o primeiro (ano)
    elif len(data_str) == 4 and data_str.isdigit(): # Se a string já for apenas os 4 dígitos
        return data_str
    return None # Se não identificar o formato, retorna nulo

def analisar_numero(val_str):
    """ Limpa strings financeiras e converte para número decimal (float) """
    if val_str is None: return 0.0 # Se for nulo, retorna zero
    val_str = str(val_str).strip().replace(',', '.') # Troca vírgula decimal por ponto
    val_str = re.sub(r'[^0-9.-]', '', val_str) # Remove tudo que não for número, ponto ou sinal de menos
    try: return float(val_str) # Tenta converter para float
    except Exception: return 0.0 # Se falhar (texto inválido), retorna zero

def cast_num(coluna):
    """ Gera uma string de comando SQL para converter texto em numérico no banco de dados """
    if not coluna or coluna == "'0'": return "0.0::numeric" # Retorna zero caso coluna vazia
    # Cria comando SQL que limpa a string no banco e faz o CAST para NUMERIC
    return "CAST(NULLIF(REGEXP_REPLACE(REPLACE(" + coluna + "::text, ',', '.'), '[^0-9.-]', '', 'g'), '') AS numeric)"

# ====================================================================
# --- FUNÇÕES AUXILIARES DE MAPEAMENTO (DINÂMICA DE TABELAS) ---
# ====================================================================
def descobrir_tabelas(cursor):
    """ Varre o banco de dados para encontrar quais tabelas são Legado ou do Padrão Novo """
    # Busca nomes de todas as tabelas no esquema público do banco
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    todas_tabelas = [r['table_name'] for r in cursor.fetchall()] # Armazena nomes em uma lista
    
    lista_legado = [] # Lista para tabelas de ministérios antigos
    lista_novo = []   # Lista para tabelas no formato 'modext' (organizadas por UF)
    
    for tabela in todas_tabelas: # Itera sobre cada tabela encontrada
        nome_minusculo = tabela.lower() # Converte nome para minúsculo para comparar
        if 'modextufid' in nome_minusculo: # Identifica se segue o padrão 'modext'
            partes = tabela.split('_') # Divide o nome para achar a UF
            uf = partes[-1].upper() if len(partes[-1]) == 2 else 'BR' # Pega a UF do final do nome
            lista_novo.append({'nome': tabela, 'uf': uf}) # Adiciona à lista de novas tabelas
        elif ('ministerio' in nome_minusculo or 'presidencia' in nome_minusculo) and 'modext' not in nome_minusculo:
            lista_legado.append(tabela) # Adiciona à lista de legado se for tabela de ministério
            
    return lista_legado, lista_novo # Retorna as duas listas categorizadas

def validar_colunas(cursor, nome_tabela, tipo):
    """ Checa quais colunas existem em uma tabela para evitar erros de SQL 'coluna não encontrada' """
    try:
        # Consulta as colunas existentes na tabela atual no dicionário de dados do Postgres
        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{nome_tabela}'")
        colunas = [r['column_name'] for r in cursor.fetchall()] # Lista de nomes de colunas
        
        if tipo == 'legado': # Lógica para mapear nomes variados em tabelas de ministérios
            col_municipio = None
            if 'município' in colunas: col_municipio = '"município"' # Trata acentuação
            elif 'municipio' in colunas: col_municipio = 'municipio' # Sem acentuação
            
            # Tenta encontrar a coluna de data de início (pode variar o nome entre tabelas)
            col_ano = '"ano_início_obra"' if 'ano_início_obra' in colunas else ('ano_inicio_obra' if 'ano_inicio_obra' in colunas else None)
            
            # Tenta encontrar a coluna de data de fim ou conclusão
            col_fim = None
            if 'ano_fim_obra' in colunas: col_fim = '"ano_fim_obra"'
            elif 'ano_conclusao_obra' in colunas: col_fim = '"ano_conclusao_obra"'
            elif 'data_termino_obra' in colunas: col_fim = '"data_termino_obra"'
            
            # Tenta mapear o percentual físico de execução
            col_fisico = '"percentual_execucao"' if 'percentual_execucao' in colunas else ('"percentual_fisico"' if 'percentual_fisico' in colunas else '0')
            
            # Retorna o nome da tabela e os nomes corretos das colunas encontradas
            return f'"{nome_tabela}"', col_municipio, {'ano': col_ano, 'fim': col_fim, 'fisico': col_fisico}
            
        elif tipo == 'novo': # Lógica de mapeamento para as tabelas do padrão Novo
            mapa_colunas = {} # Dicionário para guardar o "mapa" de colunas desta tabela
            if 'investimento_previsto' in colunas: mapa_colunas['valor'] = '"investimento_previsto"'
            if 'identificador_único' in colunas: mapa_colunas['id'] = '"identificador_único"'
            if 'objeto' in colunas: mapa_colunas['objeto'] = '"objeto"'
            elif 'nome__apelido_' in colunas: mapa_colunas['objeto'] = '"nome__apelido_"'
            if 'situação_da_intervenção' in colunas: mapa_colunas['situacao'] = '"situação_da_intervenção"'
            if 'executor_da_obra' in colunas: mapa_colunas['cidade'] = '"executor_da_obra"'
            else: mapa_colunas['cidade'] = f"'{nome_tabela.split('_')[-1]}'" # Usa a UF do nome caso não tenha coluna de cidade
            
            if 'data_inicial_prevista' in colunas: mapa_colunas['data_inicio'] = '"data_inicial_prevista"'
            if 'data_final_prevista' in colunas: mapa_colunas['data_fim'] = '"data_final_prevista"'
            
            # Mapeia naturezas de obra (espécie/tipo)
            if 'espécie' in colunas: mapa_colunas['natureza'] = '"espécie"'
            elif 'especie' in colunas: mapa_colunas['natureza'] = '"especie"'
            elif 'tipo_natureza_da_intervenção' in colunas: mapa_colunas['natureza'] = '"tipo_natureza_da_intervenção"'
            else: mapa_colunas['natureza'] = "'Não Informado'"

            mapa_colunas['funcao'] = '"função_social"' if 'função_social' in colunas else "'Não Informado'"
            mapa_colunas['fisico'] = '"percentual_execucao"' if 'percentual_execucao' in colunas else '0'

            # Valida se as colunas essenciais foram encontradas
            if 'id' in mapa_colunas and 'valor' in mapa_colunas:
                return f'"{nome_tabela}"', None, mapa_colunas
            
        return None, None, None # Se não validar, retorna nulos
    except: return None, None, None # Em caso de erro, retorna nulos

# ====================================================================
# --- ROTAS DE APRESENTAÇÃO (CARREGAMENTO DAS PÁGINAS) ---
# ====================================================================
@app.route('/')
def index(): return render_template('index.html') # Carrega a página inicial do Dashboard

@app.route('/evolucao')
def evolucao(): return render_template('evolucao.html') # Carrega página de gráficos de tempo

@app.route('/financeiros')
def financeiros(): return render_template('financeiros.html') # Carrega página de investimentos

@app.route('/situacao')
def situacao(): return render_template('situacao.html') # Carrega página de status das obras

@app.route('/classificacao')
def classificacao(): return render_template('classificacao.html') # Carrega página de categorias

# ====================================================================
# --- APIS DE DADOS (RETORNAM JSON PARA O FRONTEND) ---
# ====================================================================

# 1. API DRILLDOWN (Navegação Geográfica Nacional -> Região -> UF -> Cidade)
@app.route('/api/drilldown')
def obter_detalhamento():
    """ Gera os dados para o mapa e listas de obras filtradas por local """
    fonte = request.args.get('source', 'legado').strip() # 'legado' ou 'novo'
    regiao = request.args.get('region', '').strip()     # Região (ex: Nordeste)
    uf = request.args.get('uf', '').strip()             # Estado (ex: CE)
    cidade = request.args.get('city', '').strip()       # Município

    conexao = obter_conexao_db() # Abre conexão com o banco
    cursor = conexao.cursor(cursor_factory=RealDictCursor) # Cria cursor para retornar dicionários
    resp = {"totals": {"qtd": 0, "valor": 0}, "breakdown": [], "works": []} # Estrutura da resposta JSON
    consultas = [] # Lista para armazenar as partes da query SQL (UNION ALL)
    limite_sql = "" if (uf or cidade) else " LIMIT 1000" # Limita resultados na visão nacional para performance

    try:
        tabelas_legado, tabelas_novo = descobrir_tabelas(cursor) # Descobre quais tabelas usar
        
        if fonte == 'legado': # Monta queries para tabelas de ministérios
            for tabela in tabelas_legado:
                tbl, col_municipio, _ = validar_colunas(cursor, tabela, 'legado')
                if tbl and col_municipio:
                    origem_nome = tabela.replace('MINISTERIO_', '').replace('ministerio_', '').upper()
                    # Adiciona o comando SELECT desta tabela à lista de uniões
                    consultas.append(f'''SELECT UPPER(TRIM(uf)) as uf, {col_municipio} as cidade, "investimento_total" as valor, id_obra::text as id, objeto, "situação_atual" as situacao, '{origem_nome}' as origem FROM {tbl}''')
                    
        elif fonte == 'novo': # Monta queries para tabelas padronizadas (modext)
            uf_alvo = uf.upper() if uf else None
            regiao_alvo = REGIOES.get(regiao, []) if regiao else []
            for item in tabelas_novo:
                incluir_tabela = False # Lógica para filtrar quais tabelas de UF entrarão na query
                if uf_alvo: incluir_tabela = (item['uf'] == uf_alvo)
                elif regiao_alvo: incluir_tabela = (item['uf'] in regiao_alvo)
                else: incluir_tabela = True
                
                if incluir_tabela:
                    tbl, _, mapa_cols = validar_colunas(cursor, item['nome'], 'novo')
                    if tbl and mapa_cols:
                        obj_padrao = "'Sem Objeto'"
                        sit_padrao = "'Sem Situação'"
                        consultas.append(f'''SELECT '{item['uf']}' as uf, {mapa_cols['cidade']} as cidade, {mapa_cols['valor']} as valor, {mapa_cols['id']} as id, {mapa_cols.get('objeto', obj_padrao)} as objeto, {mapa_cols.get('situacao', sit_padrao)} as situacao, 'Novo' as origem FROM {tbl}''')

        if consultas: # Se houver tabelas a consultar
            sql_unido = " UNION ALL ".join(consultas) # Junta todos os SELECTs em um só
            filtro_base = "WHERE 1=1" # Base neutra para filtros adicionais
            
            if fonte == 'legado': # Filtros específicos para tabelas antigas
                filtro_base += " AND LENGTH(TRIM(uf)) = 2"
                if uf: filtro_base += f" AND UPPER(TRIM(uf)) = '{uf.upper().strip()}'"
                elif regiao: 
                    lista_regional = "', '".join(REGIOES.get(regiao, []))
                    if lista_regional: filtro_base += f" AND UPPER(TRIM(uf)) IN ('{lista_regional}')"
                    
            base_completa = f"SELECT * FROM ({sql_unido}) as t {filtro_base}" # Subquery com dados brutos
            consulta_filtrada = base_completa
            
            if cidade: # Aplica filtro de cidade se necessário
                cidade_segura = cidade.replace("'", "''") 
                consulta_filtrada = f"SELECT * FROM ({base_completa}) as t WHERE cidade = '{cidade_segura}'"

            # Executa cálculo dos totais gerais da seleção
            cursor.execute(f"SELECT COUNT(*) as qtd, SUM(valor) as valor FROM ({consulta_filtrada}) as t")
            total = cursor.fetchone()
            resp["totals"] = {"qtd": total['qtd'] or 0, "valor": total['valor'] or 0.0}

            # Lógica para agrupar os dados conforme o nível de navegação (Nacional/Região/UF)
            if uf: # Se estiver em um Estado, agrupa por Cidade
                cursor.execute(f"SELECT cidade as label, COUNT(*) as qtd, SUM(valor) as valor FROM ({base_completa}) as t GROUP BY cidade ORDER BY qtd DESC")
                resp["breakdown"] = cursor.fetchall()
            elif regiao: # Se estiver em uma Região, agrupa por UF
                cursor.execute(f"SELECT uf as label, COUNT(*) as qtd, SUM(valor) as valor FROM ({base_completa}) as t GROUP BY uf ORDER BY qtd DESC")
                resp["breakdown"] = cursor.fetchall()
            else: # Se estiver no Brasil todo, agrupa por Região geográfica
                cursor.execute(f"SELECT uf, COUNT(*) as qtd, SUM(valor) as valor FROM ({base_completa}) as t GROUP BY uf")
                linhas = cursor.fetchall()
                mapa_regioes = {}
                for r in linhas:
                    if not r['uf']: continue
                    u = r['uf'].upper().strip()
                    reg = 'Outra'
                    for k, v in REGIOES.items(): 
                        if u in v: reg = k; break
                    if reg not in mapa_regioes: mapa_regioes[reg] = {'qtd': 0, 'valor': 0}
                    mapa_regioes[reg]['qtd'] += r['qtd']
                    mapa_regioes[reg]['valor'] += (r['valor'] or 0)
                for k, v in mapa_regioes.items(): 
                    resp["breakdown"].append({'label': k, 'qtd': v['qtd'], 'valor': v['valor']})
                resp["breakdown"] = sorted(resp["breakdown"], key=lambda k: k['qtd'], reverse=True)
            
            # Busca a lista de obras individuais para mostrar na tabela do site
            if uf or cidade: 
                cursor.execute(f"SELECT id, objeto, situacao, valor, origem, cidade FROM ({consulta_filtrada}) as t {limite_sql}")
                resp["works"] = cursor.fetchall()

    except Exception: 
        traceback.print_exc() # Imprime erro no terminal caso algo falhe
    finally: 
        cursor.close() # Fecha o cursor
        conexao.close() # Fecha a conexão com o banco
        
    return jsonify(resp) # Retorna o JSON para o frontend

# 2. API TEMPORAL (Evolução por anos e análise de atrasos)
@app.route('/api/temporal')
def obter_dados_temporais():
    """ Gera dados de evolução anual e status de cumprimento de prazos """
    fonte = request.args.get('source', 'legado')
    conexao = obter_conexao_db()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    resp = {"anos_inicio": [], "anos_fim": [], "situacao": [], "atraso": []} # Estrutura de resposta

    sql_inicio = [] # Lista para queries de data de início
    sql_fim = []    # Lista para queries de data de conclusão
    sql_situacao = [] # Lista para contagem de status
    sql_atraso = []   # Lista para dados brutos de datas e IDs

    try:
        tabelas_legado, tabelas_novo = descobrir_tabelas(cursor)
        
        if fonte == 'legado': # Coleta dados de tabelas de ministérios
            for tabela in tabelas_legado:
                tbl, _, colunas = validar_colunas(cursor, tabela, 'legado')
                if tbl and colunas.get('ano'):
                    sql_inicio.append(f'''SELECT {colunas['ano']}::text as ano FROM {tbl}''')
                if tbl and colunas.get('fim'):
                    sql_fim.append(f'''SELECT {colunas['fim']}::text as ano FROM {tbl} WHERE "situação_atual" LIKE '%Conclu%' ''')
                if tbl:
                    sql_situacao.append(f'''SELECT "situação_atual" as sit FROM {tbl}''')

        elif fonte == 'novo': # Coleta dados de tabelas padronizadas
            for item in tabelas_novo:
                tbl, _, mapa_cols = validar_colunas(cursor, item['nome'], 'novo')
                if tbl and mapa_cols.get('data_inicio'):
                    # Pega apenas os 4 primeiros caracteres da data (o ano)
                    sql_inicio.append(f'''SELECT LEFT(CAST({mapa_cols['data_inicio']} AS TEXT), 4) as ano FROM {tbl}''')
                if tbl and mapa_cols.get('data_fim'):
                    # Pega o ano de fim se a obra estiver concluída ou finalizada
                    sql_fim.append(f'''SELECT LEFT(CAST({mapa_cols['data_fim']} AS TEXT), 4) as ano FROM {tbl} WHERE {mapa_cols['situacao']} LIKE '%Conclu%' OR {mapa_cols['situacao']} LIKE '%Finaliza%' ''')
                if tbl:
                    sql_situacao.append(f'''SELECT {mapa_cols['situacao']} as sit FROM {tbl}''')
                
                # Busca dados detalhados para o cálculo de atraso em Python
                if tbl and mapa_cols.get('data_fim'):
                    obj_padrao = "'Sem Objeto'"
                    cid_padrao = "'Sem Cidade'"
                    val_padrao = "0"
                    sql_atraso.append(f'''SELECT {mapa_cols['id']}::text as id, {mapa_cols.get('objeto', obj_padrao)} as objeto, {mapa_cols.get('cidade', cid_padrao)} as cidade, {mapa_cols.get('valor', val_padrao)} as valor, {mapa_cols['data_fim']}::text as data_fim, {mapa_cols['situacao']}::text as situacao FROM {tbl} WHERE {mapa_cols['data_fim']} IS NOT NULL''')
        
        # Processa contagem de obras iniciadas por ano
        if sql_inicio:
            query_completa = " UNION ALL ".join(sql_inicio)
            cursor.execute(f"SELECT ano, COUNT(*) as qtd FROM ({query_completa}) as t WHERE ano IS NOT NULL GROUP BY ano ORDER BY ano")
            resultados = cursor.fetchall()
            # Filtra apenas anos realistas para evitar erros de digitação na base (1991 até 2034)
            resp["anos_inicio"] = [r for r in resultados if r['ano'] and r['ano'].isdigit() and 1990 < int(r['ano']) < 2035]

        # Processa contagem de obras concluídas por ano
        if sql_fim:
            query_completa = " UNION ALL ".join(sql_fim)
            cursor.execute(f"SELECT ano, COUNT(*) as qtd FROM ({query_completa}) as t WHERE ano IS NOT NULL GROUP BY ano ORDER BY ano")
            resultados = cursor.fetchall()
            resp["anos_fim"] = [r for r in resultados if r['ano'] and r['ano'].isdigit() and 1990 < int(r['ano']) < 2035]
        
        # Consolida os tipos de situação (Status) encontrados
        if sql_situacao:
            query_completa = " UNION ALL ".join(sql_situacao)
            cursor.execute(f"SELECT sit, COUNT(*) as qtd FROM ({query_completa}) as t GROUP BY sit ORDER BY qtd DESC")
            resp["situacao"] = cursor.fetchall()

        # Lógica de cálculo de atraso (Compara a data de fim prevista com a data de HOJE)
        if sql_atraso:
            query_atrasos = " UNION ALL ".join(sql_atraso)
            cursor.execute(query_atrasos) # Puxa todos os dados brutos de datas
            resultados_atraso = cursor.fetchall()
            
            contadores = {
                'Atrasadas': {'label': 'Atrasadas', 'qtd': 0, 'obras': []},
                'No Prazo': {'label': 'No Prazo', 'qtd': 0, 'obras': []},
                'Concluídas': {'label': 'Concluídas', 'qtd': 0, 'obras': []}
            }
            
            hoje = date.today() # Pega a data atual do servidor
            
            for r in resultados_atraso:
                sit = str(r['situacao'] or '').lower()
                dt_str = str(r['data_fim'] or '').strip()
                obra_dict = {'id': r['id'], 'objeto': r['objeto'], 'cidade': r['cidade'], 'situacao': r['situacao'], 'valor': r['valor'], 'data_fim': dt_str}
                
                # Se status indica fim, coloca em concluídas
                if 'conclu' in sit or 'finaliza' in sit:
                    contadores['Concluídas']['qtd'] += 1
                    if len(contadores['Concluídas']['obras']) < 300: contadores['Concluídas']['obras'].append(obra_dict)
                # Se estiver em execução ou andamento, checa a data
                elif 'execu' in sit or 'andamento' in sit:
                    try:
                        dt_obj = None
                        # Tenta converter a string de data do banco para um objeto de data do Python
                        if '/' in dt_str: 
                            p = dt_str.split(' ')[0].split('/')
                            if len(p) == 3: dt_obj = date(int(p[2]), int(p[1]), int(p[0]))
                        elif '-' in dt_str: 
                            p = dt_str.split(' ')[0].split('-')
                            if len(p) == 3: dt_obj = date(int(p[0]), int(p[1]), int(p[2]))
                        
                        if dt_obj:
                            if dt_obj < hoje: # Se a data prevista já passou e a obra continua "em andamento" = Atrasada
                                contadores['Atrasadas']['qtd'] += 1
                                if len(contadores['Atrasadas']['obras']) < 300: contadores['Atrasadas']['obras'].append(obra_dict)
                            else: # Se a data ainda não chegou = No Prazo
                                contadores['No Prazo']['qtd'] += 1
                                if len(contadores['No Prazo']['obras']) < 300: contadores['No Prazo']['obras'].append(obra_dict)
                    except: pass # Ignora erros de datas mal formatadas
            
            # Formata o dicionário final de atrasos para a resposta JSON
            resp["atraso"] = [v for k, v in contadores.items() if v['qtd'] > 0]

    except Exception: 
        traceback.print_exc()
    finally: 
        cursor.close()
        conexao.close()
        
    return jsonify(resp)

# 3. API FINANCEIRO (Maiores investimentos por UF, Cidade e Órgão)
@app.route('/api/financeiro')
def obter_dados_financeiros():
    """ Agrupa os maiores volumes de recursos financeiros """
    fonte = request.args.get('source', 'legado').strip()
    uf = request.args.get('uf', '').strip()
    cidade = request.args.get('city', '').strip()
    
    conexao = obter_conexao_db()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    resp = {"uf": [], "cidade": [], "orgao": [], "works": []} # Estrutura de resposta
    
    consultas = []
    limite_sql = " LIMIT 300" if cidade else "" # Limite para não sobrecarregar o gráfico

    try:
        tabelas_legado, tabelas_novo = descobrir_tabelas(cursor)
        
        if fonte == 'legado':
            for tabela in tabelas_legado:
                tbl, col_municipio, _ = validar_colunas(cursor, tabela, 'legado')
                if tbl and col_municipio:
                    origem_nome = tabela.replace('MINISTERIO_', '').replace('ministerio_', '').upper()
                    consultas.append(f'''SELECT UPPER(TRIM(uf)) as uf, {col_municipio} as cidade, '{origem_nome}' as orgao, "investimento_total" as valor, id_obra::text as id, objeto, "situação_atual" as situacao, '{origem_nome}' as origem FROM {tbl}''')
        
        elif fonte == 'novo':
            uf_alvo = uf.upper() if uf else None
            for item in tabelas_novo:
                if uf_alvo and item['uf'] != uf_alvo: continue
                tbl, _, mapa_cols = validar_colunas(cursor, item['nome'], 'novo')
                if tbl:
                    col_municipio = mapa_cols.get('cidade', "'Sem Cidade'")
                    # Define qual o órgão financiador (Novo ou Executor específico)
                    if 'cidade' in mapa_cols and 'executor' in mapa_cols['cidade']:
                        col_orgao = mapa_cols['cidade']
                    else:
                        col_orgao = f"'Novo - {item['uf']}'"
                    
                    obj_padrao = "'Sem Objeto'"
                    sit_padrao = "'Sem Situação'"
                    consultas.append(f'''SELECT '{item['uf']}' as uf, {col_municipio} as cidade, {col_orgao} as orgao, {mapa_cols['valor']} as valor, {mapa_cols['id']} as id, {mapa_cols.get('objeto', obj_padrao)} as objeto, {mapa_cols.get('situacao', sit_padrao)} as situacao, 'Novo' as origem FROM {tbl}''')

        if consultas:
            sql_unido = " UNION ALL ".join(consultas)
            filtro_base = "WHERE 1=1"
            if fonte == 'legado':
                filtro_base += " AND LENGTH(TRIM(uf))=2"

            base_completa = f"SELECT * FROM ({sql_unido}) as t {filtro_base}"
            
            # Filtra por Estado (UF)
            filtrar_uf = base_completa
            if uf: filtrar_uf = f"SELECT * FROM ({base_completa}) as t WHERE UPPER(TRIM(uf)) = '{uf.upper()}'"
            
            # Filtra por Cidade
            filtrar_cidade = filtrar_uf
            if cidade: 
                cidade_segura = cidade.replace("'", "''")
                filtrar_cidade = f"SELECT * FROM ({filtrar_uf}) as t WHERE cidade = '{cidade_segura}'"

            # Agrupa por UF se não houver filtro de estado
            if not uf:
                cursor.execute(f"SELECT uf as label, SUM(valor) as valor FROM ({base_completa}) as t GROUP BY uf ORDER BY valor DESC")
                resp["uf"] = cursor.fetchall()
            
            # Agrupa por Cidade se um Estado estiver selecionado
            if uf:
                cursor.execute(f"SELECT cidade as label, SUM(valor) as valor FROM ({filtrar_uf}) as t WHERE cidade IS NOT NULL GROUP BY cidade ORDER BY valor DESC LIMIT 20")
                resp["cidade"] = cursor.fetchall()

            # Agrupa pelos maiores Órgãos financiadores
            cursor.execute(f"SELECT orgao as label, SUM(valor) as valor FROM ({filtrar_cidade}) as t WHERE orgao IS NOT NULL GROUP BY orgao ORDER BY valor DESC LIMIT 10")
            resp["orgao"] = cursor.fetchall()

            # Retorna as obras individuais mais caras para a tabela
            if cidade:
                cursor.execute(f"SELECT id, objeto, situacao, valor, origem, cidade FROM ({filtrar_cidade}) as t ORDER BY valor DESC {limite_sql}")
                resp["works"] = cursor.fetchall()

    except Exception: 
        traceback.print_exc()
    finally: 
        cursor.close()
        conexao.close()
        
    return jsonify(resp)

# 4. API SITUAÇÃO (Gráficos de Status e Progresso Físico Médio)
@app.route('/api/situacao')
def obter_dados_situacao():
    """ Analisa a situação das obras e a média de execução física """
    fonte = request.args.get('source', 'legado').strip()
    uf_param = request.args.get('uf', '').strip().upper()
    conexao = obter_conexao_db()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    
    nivel_str = "city" if uf_param else "uf"
    resp = {"status": [], "execucao": [], "works": [], "level": nivel_str}
    sql_status = [] # Queries para contagem de status
    sql_execucao = [] # Queries para médias físicas por local
    sql_obras = [] # Queries para lista detalhada de obras

    try:
        tabelas_legado, tabelas_novo = descobrir_tabelas(cursor)
        # Pega todas as tabelas para buscar as de "api_execucao_fisica"
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        todas_tabelas = [r['table_name'].lower() for r in cursor.fetchall()]

        if fonte == 'legado':
            for tabela in tabelas_legado:
                tbl, col_municipio, colunas = validar_colunas(cursor, tabela, 'legado')
                if tbl:
                    where_st = f" WHERE UPPER(TRIM(uf)) = '{uf_param}' " if uf_param else ""
                    sql_status.append(f'''SELECT "situação_atual" as label, COUNT(*) as qtd FROM {tbl} {where_st} GROUP BY 1''')
                    if colunas['fisico'] != '0' and colunas['fisico'] != "'0'":
                        if not uf_param:
                            # Coleta percentual físico para média nacional por UF
                            sql_execucao.append(f'''SELECT UPPER(TRIM(uf)) as label, {colunas['fisico']}::text as perc_bruto FROM {tbl} WHERE {colunas['fisico']} IS NOT NULL''')
                        else:
                            # Coleta dados para lista detalhada por Estado
                            col_municipio_seguro = col_municipio if col_municipio else "'Sem Município'"
                            sql_obras.append(f'''SELECT id_obra::text as id, COALESCE(objeto, 'Sem Objeto') as objeto, COALESCE({col_municipio_seguro}, 'Sem Município') as cidade_json, COALESCE("situação_atual", 'Não Informado') as situacao, 'Não Informado' as especie, {colunas['fisico']}::text as perc_bruto FROM {tbl} WHERE UPPER(TRIM(uf)) = '{uf_param}' AND {colunas['fisico']} IS NOT NULL''')

        elif fonte == 'novo':
            ufs_processadas = set() # Controle para não duplicar dados de UFs

            # Parte 1: Busca status nas tabelas de projetos
            for item in tabelas_novo:
                if uf_param and item['uf'] != uf_param: continue
                tbl, _, mapa_cols = validar_colunas(cursor, item['nome'], 'novo')
                if tbl:
                    sql_status.append(f'''SELECT {mapa_cols['situacao']} as label, COUNT(*) as qtd FROM {tbl} GROUP BY 1''')

            # Parte 2: Tenta cruzar dados das tabelas de INVESTIMENTO com EXECUÇÃO FÍSICA
            for tab in todas_tabelas:
                if tab.startswith('api_projeto_investimento_'):
                    uf_tab = tab.replace('api_projeto_investimento_', '').upper()
                    if uf_param and uf_tab != uf_param: continue
                    
                    tab_fis = f"api_execucao_fisica_{uf_tab.lower()}"
                    
                    if tab_fis in todas_tabelas:
                        # Busca nomes reais das colunas para fazer o JOIN entre tabelas
                        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tab}'")
                        colunas_proj = [r['column_name'].lower() for r in cursor.fetchall()]
                        
                        col_nome = "nome" if "nome" in colunas_proj else ("descricao" if "descricao" in colunas_proj else "'Sem Objeto'")
                        col_especie = "especie" if "especie" in colunas_proj else ("natureza" if "natureza" in colunas_proj else "'Não Informado'")
                        col_cidade = "executores" if "executores" in colunas_proj else "'Sem Cidade'"
                        col_sit = "situacao" if "situacao" in colunas_proj else "'Não Informado'"
                        col_id = "id_unico" if "id_unico" in colunas_proj else "id_unico_api"

                        ufs_processadas.add(uf_tab)

                        if not uf_param:
                            # Query para média nacional por UF unindo projeto e execução física
                            sql_execucao.append(f'''SELECT '{uf_tab}' as label, f.percentual::text as perc_bruto FROM {tab} p JOIN {tab_fis} f ON p.{col_id}::text = f.id_unico::text''')
                        else:
                            # Query para lista de obras do estado unindo projeto e execução física
                            sql_obras.append(f'''SELECT p.{col_id}::text as id, COALESCE(p.{col_nome}, 'Sem Objeto') as objeto, p.{col_cidade}::text as cidade_json, COALESCE(p.{col_sit}, 'Não Informado') as situacao, COALESCE(p.{col_especie}, 'Não Informado') as especie, f.percentual::text as perc_bruto FROM {tab} p JOIN {tab_fis} f ON p.{col_id}::text = f.id_unico::text WHERE f.percentual IS NOT NULL''')

            # Parte 3: Complementa com dados de tabelas 'modext' que não foram processadas no cruzamento acima
            for item in tabelas_novo:
                if item['uf'] in ufs_processadas: continue
                if uf_param and item['uf'] != uf_param: continue
                
                tbl, _, mapa_cols = validar_colunas(cursor, item['nome'], 'novo')
                if tbl and mapa_cols and mapa_cols.get('fisico') and mapa_cols['fisico'] not in ("'0'", '0'):
                    if not uf_param:
                        sql_execucao.append(f'''SELECT '{item['uf']}' as label, {mapa_cols['fisico']}::text as perc_bruto FROM {tbl} WHERE {mapa_cols['fisico']} IS NOT NULL''')
                    else:
                        obj_col = mapa_cols.get('objeto', "'Sem Objeto'")
                        cid_col = mapa_cols.get('cidade', "'Sem Cidade'")
                        sit_col = mapa_cols.get('situacao', "'Não Informado'")
                        esp_col = mapa_cols.get('natureza', "'Não Informado'")
                        id_col = mapa_cols.get('id', "'0'")
                        sql_obras.append(f'''SELECT {id_col}::text as id, {obj_col}::text as objeto, {cid_col}::text as cidade_json, {sit_col}::text as situacao, {esp_col}::text as especie, {mapa_cols['fisico']}::text as perc_bruto FROM {tbl} WHERE {mapa_cols['fisico']} IS NOT NULL''')

        # Executa a contagem consolidada de status
        if sql_status:
            query_status = " UNION ALL ".join(sql_status)
            cursor.execute(f"SELECT label, SUM(qtd) as qtd FROM ({query_status}) as t GROUP BY label ORDER BY qtd DESC")
            resp["status"] = cursor.fetchall()

        # Calcula a média de execução física por Estado no Python
        if sql_execucao and not uf_param:
            query_exec = " UNION ALL ".join(sql_execucao)
            cursor.execute(query_exec)
            resultados_exec = cursor.fetchall()
            totais_fisico = {}
            for r in resultados_exec:
                lbl = str(r['label']).strip() if r['label'] else 'Não Informado'
                val_str = str(r['perc_bruto']).replace(',', '.')
                val_str = re.sub(r'[^0-9.-]', '', val_str)
                try: val = float(val_str)
                except ValueError: val = 0.0
                
                if lbl not in totais_fisico: totais_fisico[lbl] = {'soma': 0.0, 'qtd': 0}
                totais_fisico[lbl]['soma'] += val
                totais_fisico[lbl]['qtd'] += 1
                
            # Calcula a média aritmética para cada UF
            lista_medias = [{'label': k, 'fisico': round(v['soma'] / v['qtd'], 1)} for k, v in totais_fisico.items() if v['qtd'] > 0]
            resp["execucao"] = sorted(lista_medias, key=lambda x: x['fisico'], reverse=True)

        # Formata a lista detalhada de obras com extração de cidade de strings JSON
        if sql_obras and uf_param:
            query_obras = " UNION ALL ".join(sql_obras)
            cursor.execute(query_obras)
            resultados_obras = cursor.fetchall()
            lista_obras = []
            for r in resultados_obras:
                val_str = str(r['perc_bruto']).replace(',', '.')
                val_str = re.sub(r'[^0-9.-]', '', val_str)
                try: val = float(val_str)
                except ValueError: val = 0.0
                
                cidade_limpa = "Sem Município"
                cidade_bruta = str(r.get('cidade_json', ''))
                # Tenta achar o nome da cidade dentro de uma string que parece JSON
                if cidade_bruta:
                    match = re.search(r"['\"]nome['\"]\s*:\s*['\"]([^'\"]+)['\"]", cidade_bruta)
                    if match: cidade_limpa = match.group(1)
                    else: cidade_limpa = cidade_bruta
                
                lista_obras.append({
                    'id': r['id'],
                    'objeto': r['objeto'],
                    'cidade': cidade_limpa,
                    'situacao': r['situacao'],
                    'especie': r.get('especie', 'Não Informado'),
                    'fisico': val
                })
            # Retorna as 300 obras com maior percentual físico
            resp["works"] = sorted(lista_obras, key=lambda x: x['fisico'], reverse=True)[:300]

    except Exception as e:
        traceback.print_exc()
    finally:
        cursor.close()
        conexao.close()
        
    return jsonify(resp)

# 5. API CLASSIFICAÇÃO (Agrupamento por Natureza e Função Social)
@app.route('/api/classificacao')
def obter_dados_classificacao():
    """ Categoriza obras por palavras-chave e colunas de espécie """
    fonte = request.args.get('source', 'legado')
    conexao = obter_conexao_db()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    resp = {"natureza": [], "funcao": []} # Estrutura de resposta
    sql_natureza = [] # Queries para tipos de obra (Construção, Reforma)
    sql_funcao = []   # Queries para áreas (Saúde, Educação)

    try:
        tabelas_legado, tabelas_novo = descobrir_tabelas(cursor)
        
        # Regra SQL para categorizar obras legado baseada no texto da coluna OBJETO
        regra_natureza_legado = """
            CASE 
                WHEN UPPER(objeto) LIKE '%REFORMA%' THEN 'Reforma'
                WHEN UPPER(objeto) LIKE '%AMPLIAÇÃO%' THEN 'Reforma/Ampliação'
                WHEN UPPER(objeto) LIKE '%RESTAURAÇÃO%' THEN 'Restauração'
                WHEN UPPER(objeto) LIKE '%CONSTRUÇÃO%' THEN 'Construção/Obra'
                WHEN UPPER(objeto) LIKE '%IMPLANTAÇÃO%' THEN 'Construção/Obra'
                WHEN UPPER(objeto) LIKE '%PAVIMENTAÇÃO%' THEN 'Infraestrutura'
                WHEN UPPER(objeto) LIKE '%AQUISIÇÃO%' THEN 'Aquisição'
                ELSE 'Outros'
            END
        """
        # Regra SQL para categorizar a área social baseada no texto da coluna OBJETO
        regra_funcao_legado = """
            CASE 
                WHEN UPPER(objeto) LIKE '%ESCOLA%' OR UPPER(objeto) LIKE '%CRECHE%' THEN 'Educação'
                WHEN UPPER(objeto) LIKE '%UBS%' OR UPPER(objeto) LIKE '%HOSPITAL%' OR UPPER(objeto) LIKE '%SAÚDE%' THEN 'Saúde'
                WHEN UPPER(objeto) LIKE '%QUADRA%' OR UPPER(objeto) LIKE '%ESPORTE%' THEN 'Esporte/Lazer'
                WHEN UPPER(objeto) LIKE '%PAVIMENT%' OR UPPER(objeto) LIKE '%DRENAGEM%' OR UPPER(objeto) LIKE '%SANEAMENTO%' THEN 'Infraestrutura'
                WHEN UPPER(objeto) LIKE '%CULTURA%' OR UPPER(objeto) LIKE '%TURIS%' THEN 'Cultura/Turismo'
                WHEN UPPER(objeto) LIKE '%AGRIC%' OR UPPER(objeto) LIKE '%RURAL%' THEN 'Agricultura'
                ELSE 'Não Identificado'
            END
        """

        if fonte == 'legado':
            for tabela in tabelas_legado:
                tbl, _, _ = validar_colunas(cursor, tabela, 'legado')
                if tbl:
                    sql_natureza.append(f'''SELECT {regra_natureza_legado} as label, COUNT(*) as qtd FROM {tbl} GROUP BY 1''')
                    sql_funcao.append(f'''SELECT {regra_funcao_legado} as label, COUNT(*) as qtd FROM {tbl} GROUP BY 1''')

        elif fonte == 'novo':
            for item in tabelas_novo:
                tbl, _, mapa_cols = validar_colunas(cursor, item['nome'], 'novo')
                if tbl:
                    # Usa colunas nativas das novas tabelas para classificação
                    sql_natureza.append(f'''SELECT {mapa_cols['natureza']} as label, COUNT(*) as qtd FROM {tbl} GROUP BY 1''')
                    sql_funcao.append(f'''SELECT {mapa_cols['funcao']} as label, COUNT(*) as qtd FROM {tbl} GROUP BY 1''')

        # Consolida e retorna dados de Natureza
        if sql_natureza:
            query_completa = " UNION ALL ".join(sql_natureza)
            cursor.execute(f"SELECT UPPER(TRIM(label::text)) as label, SUM(qtd) as qtd FROM ({query_completa}) as t WHERE label IS NOT NULL GROUP BY UPPER(TRIM(label::text)) ORDER BY qtd DESC")
            resp["natureza"] = cursor.fetchall()
            
        # Consolida e retorna dados de Função Social
        if sql_funcao:
            query_completa = " UNION ALL ".join(sql_funcao)
            cursor.execute(f"SELECT UPPER(TRIM(label::text)) as label, SUM(qtd) as qtd FROM ({query_completa}) as t WHERE label IS NOT NULL GROUP BY UPPER(TRIM(label::text)) ORDER BY qtd DESC LIMIT 10")
            resp["funcao"] = cursor.fetchall()

    except Exception: 
        traceback.print_exc()
    finally: 
        cursor.close()
        conexao.close()
        
    return jsonify(resp)

# ====================================================================
# --- ROTA ISOLADA: DETALHAMENTO INDIVIDUAL DA OBRA ---
# ====================================================================

@app.route('/obra/<id_obra>')
def detalhe_obra(id_obra):
    """ Rota que apenas carrega o HTML da página de detalhes de uma obra """
    return render_template('obra.html', id_obra=id_obra)

@app.route('/api/obra/<id_obra>')
def detalhar_obra_api(id_obra):
    """ API que busca TODOS os dados de uma única obra em todas as tabelas possíveis """
    conexao = obter_conexao_db()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    
    # Estrutura JSON completa para a ficha técnica da obra
    resp = {
        "encontrado": False,
        "basico": {},
        "execucao": {
            "perc_fisico": 0.0,
            "perc_financeiro": 0.0,
            "valor_previsto": 0.0,
            "valor_empenhado": 0.0,
            "valor_desembolsado": 0.0
        },
        "cronograma": {},
        "impacto": {},
        "investimento": {},
        "gastos": []
    }
    
    # Função interna para limpar floats de forma ultra segura contra diversos formatos de texto
    def conversor_float_seguro(v):
        if v is None: return 0.0
        if isinstance(v, (int, float)):
            if math.isnan(v): return 0.0
            return float(v)
            
        v_str = str(v).strip()
        if not v_str: return 0.0
        
        v_str = re.sub(r'[^0-9.,-]', '', v_str) # Remove caracteres estranhos
        if not v_str: return 0.0
        
        # Lógica para tratar milhares e decimais (ponto vs vírgula)
        virgulas = v_str.count(',')
        pontos = v_str.count('.')
        
        if virgulas == 1 and pontos >= 1: # Caso: 1.234,56
            v_str = v_str.replace('.', '').replace(',', '.')
        elif virgulas == 1 and pontos == 0: # Caso: 1234,56
            v_str = v_str.replace(',', '.')
        elif pontos >= 1 and virgulas == 0: # Caso: 1.234.567 (formato incorreto)
            parte = v_str.rsplit('.', 1)
            if len(parte[1]) != 2:
                v_str = v_str.replace('.', '')
                
        try:
            val = float(v_str)
            if math.isnan(val): return 0.0
            return val
        except Exception:
            return 0.0

    # Função interna que busca um valor em um dicionário testando várias chaves possíveis
    def obter_chave_flexivel(dicionario, *chaves):
        for chave in chaves:
            for d_key, d_val in dicionario.items():
                if d_key.strip().lower() == chave.strip().lower():
                    return d_val
        return None

    try:
        tabelas_legado, tabelas_novo = descobrir_tabelas(cursor)
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        todas_tabelas = [r['table_name'].lower() for r in cursor.fetchall()]
        
        dados_da_obra = None
        origem_tabela = None

        # PASSO 1: Busca o ID nas tabelas de INVESTIMENTO (API)
        for tabela in todas_tabelas:
            if tabela.startswith('api_projeto_investimento_'):
                cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tabela}'")
                colunas = [r['column_name'].lower() for r in cursor.fetchall()]
                id_col = "id_unico" if "id_unico" in colunas else ("id_unico_api" if "id_unico_api" in colunas else None)
                if id_col:
                    try:
                        cursor.execute(f"SELECT * FROM {tabela} WHERE \"{id_col}\"::text = %s LIMIT 1", (id_obra,))
                        linha_resultado = cursor.fetchone()
                        if linha_resultado:
                            dados_da_obra = dict(linha_resultado)
                            origem_tabela = {'nome': tabela, 'tipo': 'api', 'uf': tabela.replace('api_projeto_investimento_', '').upper()}
                            break
                    except: 
                        conexao.rollback()
                        pass
        
        # PASSO 2: Se não achar, busca nas tabelas PADRONIZADAS (NOVO)
        if not dados_da_obra:
            for item in tabelas_novo:
                tbl, _, mapa_cols = validar_colunas(cursor, item['nome'], 'novo')
                if tbl and mapa_cols and mapa_cols.get('id'):
                    col_id = mapa_cols['id'].replace('"', '') 
                    try:
                        cursor.execute(f"SELECT * FROM {tbl} WHERE \"{col_id}\"::text = %s LIMIT 1", (id_obra,))
                        linha_resultado = cursor.fetchone()
                        if linha_resultado:
                            dados_da_obra = dict(linha_resultado)
                            origem_tabela = {'nome': item['nome'], 'tipo': 'novo', 'uf': item['uf']}
                            break
                    except: 
                        conexao.rollback()
                        pass

        # PASSO 3: Se ainda não achar, busca nas tabelas de MINISTÉRIOS (LEGADO)
        if not dados_da_obra:
            for tabela in tabelas_legado:
                try:
                    cursor.execute(f"SELECT * FROM {tabela} WHERE id_obra::text = %s LIMIT 1", (id_obra,))
                    linha_resultado = cursor.fetchone()
                    if linha_resultado:
                        dados_da_obra = dict(linha_resultado)
                        origem_tabela = {'nome': tabela, 'tipo': 'legado'}
                        break
                except: 
                    conexao.rollback()
                    pass

        # Se a obra foi encontrada em alguma das tabelas acima:
        if dados_da_obra:
            resp["encontrado"] = True
            
            # Extrai nome, UF e cidade usando as chaves flexíveis
            nome_val = str(obter_chave_flexivel(dados_da_obra, 'nome__apelido_', 'nome', 'título', 'descricao', 'objeto') or 'Não Informado')
            uf_obra = str(obter_chave_flexivel(dados_da_obra, 'uf', 'uf_localização') or origem_tabela.get('uf', 'br')).lower().strip()
            
            cidade_val = str(obter_chave_flexivel(dados_da_obra, 'município', 'municipio', 'executor_da_obra') or 'Não Informada')
            executores = obter_chave_flexivel(dados_da_obra, 'executores')
            # Limpa o nome da cidade se vier dentro de uma estrutura JSON
            if executores:
                cidade_bruta = str(executores)
                match = re.search(r"['\"]nome['\"]\s*:\s*['\"]([^'\"]+)['\"]", cidade_bruta)
                if match: cidade_val = match.group(1)

            # Monta endereço completo
            endereco = obter_chave_flexivel(dados_da_obra, 'endereco', 'endereço', 'localização_coordenadas')
            localizacao_completa = f"{cidade_val} - {uf_obra.upper()}"
            if endereco: localizacao_completa += f" ({endereco})"

            resp["basico"] = {
                "id": id_obra,
                "nome": nome_val,
                "localizacao": localizacao_completa,
                "executor": cidade_val,
                "financiador": "Governo Federal" if origem_tabela.get('tipo') != 'legado' else origem_tabela['nome'].replace('MINISTERIO_', '')
            }

            # Tenta pegar o valor total previsto do investimento
            val_total = conversor_float_seguro(obter_chave_flexivel(dados_da_obra, 'investimento_previsto', 'meta_global', 'investimento_total'))
            
            # Se for obra nova e o valor estiver zerado, tenta buscar na tabela de UF correspondente
            if val_total == 0.0 and origem_tabela.get('tipo') != 'legado' and uf_obra != 'br':
                for item in tabelas_novo:
                    if item['uf'] == uf_obra.upper():
                        try:
                            cursor.execute(f"SELECT * FROM \"{item['nome']}\" WHERE identificador_único::text = %s LIMIT 1", (id_obra,))
                            linha_mod = cursor.fetchone()
                            if linha_mod and linha_mod.get('investimento_previsto'):
                                val_total = conversor_float_seguro(linha_mod['investimento_previsto'])
                        except: 
                            conexao.rollback()
                            pass

            # BUSCA DE SALDOS CONTÁBEIS (Cruza dados de execução financeira e saldo contábil)
            val_pago_final = conversor_float_seguro(obter_chave_flexivel(dados_da_obra, 'valor_empenhado'))
            val_restos_final = conversor_float_seguro(obter_chave_flexivel(dados_da_obra, 'valor_desembolsado', 'valor_repasse'))

            if origem_tabela.get('tipo') != 'legado' and uf_obra != 'br':
                tab_fin = f"api_execucao_financeira_{uf_obra}"
                tab_saldo = f"api_saldo_contabil_{uf_obra}"
                ugs = [] # Lista de Unidades Gestoras
                
                # Acha quais UGs estão pagando por esta obra
                if tab_fin in todas_tabelas:
                    try:
                        cursor.execute(f"SELECT * FROM {tab_fin} WHERE id_unico::text = %s", (id_obra,))
                        for r in cursor.fetchall():
                            if r.get('ug_emitente'): ugs.append(str(r['ug_emitente']).strip())
                            if r.get('ug_emitente1'): ugs.append(str(r['ug_emitente1']).strip())
                    except Exception as e:
                        conexao.rollback()
                
                # Pega o saldo mais recente dessas UGs na tabela de saldos contábeis
                if ugs and tab_saldo in todas_tabelas:
                    ugs_unicas = list(set(ugs))
                    ugs_str = "','".join(ugs_unicas)
                    try:
                        cursor.execute(f"SELECT * FROM {tab_saldo} WHERE ug_emitente_filtro::text IN ('{ugs_str}')")
                        linhas_saldo = cursor.fetchall()
                        
                        if linhas_saldo:
                            for rs in reversed(linhas_saldo): # Pega a última linha (mais atual)
                                p1 = conversor_float_seguro(rs.get('vl_pago'))
                                p2 = conversor_float_seguro(rs.get('vl_pago1'))
                                r1 = conversor_float_seguro(rs.get('vl_restos_a_pagar'))
                                r2 = conversor_float_seguro(rs.get('vl_restos_a_pagar1'))
                                
                                v_pago = p1 if p1 > 0 else p2
                                v_restos = r1 if r1 > 0 else r2
                                
                                if v_pago > 0 or v_restos > 0:
                                    val_pago_final = v_pago
                                    val_restos_final = v_restos
                                    break
                    except: 
                        conexao.rollback()

            # BUSCA PERCENTUAL DE EXECUÇÃO FÍSICA
            perc_fisico = 0.0
            if origem_tabela.get('tipo') != 'legado' and uf_obra != 'br':
                tab_fis = f"api_execucao_fisica_{uf_obra}"
                if tab_fis in todas_tabelas:
                    try:
                        cursor.execute(f"SELECT * FROM {tab_fis} WHERE id_unico::text = %s LIMIT 1", (id_obra,))
                        linha_fis = cursor.fetchone()
                        if linha_fis and linha_fis.get('percentual'):
                            perc_fisico = conversor_float_seguro(linha_fis['percentual'])
                    except: 
                        conexao.rollback()
            
            if perc_fisico == 0.0: # Fallback: se não achar na tabela física, tenta na tabela de projeto
                perc_fisico = conversor_float_seguro(obter_chave_flexivel(dados_da_obra, 'percentual_execucao', 'percentual_fisico', 'execução física'))

            # Coleta Datas e Situação
            dt_inicio = obter_chave_flexivel(dados_da_obra, 'data_inicial_efetiva', 'data_início', 'data_inicial_prevista', 'ano_início_obra') or 'Não Informado'
            dt_fim = obter_chave_flexivel(dados_da_obra, 'data_final_efetiva', 'data_fim', 'data_final_prevista', 'ano_fim_obra') or 'Não Informado'
            sit = str(obter_chave_flexivel(dados_da_obra, 'situacao', 'situação_da_intervenção', 'situação_atual') or 'Não Informada')

            paralisacao = obter_chave_flexivel(dados_da_obra, 'motivo_paralisação', 'cancelamentos_paralisacoes')
            if paralisacao: sit += f" (Motivo: {paralisacao})"

            resp["cronograma"] = {
                "data_inicio": str(dt_inicio),
                "data_fim": str(dt_fim),
                "situacao": sit
            }

            # Dados de Investimento e Contrato
            modalidade = obter_chave_flexivel(dados_da_obra, 'modalidade', 'tipo_de_instrumento') or ('Transferência Fundo a Fundo' if 'fundo' in nome_val.lower() else "Convênio / Contrato de Repasse")
            fornecedor = str(obter_chave_flexivel(dados_da_obra, 'cnpj_executor') or 'Não Informado')

            # Tenta achar o nome do fornecedor/empreiteira na tabela de contratos
            if origem_tabela.get('tipo') != 'legado' and uf_obra != 'br':
                tab_contrato = f"api_execucao_financeira_contrato_{uf_obra}"
                if tab_contrato in todas_tabelas:
                    try:
                        cursor.execute(f"SELECT * FROM {tab_contrato} WHERE id_projeto_investimento::text = %s LIMIT 1", (id_obra,))
                        linha_contrato = cursor.fetchone()
                        if linha_contrato and linha_contrato.get('fornecedor_nome'):
                            fornecedor = str(linha_contrato['fornecedor_nome'])
                    except: 
                        conexao.rollback()

            resp["investimento"] = {
                "fonte": str(obter_chave_flexivel(dados_da_obra, 'fontes_de_recurso') or 'Orçamento Geral da União'),
                "modalidade": str(modalidade),
                "contrato_fornecedor": fornecedor,
                "contrato_vigencia": f"{dt_inicio} a {dt_fim}"
            }

            # Dados de Impacto Social
            funcao = obter_chave_flexivel(dados_da_obra, 'funcao_social', 'função_social', 'tipo') or 'Não Mapeada'
            empregos = obter_chave_flexivel(dados_da_obra, 'qdt_empregos_gerados', 'empregos_gerados') or 'Não Informado'
            publico = obter_chave_flexivel(dados_da_obra, 'populacao_beneficiada', 'desc_populacao_beneficiada') or 'Estimativa indisponível'

            resp["impacto"] = {
                "funcao": str(funcao),
                "publico_beneficiado": str(publico),
                "empregos": str(empregos)
            }

            # BUSCA ITENS DE GASTO DETALHADOS (PAD - Plano de Detalhamento)
            pad_table = f"pad_completo_{uf_obra}"
            if pad_table in todas_tabelas:
                try:
                    cursor.execute(f'SELECT * FROM "{pad_table}" WHERE id_unico::text = %s', (id_obra,))
                    linhas_pad = cursor.fetchall()
                    
                    for row_pad in linhas_pad:
                        dict_pad = dict(row_pad)
                        v_executado = conversor_float_seguro(obter_chave_flexivel(dict_pad, 'valor_total_executado'))
                        v_previsto = conversor_float_seguro(obter_chave_flexivel(dict_pad, 'valor_total_previsto'))
                        valor_final = v_executado if v_executado > 0 else v_previsto
                        
                        resp["gastos"].append({
                            "item": str(obter_chave_flexivel(dict_pad, 'descrição', 'descricao', 'item', 'itens') or '-'),
                            "natureza": str(obter_chave_flexivel(dict_pad, 'tipo despesa', 'tipo_despesa') or 'Material/Serviço'),
                            "qtd": conversor_float_seguro(obter_chave_flexivel(dict_pad, 'quantidade', 'qtd') or 1),
                            "preco_un": conversor_float_seguro(obter_chave_flexivel(dict_pad, 'valor_unit', 'valor_unitario') or 0),
                            "total": valor_final,
                            "fornecedor": str(obter_chave_flexivel(dict_pad, 'convenente', 'fornecedor') or '-'),
                            "data": str(obter_chave_flexivel(dict_pad, 'data_geracao_relatorio', 'data') or '-')[:10],
                            "nf": str(obter_chave_flexivel(dict_pad, 'codigo_instrumento', 'nf') or '-')
                        })
                except: 
                    conexao.rollback()

            # Cálculo final da porcentagem financeira (Quanto já foi pago do total previsto)
            perc_finan = (val_pago_final / val_total * 100) if val_total > 0 else 0
            
            resp["execucao"]["perc_fisico"] = perc_fisico
            resp["execucao"]["perc_financeiro"] = round(perc_finan, 1)
            resp["execucao"]["valor_previsto"] = val_total
            resp["execucao"]["valor_empenhado"] = val_pago_final
            resp["execucao"]["valor_desembolsado"] = val_restos_final

    except Exception as e:
        traceback.print_exc()
    finally:
        cursor.close()
        conexao.close()
        
    return jsonify(resp)

# INICIALIZAÇÃO DO SERVIDOR
if __name__ == '__main__':
    # Roda a aplicação em modo debug (mostra erros no navegador e reinicia ao salvar)
    app.run(debug=True)