import psycopg2
import os
import traceback
import re
import math
from flask import Flask, render_template, jsonify, request
from psycopg2.extras import RealDictCursor
from datetime import date

app = Flask(__name__)

# ====================================================================
# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# ====================================================================
DB_CONFIG = {
    "dbname": "minhas_obras",
    "user": "postgres", # NÃO PODE TRADUZIR ESTA CHAVE
    "password": "cb2907cb",
    "host": "localhost",
    "port": "5432"
}

REGIOES = {
    'Norte': ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'],
    'Nordeste': ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
    'Centro-Oeste': ['DF', 'GO', 'MT', 'MS'],
    'Sudeste': ['ES', 'MG', 'RJ', 'SP'],
    'Sul': ['PR', 'RS', 'SC']
}

def obter_conexao_db():
    return psycopg2.connect(**DB_CONFIG)

# ====================================================================
# --- FUNÇÕES DE LIMPEZA (PYTHON E SQL) ---
# ====================================================================
def extrair_ano(data_str):
    if not data_str: return None
    data_str = str(data_str).strip()
    if '/' in data_str:
        partes = data_str.split(' ')[0].split('/')
        if len(partes) == 3: return partes[2]
    elif '-' in data_str:
        partes = data_str.split(' ')[0].split('-')
        if len(partes) >= 1 and len(partes[0]) == 4: return partes[0]
    elif len(data_str) == 4 and data_str.isdigit():
        return data_str
    return None

def analisar_numero(val_str):
    if val_str is None: return 0.0
    val_str = str(val_str).strip().replace(',', '.')
    val_str = re.sub(r'[^0-9.-]', '', val_str)
    try: return float(val_str)
    except Exception: return 0.0

def cast_num(coluna):
    if not coluna or coluna == "'0'": return "0.0::numeric"
    return "CAST(NULLIF(REGEXP_REPLACE(REPLACE(" + coluna + "::text, ',', '.'), '[^0-9.-]', '', 'g'), '') AS numeric)"

# ====================================================================
# --- FUNÇÕES AUXILIARES DE MAPEAMENTO ---
# ====================================================================
def descobrir_tabelas(cursor):
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    todas_tabelas = [r['table_name'] for r in cursor.fetchall()]
    
    lista_legado = []
    lista_novo = []
    
    for tabela in todas_tabelas:
        nome_minusculo = tabela.lower()
        if 'modextufid' in nome_minusculo: 
            partes = tabela.split('_')
            uf = partes[-1].upper() if len(partes[-1]) == 2 else 'BR'
            lista_novo.append({'nome': tabela, 'uf': uf})
        elif ('ministerio' in nome_minusculo or 'presidencia' in nome_minusculo or 'sec_esp' in nome_minusculo) and 'modext' not in nome_minusculo:
            lista_legado.append(tabela)
            
    return lista_legado, lista_novo

def validar_colunas(cursor, nome_tabela, tipo):
    try:
        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{nome_tabela}'")
        colunas = [r['column_name'] for r in cursor.fetchall()]
        
        if tipo == 'legado':
            col_municipio = None
            if 'município' in colunas: col_municipio = '"município"'
            elif 'municipio' in colunas: col_municipio = 'municipio'
            
            col_ano = '"ano_início_obra"' if 'ano_início_obra' in colunas else ('ano_inicio_obra' if 'ano_inicio_obra' in colunas else None)
            
            col_fim = None
            if 'ano_fim_obra' in colunas: col_fim = '"ano_fim_obra"'
            elif 'ano_conclusao_obra' in colunas: col_fim = '"ano_conclusao_obra"'
            elif 'data_termino_obra' in colunas: col_fim = '"data_termino_obra"'
            
            col_fisico = '"percentual_execucao"' if 'percentual_execucao' in colunas else ('"percentual_fisico"' if 'percentual_fisico' in colunas else '0')
            
            return f'"{nome_tabela}"', col_municipio, {'ano': col_ano, 'fim': col_fim, 'fisico': col_fisico}
            
        elif tipo == 'novo':
            mapa_colunas = {}
            if 'investimento_previsto' in colunas: mapa_colunas['valor'] = '"investimento_previsto"'
            if 'identificador_único' in colunas: mapa_colunas['id'] = '"identificador_único"'
            if 'objeto' in colunas: mapa_colunas['objeto'] = '"objeto"'
            elif 'nome__apelido_' in colunas: mapa_colunas['objeto'] = '"nome__apelido_"'
            if 'situação_da_intervenção' in colunas: mapa_colunas['situacao'] = '"situação_da_intervenção"'
            if 'executor_da_obra' in colunas: mapa_colunas['cidade'] = '"executor_da_obra"'
            else: mapa_colunas['cidade'] = f"'{nome_tabela.split('_')[-1]}'" 
            
            if 'data_inicial_prevista' in colunas: mapa_colunas['data_inicio'] = '"data_inicial_prevista"'
            if 'data_final_prevista' in colunas: mapa_colunas['data_fim'] = '"data_final_prevista"'

            if 'espécie' in colunas: mapa_colunas['natureza'] = '"espécie"'
            elif 'especie' in colunas: mapa_colunas['natureza'] = '"especie"'
            elif 'tipo_natureza_da_intervenção' in colunas: mapa_colunas['natureza'] = '"tipo_natureza_da_intervenção"'
            else: mapa_colunas['natureza'] = "'Não Informado'"

            mapa_colunas['funcao'] = '"função_social"' if 'função_social' in colunas else "'Não Informado'"
            mapa_colunas['fisico'] = '"percentual_execucao"' if 'percentual_execucao' in colunas else '0'

            if 'id' in mapa_colunas and 'valor' in mapa_colunas:
                return f'"{nome_tabela}"', None, mapa_colunas
            
        return None, None, None
    except: return None, None, None

# ====================================================================
# --- ROTAS DE APRESENTAÇÃO (FRONTEND) ---
# ====================================================================
@app.route('/')
def index(): return render_template('index.html')

@app.route('/evolucao')
def evolucao(): return render_template('evolucao.html')

@app.route('/financeiros')
def financeiros(): return render_template('financeiros.html')

@app.route('/situacao')
def situacao(): return render_template('situacao.html')

@app.route('/classificacao')
def classificacao(): return render_template('classificacao.html')


# ====================================================================
# --- APIS DE DADOS (JSON) ---
# ====================================================================

# 1. API DRILLDOWN (Navegação Geográfica)
@app.route('/api/drilldown')
def obter_detalhamento():
    fonte = request.args.get('source', 'legado').strip() # Usar 'source' se o front manda 'source'
    regiao = request.args.get('region', '').strip()
    uf = request.args.get('uf', '').strip()
    cidade = request.args.get('city', '').strip()

    conexao = obter_conexao_db()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    resp = {"totals": {"qtd": 0, "valor": 0}, "breakdown": [], "works": []}
    consultas = [] 
    limite_sql = "" if (uf or cidade) else " LIMIT 1000"

    try:
        tabelas_legado, tabelas_novo = descobrir_tabelas(cursor)
        
        if fonte == 'legado':
            for tabela in tabelas_legado:
                tbl, col_municipio, _ = validar_colunas(cursor, tabela, 'legado')
                if tbl and col_municipio:
                    origem_nome = tabela.replace('MINISTERIO_', '').replace('ministerio_', '').upper()
                    consultas.append(f'''SELECT UPPER(TRIM(uf)) as uf, {col_municipio} as cidade, "investimento_total" as valor, id_obra::text as id, objeto, "situação_atual" as situacao, '{origem_nome}' as origem FROM {tbl}''')
                    
        elif fonte == 'novo':
            uf_alvo = uf.upper() if uf else None
            regiao_alvo = REGIOES.get(regiao, []) if regiao else []
            for item in tabelas_novo:
                incluir_tabela = False
                if uf_alvo: incluir_tabela = (item['uf'] == uf_alvo)
                elif regiao_alvo: incluir_tabela = (item['uf'] in regiao_alvo)
                else: incluir_tabela = True
                
                if incluir_tabela:
                    tbl, _, mapa_cols = validar_colunas(cursor, item['nome'], 'novo')
                    if tbl and mapa_cols:
                        obj_padrao = "'Sem Objeto'"
                        sit_padrao = "'Sem Situação'"
                        consultas.append(f'''SELECT '{item['uf']}' as uf, {mapa_cols['cidade']} as cidade, {mapa_cols['valor']} as valor, {mapa_cols['id']} as id, {mapa_cols.get('objeto', obj_padrao)} as objeto, {mapa_cols.get('situacao', sit_padrao)} as situacao, 'Novo' as origem FROM {tbl}''')

        if consultas:
            sql_unido = " UNION ALL ".join(consultas)
            filtro_base = "WHERE 1=1"
            
            if fonte == 'legado':
                filtro_base += " AND LENGTH(TRIM(uf)) = 2"
                if uf: filtro_base += f" AND UPPER(TRIM(uf)) = '{uf.upper().strip()}'"
                elif regiao: 
                    lista_regional = "', '".join(REGIOES.get(regiao, []))
                    if lista_regional: filtro_base += f" AND UPPER(TRIM(uf)) IN ('{lista_regional}')"
                    
            base_completa = f"SELECT * FROM ({sql_unido}) as t {filtro_base}"
            consulta_filtrada = base_completa
            
            if cidade:
                cidade_segura = cidade.replace("'", "''") 
                consulta_filtrada = f"SELECT * FROM ({base_completa}) as t WHERE cidade = '{cidade_segura}'"

            cursor.execute(f"SELECT COUNT(*) as qtd, SUM(valor) as valor FROM ({consulta_filtrada}) as t")
            total = cursor.fetchone()
            resp["totals"] = {"qtd": total['qtd'] or 0, "valor": total['valor'] or 0.0}

            if uf: 
                cursor.execute(f"SELECT cidade as label, COUNT(*) as qtd, SUM(valor) as valor FROM ({base_completa}) as t GROUP BY cidade ORDER BY qtd DESC")
                resp["breakdown"] = cursor.fetchall()
            elif regiao: 
                cursor.execute(f"SELECT uf as label, COUNT(*) as qtd, SUM(valor) as valor FROM ({base_completa}) as t GROUP BY uf ORDER BY qtd DESC")
                resp["breakdown"] = cursor.fetchall()
            else:
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
            
            if uf or cidade: 
                cursor.execute(f"SELECT id, objeto, situacao, valor, origem, cidade FROM ({consulta_filtrada}) as t {limite_sql}")
                resp["works"] = cursor.fetchall()

    except Exception: 
        traceback.print_exc()
    finally: 
        cursor.close()
        conexao.close()
        
    return jsonify(resp)

# 2. API TEMPORAL
@app.route('/api/temporal')
def obter_dados_temporais():
    fonte = request.args.get('source', 'legado')
    conexao = obter_conexao_db()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    resp = {"anos_inicio": [], "anos_fim": [], "situacao": [], "atraso": []}

    sql_inicio = []
    sql_fim = []
    sql_situacao = []
    sql_atraso = []

    try:
        tabelas_legado, tabelas_novo = descobrir_tabelas(cursor)
        
        if fonte == 'legado':
            for tabela in tabelas_legado:
                tbl, _, colunas = validar_colunas(cursor, tabela, 'legado')
                if tbl and colunas.get('ano'):
                    sql_inicio.append(f'''SELECT {colunas['ano']}::text as ano FROM {tbl}''')
                if tbl and colunas.get('fim'):
                    sql_fim.append(f'''SELECT {colunas['fim']}::text as ano FROM {tbl} WHERE "situação_atual" LIKE '%Conclu%' ''')
                if tbl:
                    sql_situacao.append(f'''SELECT "situação_atual" as sit FROM {tbl}''')

        elif fonte == 'novo':
            for item in tabelas_novo:
                tbl, _, mapa_cols = validar_colunas(cursor, item['nome'], 'novo')
                if tbl and mapa_cols.get('data_inicio'):
                    sql_inicio.append(f'''SELECT LEFT(CAST({mapa_cols['data_inicio']} AS TEXT), 4) as ano FROM {tbl}''')
                if tbl and mapa_cols.get('data_fim'):
                    sql_fim.append(f'''SELECT LEFT(CAST({mapa_cols['data_fim']} AS TEXT), 4) as ano FROM {tbl} WHERE {mapa_cols['situacao']} LIKE '%Conclu%' OR {mapa_cols['situacao']} LIKE '%Finaliza%' ''')
                if tbl:
                    sql_situacao.append(f'''SELECT {mapa_cols['situacao']} as sit FROM {tbl}''')
                
                if tbl and mapa_cols.get('data_fim'):
                    obj_padrao = "'Sem Objeto'"
                    cid_padrao = "'Sem Cidade'"
                    val_padrao = "0"
                    sql_atraso.append(f'''SELECT {mapa_cols['id']}::text as id, {mapa_cols.get('objeto', obj_padrao)} as objeto, {mapa_cols.get('cidade', cid_padrao)} as cidade, {mapa_cols.get('valor', val_padrao)} as valor, {mapa_cols['data_fim']}::text as data_fim, {mapa_cols['situacao']}::text as situacao FROM {tbl} WHERE {mapa_cols['data_fim']} IS NOT NULL''')
        
        if sql_inicio:
            query_completa = " UNION ALL ".join(sql_inicio)
            cursor.execute(f"SELECT ano, COUNT(*) as qtd FROM ({query_completa}) as t WHERE ano IS NOT NULL GROUP BY ano ORDER BY ano")
            resultados = cursor.fetchall()
            resp["anos_inicio"] = [r for r in resultados if r['ano'] and r['ano'].isdigit() and 1990 < int(r['ano']) < 2035]

        if sql_fim:
            query_completa = " UNION ALL ".join(sql_fim)
            cursor.execute(f"SELECT ano, COUNT(*) as qtd FROM ({query_completa}) as t WHERE ano IS NOT NULL GROUP BY ano ORDER BY ano")
            resultados = cursor.fetchall()
            resp["anos_fim"] = [r for r in resultados if r['ano'] and r['ano'].isdigit() and 1990 < int(r['ano']) < 2035]
        
        if sql_situacao:
            query_completa = " UNION ALL ".join(sql_situacao)
            cursor.execute(f"SELECT sit, COUNT(*) as qtd FROM ({query_completa}) as t GROUP BY sit ORDER BY qtd DESC")
            resp["situacao"] = cursor.fetchall()

        if sql_atraso:
            query_atrasos = " UNION ALL ".join(sql_atraso)
            cursor.execute(query_atrasos)
            resultados_atraso = cursor.fetchall()
            
            contadores = {
                'Atrasadas': {'label': 'Atrasadas', 'qtd': 0, 'obras': []},
                'No Prazo': {'label': 'No Prazo', 'qtd': 0, 'obras': []},
                'Concluídas': {'label': 'Concluídas', 'qtd': 0, 'obras': []}
            }
            
            hoje = date.today()
            
            for r in resultados_atraso:
                sit = str(r['situacao'] or '').lower()
                dt_str = str(r['data_fim'] or '').strip()
                
                obra_dict = {'id': r['id'], 'objeto': r['objeto'], 'cidade': r['cidade'], 'situacao': r['situacao'], 'valor': r['valor'], 'data_fim': dt_str}
                
                if 'conclu' in sit or 'finaliza' in sit:
                    contadores['Concluídas']['qtd'] += 1
                    if len(contadores['Concluídas']['obras']) < 300: contadores['Concluídas']['obras'].append(obra_dict)
                elif 'execu' in sit or 'andamento' in sit:
                    try:
                        dt_obj = None
                        if '/' in dt_str: 
                            p = dt_str.split(' ')[0].split('/')
                            if len(p) == 3: dt_obj = date(int(p[2]), int(p[1]), int(p[0]))
                        elif '-' in dt_str: 
                            p = dt_str.split(' ')[0].split('-')
                            if len(p) == 3: dt_obj = date(int(p[0]), int(p[1]), int(p[2]))
                        
                        if dt_obj:
                            if dt_obj < hoje: 
                                contadores['Atrasadas']['qtd'] += 1
                                if len(contadores['Atrasadas']['obras']) < 300: contadores['Atrasadas']['obras'].append(obra_dict)
                            else: 
                                contadores['No Prazo']['qtd'] += 1
                                if len(contadores['No Prazo']['obras']) < 300: contadores['No Prazo']['obras'].append(obra_dict)
                    except: pass
            
            resp["atraso"] = [v for k, v in contadores.items() if v['qtd'] > 0]

    except Exception: 
        traceback.print_exc()
    finally: 
        cursor.close()
        conexao.close()
        
    return jsonify(resp)

# 3. API FINANCEIRO
@app.route('/api/financeiro')
def obter_dados_financeiros():
    fonte = request.args.get('source', 'legado').strip()
    uf = request.args.get('uf', '').strip()
    cidade = request.args.get('city', '').strip()
    
    conexao = obter_conexao_db()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    resp = {"uf": [], "cidade": [], "orgao": [], "works": []}
    
    consultas = []
    limite_sql = " LIMIT 300" if cidade else ""

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
            
            filtrar_uf = base_completa
            if uf: filtrar_uf = f"SELECT * FROM ({base_completa}) as t WHERE UPPER(TRIM(uf)) = '{uf.upper()}'"
            
            filtrar_cidade = filtrar_uf
            if cidade: 
                cidade_segura = cidade.replace("'", "''")
                filtrar_cidade = f"SELECT * FROM ({filtrar_uf}) as t WHERE cidade = '{cidade_segura}'"

            if not uf:
                cursor.execute(f"SELECT uf as label, SUM(valor) as valor FROM ({base_completa}) as t GROUP BY uf ORDER BY valor DESC")
                resp["uf"] = cursor.fetchall()
            
            if uf:
                cursor.execute(f"SELECT cidade as label, SUM(valor) as valor FROM ({filtrar_uf}) as t WHERE cidade IS NOT NULL GROUP BY cidade ORDER BY valor DESC LIMIT 20")
                resp["cidade"] = cursor.fetchall()

            cursor.execute(f"SELECT orgao as label, SUM(valor) as valor FROM ({filtrar_cidade}) as t WHERE orgao IS NOT NULL GROUP BY orgao ORDER BY valor DESC LIMIT 10")
            resp["orgao"] = cursor.fetchall()

            if cidade:
                cursor.execute(f"SELECT id, objeto, situacao, valor, origem, cidade FROM ({filtrar_cidade}) as t ORDER BY valor DESC {limite_sql}")
                resp["works"] = cursor.fetchall()

    except Exception: 
        traceback.print_exc()
    finally: 
        cursor.close()
        conexao.close()
        
    return jsonify(resp)

# 4. API SITUAÇÃO
@app.route('/api/situacao')
def obter_dados_situacao():
    fonte = request.args.get('source', 'legado').strip()
    uf_param = request.args.get('uf', '').strip().upper()
    conexao = obter_conexao_db()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    
    nivel_str = "city" if uf_param else "uf"
    resp = {"status": [], "execucao": [], "works": [], "level": nivel_str}
    sql_status = []
    sql_execucao = []
    sql_obras = []

    try:
        tabelas_legado, tabelas_novo = descobrir_tabelas(cursor)
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
                            sql_execucao.append(f'''SELECT UPPER(TRIM(uf)) as label, {colunas['fisico']}::text as perc_bruto FROM {tbl} WHERE {colunas['fisico']} IS NOT NULL''')
                        else:
                            col_municipio_seguro = col_municipio if col_municipio else "'Sem Município'"
                            sql_obras.append(f'''SELECT id_obra::text as id, COALESCE(objeto, 'Sem Objeto') as objeto, COALESCE({col_municipio_seguro}, 'Sem Município') as cidade_json, COALESCE("situação_atual", 'Não Informado') as situacao, 'Não Informado' as especie, {colunas['fisico']}::text as perc_bruto FROM {tbl} WHERE UPPER(TRIM(uf)) = '{uf_param}' AND {colunas['fisico']} IS NOT NULL''')

        elif fonte == 'novo':
            ufs_processadas = set()

            for item in tabelas_novo:
                if uf_param and item['uf'] != uf_param: continue
                tbl, _, mapa_cols = validar_colunas(cursor, item['nome'], 'novo')
                if tbl:
                    sql_status.append(f'''SELECT {mapa_cols['situacao']} as label, COUNT(*) as qtd FROM {tbl} GROUP BY 1''')

            for tab in todas_tabelas:
                if tab.startswith('api_projeto_investimento_'):
                    uf_tab = tab.replace('api_projeto_investimento_', '').upper()
                    if uf_param and uf_tab != uf_param: continue
                    
                    tab_fis = f"api_execucao_fisica_{uf_tab.lower()}"
                    
                    if tab_fis in todas_tabelas:
                        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tab}'")
                        colunas_proj = [r['column_name'].lower() for r in cursor.fetchall()]
                        
                        col_nome = "nome" if "nome" in colunas_proj else ("descricao" if "descricao" in colunas_proj else "'Sem Objeto'")
                        col_especie = "especie" if "especie" in colunas_proj else ("natureza" if "natureza" in colunas_proj else "'Não Informado'")
                        col_cidade = "executores" if "executores" in colunas_proj else "'Sem Cidade'"
                        col_sit = "situacao" if "situacao" in colunas_proj else "'Não Informado'"
                        col_id = "id_unico" if "id_unico" in colunas_proj else "id_unico_api"

                        ufs_processadas.add(uf_tab)

                        if not uf_param:
                            sql_execucao.append(f'''SELECT '{uf_tab}' as label, f.percentual::text as perc_bruto FROM {tab} p JOIN {tab_fis} f ON p.{col_id}::text = f.id_unico::text''')
                        else:
                            sql_obras.append(f'''SELECT p.{col_id}::text as id, COALESCE(p.{col_nome}, 'Sem Objeto') as objeto, p.{col_cidade}::text as cidade_json, COALESCE(p.{col_sit}, 'Não Informado') as situacao, COALESCE(p.{col_especie}, 'Não Informado') as especie, f.percentual::text as perc_bruto FROM {tab} p JOIN {tab_fis} f ON p.{col_id}::text = f.id_unico::text WHERE f.percentual IS NOT NULL''')

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

        if sql_status:
            query_status = " UNION ALL ".join(sql_status)
            cursor.execute(f"SELECT label, SUM(qtd) as qtd FROM ({query_status}) as t GROUP BY label ORDER BY qtd DESC")
            resp["status"] = cursor.fetchall()

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
                
            lista_medias = [{'label': k, 'fisico': round(v['soma'] / v['qtd'], 1)} for k, v in totais_fisico.items() if v['qtd'] > 0]
            resp["execucao"] = sorted(lista_medias, key=lambda x: x['fisico'], reverse=True)

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
            resp["works"] = sorted(lista_obras, key=lambda x: x['fisico'], reverse=True)[:300]

    except Exception as e:
        traceback.print_exc()
    finally:
        cursor.close()
        conexao.close()
        
    return jsonify(resp)

# 5. API CLASSIFICAÇÃO
@app.route('/api/classificacao')
def obter_dados_classificacao():
    fonte = request.args.get('source', 'legado')
    conexao = obter_conexao_db()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    resp = {"natureza": [], "funcao": []}
    sql_natureza = []
    sql_funcao = []

    try:
        tabelas_legado, tabelas_novo = descobrir_tabelas(cursor)
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
                    sql_natureza.append(f'''SELECT {mapa_cols['natureza']} as label, COUNT(*) as qtd FROM {tbl} GROUP BY 1''')
                    sql_funcao.append(f'''SELECT {mapa_cols['funcao']} as label, COUNT(*) as qtd FROM {tbl} GROUP BY 1''')

        if sql_natureza:
            query_completa = " UNION ALL ".join(sql_natureza)
            cursor.execute(f"SELECT UPPER(TRIM(label::text)) as label, SUM(qtd) as qtd FROM ({query_completa}) as t WHERE label IS NOT NULL GROUP BY UPPER(TRIM(label::text)) ORDER BY qtd DESC")
            resp["natureza"] = cursor.fetchall()
            
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
    return render_template('obra.html', id_obra=id_obra)

@app.route('/api/obra/<id_obra>')
def detalhar_obra_api(id_obra):
    conexao = obter_conexao_db()
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    
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
    
    def conversor_float_seguro(v):
        if v is None: return 0.0
        if isinstance(v, (int, float)):
            if math.isnan(v): return 0.0
            return float(v)
            
        v_str = str(v).strip()
        if not v_str: return 0.0
        
        v_str = re.sub(r'[^0-9.,-]', '', v_str)
        if not v_str: return 0.0
        
        virgulas = v_str.count(',')
        pontos = v_str.count('.')
        
        if virgulas == 1 and pontos >= 1:
            v_str = v_str.replace('.', '').replace(',', '.')
        elif virgulas == 1 and pontos == 0:
            v_str = v_str.replace(',', '.')
        elif pontos >= 1 and virgulas == 0:
            parte = v_str.rsplit('.', 1)
            if len(parte[1]) != 2:
                v_str = v_str.replace('.', '')
                
        try:
            val = float(v_str)
            if math.isnan(val): return 0.0
            return val
        except Exception:
            return 0.0

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

        if dados_da_obra:
            resp["encontrado"] = True
            
            nome_val = str(obter_chave_flexivel(dados_da_obra, 'nome__apelido_', 'nome', 'título', 'descricao', 'objeto') or 'Não Informado')
            uf_obra = str(obter_chave_flexivel(dados_da_obra, 'uf', 'uf_localização') or origem_tabela.get('uf', 'br')).lower().strip()
            
            cidade_val = str(obter_chave_flexivel(dados_da_obra, 'município', 'municipio', 'executor_da_obra') or 'Não Informada')
            executores = obter_chave_flexivel(dados_da_obra, 'executores')
            if executores:
                cidade_bruta = str(executores)
                match = re.search(r"['\"]nome['\"]\s*:\s*['\"]([^'\"]+)['\"]", cidade_bruta)
                if match: cidade_val = match.group(1)

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

            val_total = conversor_float_seguro(obter_chave_flexivel(dados_da_obra, 'investimento_previsto', 'meta_global', 'investimento_total'))
            
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

            # ===================================================================================
            # SALDOS CONTÁBEIS: Nova lógica pegando apenas a última linha válida (sem somar)
            # ===================================================================================
            val_pago_final = conversor_float_seguro(obter_chave_flexivel(dados_da_obra, 'valor_empenhado'))
            val_restos_final = conversor_float_seguro(obter_chave_flexivel(dados_da_obra, 'valor_desembolsado', 'valor_repasse'))

            if origem_tabela.get('tipo') != 'legado' and uf_obra != 'br':
                tab_fin = f"api_execucao_financeira_{uf_obra}"
                tab_saldo = f"api_saldo_contabil_{uf_obra}"
                ugs = []
                
                if tab_fin in todas_tabelas:
                    try:
                        cursor.execute(f"SELECT * FROM {tab_fin} WHERE id_unico::text = %s", (id_obra,))
                        for r in cursor.fetchall():
                            if r.get('ug_emitente'): ugs.append(str(r['ug_emitente']).strip())
                            if r.get('ug_emitente1'): ugs.append(str(r['ug_emitente1']).strip())
                    except Exception as e:
                        conexao.rollback()
                        print("Erro Busca UG:", e)
                
                if ugs and tab_saldo in todas_tabelas:
                    ugs_unicas = list(set(ugs))
                    ugs_str = "','".join(ugs_unicas)
                    try:
                        cursor.execute(f"SELECT * FROM {tab_saldo} WHERE ug_emitente_filtro::text IN ('{ugs_str}')")
                        linhas_saldo = cursor.fetchall()
                        
                        if linhas_saldo:
                            for rs in reversed(linhas_saldo):
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
                                    
                    except Exception as e:
                        conexao.rollback()
                        print("Erro Saldo Contabil:", e)

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
                        pass
            
            if perc_fisico == 0.0:
                perc_fisico = conversor_float_seguro(obter_chave_flexivel(dados_da_obra, 'percentual_execucao', 'percentual_fisico', 'execução física'))

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

            modalidade = obter_chave_flexivel(dados_da_obra, 'modalidade', 'tipo_de_instrumento') or ('Transferência Fundo a Fundo' if 'fundo' in nome_val.lower() else "Convênio / Contrato de Repasse")
            fornecedor = str(obter_chave_flexivel(dados_da_obra, 'cnpj_executor') or 'Não Informado')

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
                        pass

            resp["investimento"] = {
                "fonte": str(obter_chave_flexivel(dados_da_obra, 'fontes_de_recurso') or 'Orçamento Geral da União'),
                "modalidade": str(modalidade),
                "contrato_fornecedor": fornecedor,
                "contrato_vigencia": f"{dt_inicio} a {dt_fim}"
            }

            funcao = obter_chave_flexivel(dados_da_obra, 'funcao_social', 'função_social', 'tipo') or 'Não Mapeada'
            empregos = obter_chave_flexivel(dados_da_obra, 'qdt_empregos_gerados', 'empregos_gerados') or 'Não Informado'
            publico = obter_chave_flexivel(dados_da_obra, 'populacao_beneficiada', 'desc_populacao_beneficiada') or 'Estimativa indisponível'

            resp["impacto"] = {
                "funcao": str(funcao),
                "publico_beneficiado": str(publico),
                "empregos": str(empregos)
            }

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
                except Exception as epad:
                    conexao.rollback()
                    print("Erro ao ler PAD:", epad)

            # CÁLCULO DE PORCENTAGEM USANDO O VALOR PAGO VS PREVISTO
            perc_finan = (val_pago_final / val_total * 100) if val_total > 0 else 0
            
            resp["execucao"]["perc_fisico"] = perc_fisico
            resp["execucao"]["perc_financeiro"] = round(perc_finan, 1)
            resp["execucao"]["valor_previsto"] = val_total
            resp["execucao"]["valor_empenhado"] = val_pago_final
            resp["execucao"]["valor_desembolsado"] = val_restos_final

    except Exception as e:
        print("Erro Detalhe Obra:", e)
        traceback.print_exc()
    finally:
        cursor.close()
        conexao.close()
        
    return jsonify(resp)

if __name__ == '__main__':
    app.run(debug=True)