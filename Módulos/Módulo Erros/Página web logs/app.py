import os
import smtplib
import requests
import time
import threading
import html  # <--- Importante para corrigir o erro do Telegram
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine, inspect, text

# --- 1. CONFIGURAÇÃO DE DIRETÓRIOS ---
diretorio_base = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, 
            template_folder=diretorio_base, 
            static_folder=diretorio_base)

# --- 2. CONFIGURAÇÕES DE BANCO DE DADOS ---
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb"
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras"

DB_URI = f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}'
engine = create_engine(DB_URI)

# --- 3. CONFIGURAÇÕES DE NOTIFICAÇÃO (PREENCHA AQUI) ---
EMAIL_SENDER = 'botminhasobras@gmail.com'
EMAIL_PASSWORD = 'xqww aqmf vjmr svab'
EMAIL_RECEIVER = 'botminhasobras@gmail.com' # Pode ser o mesmo do remetente
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

TELEGRAM_TOKEN = '8540221492:AAEqj8dkKivvBzLHEoT548h-BQZiR_SOafk'
# IMPORTANTE: O Chat ID NÃO é o mesmo número do início do token.
# Siga as instruções para pegar seu ID pessoal ou do grupo.
TELEGRAM_CHAT_ID = '929373299' 

# Variável global para controlar o último momento checado
# Ao iniciar, define como "agora" para não alertar erros antigos, apenas novos.
ULTIMO_CHECK = datetime.now()

# --- 4. FUNÇÕES DE NOTIFICAÇÃO ---
def enviar_telegram(mensagem):
    """Envia mensagem para o bot do Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        carga = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensagem,
            "modo": "HTML"
        }
        response = requests.post(url, data=carga)
        if not response.ok:
            print(f"[Monitor] ❌ Erro Telegram: {response.status_code} - {response.text}")
        else:
            print(f"[Monitor] ✅ Telegram enviado com sucesso!")
        return response.ok
    except Exception as e:
        print(f"[Monitor] ❌ Erro ao enviar Telegram: {e}")
        return False

def enviar_email(assunto, corpo_html):
    """Envia e-mail com suporte a HTML."""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = assunto

        msg.attach(MIMEText(corpo_html, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"[Monitor] ✅ E-mail enviado com sucesso!")
        return True
    except Exception as e:
        print(f"[Monitor] ❌ Erro ao enviar E-mail: {e}")
        return False

# --- 5. LÓGICA DE MONITORAMENTO EM TEMPO REAL ---
def checar_novos_erros():
    """Função que roda em loop checando o banco."""
    global ULTIMO_CHECK
    
    print(f"[Monitor] Iniciando vigília... (Buscando erros após {ULTIMO_CHECK.strftime('%H:%M:%S')})")
    
    while True:
        try:
            # Intervalo de checagem (60 segundos)
            time.sleep(60)
            
            # Cria uma nova conexão dedicada para a thread
            with engine.connect() as conn:
                inspector = inspect(engine)
                # Pega tabelas atualizadas a cada loop (caso surja um sistema novo)
                tabelas_logs = [t for t in inspector.get_table_names() if t.startswith('logs_')]
                
                erros_novos = []
                agora = datetime.now()
                
                for tabela in tabelas_logs:
                    # Busca erros que ocorreram DEPOIS do último check
                    sql = text(f"""
                        SELECT arquivo_origem, mensagem, data_hora 
                        FROM {tabela} 
                        WHERE nivel = 'ERROR' AND data_hora > :ultimo_check
                    """)
                    
                    result = conn.execute(sql, {'ultimo_check': ULTIMO_CHECK}).mappings().all()
                    
                    if result:
                        erros_novos.append({
                            'sistema': formatar_nome_sistema(tabela),
                            'logs': result
                        })
                
                # Se achou erros novos, dispara alertas
                if erros_novos:
                    print(f"[Monitor] 🚨 {len(erros_novos)} sistemas apresentaram novos erros!")
                    processar_alertas(erros_novos)
                
                # Atualiza o "ponteiro" de tempo para agora
                ULTIMO_CHECK = agora
                
        except Exception as e:
            print(f"[Monitor] Erro no loop de monitoramento: {e}")
            # Espera um pouco antes de tentar de novo para não travar CPU em caso de erro de conexão
            time.sleep(10)

def processar_alertas(erros_encontrados):
    """Formata e envia os alertas."""
    
    # --- Telegram ---
    msg_telegram = f"<b>🚨 ALERTA DE ERRO EM TEMPO REAL</b>\n\n"
    for item in erros_encontrados:
        msg_telegram += f"<b>📂 {item['sistema']}</b>\n"
        for erro in item['logs']:
            # Escapa caracteres HTML para não quebrar o envio do Telegram
            texto_erro = erro['mensagem']
            # AUMENTADO DE 100 PARA 1000 CARACTERES
            if len(texto_erro) > 1000:
                texto_erro = texto_erro[:1000] + '... (ver log completo no site)'
            
            # Sanitização crucial aqui:
            texto_seguro = html.escape(texto_erro)
            
            msg_telegram += f"└ ⏰ {erro['data_hora'].strftime('%H:%M:%S')} - {texto_seguro}\n"
        msg_telegram += "\n"
    
    enviar_telegram(msg_telegram)
    
    # --- E-mail ---
    html_email = "<h2>🚨 Novos Erros Detectados</h2><hr>"
    count = 0
    for item in erros_encontrados:
        html_email += f"<h3>📂 {item['sistema']}</h3><ul>"
        for erro in item['logs']:
            count += 1
            # Também escapamos no email por segurança, embora browsers lidem melhor
            msg_segura = html.escape(erro['mensagem'])
            html_email += f"<li><b>{erro['data_hora'].strftime('%H:%M:%S')}</b>: {msg_segura}</li>"
        html_email += "</ul>"
    
    enviar_email(f"Alerta: {count} Novos Erros Detectados", html_email)

# --- 6. FUNÇÕES AUXILIARES FLASK ---
def formatar_nome_sistema(nome_tabela):
    nome = nome_tabela.replace('logs_', '')
    return nome.replace('_', ' ').title()

@app.context_processor
def utility_processor():
    return dict(formatar_nome=formatar_nome_sistema)

# --- 7. ROTAS DO SITE ---
@app.route('/')
def index():
    try:
        inspector = inspect(engine)
        tabelas_logs = [t for t in inspector.get_table_names() if t.startswith('logs_')]
        
        resumo = []
        with engine.connect() as conn:
            for tabela in tabelas_logs:
                sql = text(f"SELECT COUNT(*) FROM {tabela} WHERE nivel = 'ERROR' AND data_hora::date = CURRENT_DATE")
                count = conn.execute(sql).scalar()
                
                resumo.append({
                    'tabela': tabela,
                    'nome_exibicao': formatar_nome_sistema(tabela),
                    'erros_hoje': count
                })
        
        return render_template('index.html', sistemas=resumo)
    except Exception as e:
        return f"<h1>Erro ao conectar no Banco de Dados</h1><p>{str(e)}</p>"

@app.route('/logs/<nome_tabela>')
def ver_logs(nome_tabela):
    if not nome_tabela.startswith('logs_'):
        return redirect(url_for('index'))
    
    filtro_nivel = request.args.get('nivel')
    query = f"SELECT * FROM {nome_tabela} WHERE 1=1"
    params = {}
    
    if filtro_nivel and filtro_nivel != 'TODOS':
        query += " AND nivel = :nivel"
        params['nivel'] = filtro_nivel
        
    query += " ORDER BY data_hora DESC LIMIT 200"
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            logs = result.mappings().all()
            
        return render_template('logs.html', 
                               logs=logs, 
                               tabela=nome_tabela, 
                               filtro_atual=filtro_nivel)
    except Exception as e:
        return f"<h1>Erro ao ler logs</h1><p>{str(e)}</p>"

# Rota manual continua existindo se quiser forçar o envio
@app.route('/relatorio')
def enviar_relatorio_dia():
    return "O monitoramento agora é automático em tempo real! Verifique o console."

if __name__ == '__main__':
    # INICIA A THREAD DE MONITORAMENTO
    # daemon=True significa que se você fechar o site, o monitor morre junto (não fica zumbi)
    monitor_thread = threading.Thread(target=checar_novos_erros, daemon=True)
    monitor_thread.start()
    
    print(f"--> Servidor rodando na pasta: {diretorio_base}")
    print("--> Monitoramento em Tempo Real: ATIVO")
    print("--> Acesse: http://127.0.0.1:5000")
    
    # use_reloader=False é importante quando se usa threads, senão ele roda a thread 2x
    app.run(debug=True, use_reloader=False)