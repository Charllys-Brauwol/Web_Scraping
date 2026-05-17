# ==============================================================================
# --- 1. IMPORTAÇÕES ---
# Ferramentas para e-mail, Telegram, threads (tarefas simultâneas) e criação do site.
# ==============================================================================
import os  # Para caminhos no Windows
import smtplib  # Para envio de e-mails usando o protocolo SMTP
import requests  # Para fazer requisições web (usado aqui para falar com a API do Telegram)
import time  # Para pausas no código
import threading  # A MÁGICA: Permite rodar o site e o cão de guarda ao mesmo tempo, sem um travar o outro!
import html  # Para "higienizar" o texto dos erros (evita que o Telegram confunda '<' com código e trave)
from datetime import datetime, timedelta  # Para trabalhar com datas e medir o tempo
from email.mime.text import MIMEText  # Para montar o corpo do e-mail
from email.mime.multipart import MIMEMultipart  # Para e-mails complexos (com HTML)
from flask import Flask, render_template, request, redirect, url_for  # O framework que cria o site (Dashboard)
from sqlalchemy import create_engine, inspect, text  # O motor do banco de dados

# ==============================================================================
# --- 1. CONFIGURAÇÃO DE DIRETÓRIOS E FLASK ---
# ==============================================================================
# Descobre a pasta exata onde este arquivo Python está salvo no seu computador
diretorio_base = os.path.abspath(os.path.dirname(__file__))

# Instancia o servidor web Flask. Diz para ele procurar as páginas HTML (templates) na mesma pasta do script
app = Flask(__name__, 
            template_folder=diretorio_base, 
            static_folder=diretorio_base)

# ==============================================================================
# --- 2. CONFIGURAÇÕES DE BANCO DE DADOS ---
# O Dashboard precisa acessar o mesmo banco que os robôs alimentam
# ==============================================================================
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "cb2907cb"
DB_PORT = "5432"
TARGET_DB_NAME = "minhas_obras"

# Cria a string de conexão e o motor do SQLAlchemy que o Flask vai usar para ler os logs
DB_URI = f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}'
engine = create_engine(DB_URI)

# ==============================================================================
# --- 3. CONFIGURAÇÕES DE NOTIFICAÇÃO ---
# Credenciais para os alertas dispararem
# ==============================================================================
EMAIL_SENDER = 'botminhasobras@gmail.com' # Conta do bot que vai enviar o e-mail
EMAIL_PASSWORD = 'xqww aqmf vjmr svab' # Senha de aplicativo gerada no Google (nunca use a senha real da conta!)
EMAIL_RECEIVER = 'botminhasobras@gmail.com' # Para quem o alerta vai (você)
SMTP_SERVER = 'smtp.gmail.com' # Servidor de disparo do Google
SMTP_PORT = 587 # Porta de segurança TLS

TELEGRAM_TOKEN = '8540221492:AAEqj8dkKivvBzLHEoT548h-BQZiR_SOafk' # A "chave" do seu bot criado no BotFather
TELEGRAM_CHAT_ID = '929373299' # A "identidade" do seu WhatsApp/Telegram pessoal para o bot saber para quem mandar

# Ponto de Partida do Cão de Guarda: Começa a vigiar os erros a partir do EXATO SEGUNDO que você roda esse script.
# Isso impede que ele te mande mensagens de erros que aconteceram ontem.
ULTIMO_CHECK = datetime.now()

# ==============================================================================
# --- 4. FUNÇÕES DE NOTIFICAÇÃO (TELEGRAM E EMAIL) ---
# ==============================================================================
def enviar_telegram(mensagem):
    """Bate na porta da API do Telegram e entrega a mensagem formatada para você."""
    try:
        # A URL oficial do Telegram para mandar mensagens
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        # O pacote de informações que vamos enviar
        carga = {
            "chat_id": TELEGRAM_CHAT_ID, # Pra quem é
            "text": mensagem, # O que é
            "modo": "HTML" # Diz pro Telegram aceitar negrito <b>, quebras de linha, etc
        }
        # Dispara o pacote
        response = requests.post(url, data=carga)
        
        if not response.ok: # Se o Telegram recusar (Ex: texto longo demais, tags HTML abertas)
            print(f"[Monitor] ❌ Erro Telegram: {response.status_code} - {response.text}")
        else:
            print(f"[Monitor] ✅ Telegram enviado com sucesso!")
        return response.ok
    except Exception as e: # Se a internet do servidor cair
        print(f"[Monitor] ❌ Erro ao enviar Telegram: {e}")
        return False

def enviar_email(assunto, corpo_html):
    """Monta uma carta eletrônica bonita com HTML e despacha pelo servidor do Gmail."""
    try:
        msg = MIMEMultipart() # Cria o "envelope" do e-mail
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = assunto

        # Coloca a mensagem HTML dentro do envelope
        msg.attach(MIMEText(corpo_html, 'html'))

        # Abre comunicação com o correio (servidor SMTP do Gmail)
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls() # Criptografa a conexão (segurança)
            server.login(EMAIL_SENDER, EMAIL_PASSWORD) # Faz o login do robô
            server.send_message(msg) # Dispara o e-mail
            
        print(f"[Monitor] ✅ E-mail enviado com sucesso!")
        return True
    except Exception as e:
        print(f"[Monitor] ❌ Erro ao enviar E-mail: {e}")
        return False

# ==============================================================================
# --- 5. LÓGICA DE MONITORAMENTO EM TEMPO REAL (O CÃO DE GUARDA) ---
# ==============================================================================
def checar_novos_erros():
    """Essa função é o "Cão de Guarda". Ela roda em loop infinito numa via separada do site."""
    global ULTIMO_CHECK # Chama a variável de controle de tempo lá de cima
    
    print(f"[Monitor] Iniciando vigília... (Buscando erros após {ULTIMO_CHECK.strftime('%H:%M:%S')})")
    
    while True: # Loop infinito da vigília
        try:
            # O cão dorme por 60 segundos. (Checa o banco de 1 em 1 minuto para não fritar o computador)
            time.sleep(60)
            
            # Abre uma linha direta com o banco de dados
            with engine.connect() as conn:
                inspector = inspect(engine)
                # Verifica todas as tabelas do banco que comecem com "logs_"
                tabelas_logs = [t for t in inspector.get_table_names() if t.startswith('logs_')]
                
                erros_novos = [] # Caixinha pra acumular os erros deste minuto
                agora = datetime.now() # Marca o momento atual
                
                for tabela in tabelas_logs: # Para cada tabela de log no banco
                    # Manda um comando SQL que diz: "Me traga erros (ERROR) que nasceram DEPOIS do último check"
                    sql = text(f"""
                        SELECT arquivo_origem, mensagem, data_hora 
                        FROM {tabela} 
                        WHERE nivel = 'ERROR' AND data_hora > :ultimo_check
                    """)
                    
                    # Executa a busca enviando a hora do último check para o banco de dados
                    result = conn.execute(sql, {'ultimo_check': ULTIMO_CHECK}).mappings().all()
                    
                    if result: # Se ele achou erros novos
                        erros_novos.append({
                            'sistema': formatar_nome_sistema(tabela), # Pega o nome do sistema limpo (Ex: Site Legado)
                            'logs': result # Pega a lista dos erros
                        })
                
                # Se após olhar todas as tabelas, houverem erros na caixinha...
                if erros_novos:
                    print(f"[Monitor] 🚨 {len(erros_novos)} sistemas apresentaram novos erros!")
                    # Aciona a sirene de alerta (Manda para a função que formata e dispara as msgs)
                    processar_alertas(erros_novos)
                
                # O mais importante: Atualiza o ponteiro de tempo!
                # Da próxima vez que o cão de guarda acordar (daqui 1 min), ele só vai olhar as coisas DEPOIS de 'agora'
                ULTIMO_CHECK = agora
                
        except Exception as e:
            print(f"[Monitor] Erro no loop de monitoramento: {e}")
            # Se o banco de dados cair, o cão de guarda não morre, ele dorme 10s e tenta de novo
            time.sleep(10)

def processar_alertas(erros_encontrados):
    """Pega os dados brutos de erro e transforma numa mensagem amigável para enviar."""
    
    # --- Monta o texto para o Telegram ---
    msg_telegram = f"<b>🚨 ALERTA DE ERRO EM TEMPO REAL</b>\n\n"
    for item in erros_encontrados:
        msg_telegram += f"<b>📂 {item['sistema']}</b>\n" # Nome do sistema em negrito
        
        for erro in item['logs']:
            texto_erro = erro['mensagem']
            
            # Se o erro for uma "bíblia" de código, corta em 1000 caracteres para o Telegram não rejeitar
            if len(texto_erro) > 1000:
                texto_erro = texto_erro[:1000] + '... (ver log completo no site)'
            
            # HIGIENIZAÇÃO: Transforma símbolos como "<" em códigos seguros "&lt;" para o Telegram não interpretar como Tag HTML errada
            texto_seguro = html.escape(texto_erro)
            
            # Monta a linha com o reloginho, a hora e o erro
            msg_telegram += f"└ ⏰ {erro['data_hora'].strftime('%H:%M:%S')} - {texto_seguro}\n"
        msg_telegram += "\n" # Espaço vazio entre sistemas
    
    enviar_telegram(msg_telegram) # Manda pro celular
    
    # --- Monta o texto para o E-mail (com código HTML) ---
    html_email = "<h2>🚨 Novos Erros Detectados</h2><hr>"
    count = 0
    for item in erros_encontrados:
        html_email += f"<h3>📂 {item['sistema']}</h3><ul>" # Começa uma lista de tópicos (bullets)
        for erro in item['logs']:
            count += 1
            msg_segura = html.escape(erro['mensagem'])
            html_email += f"<li><b>{erro['data_hora'].strftime('%H:%M:%S')}</b>: {msg_segura}</li>" # <li> é a "bolinha" da lista
        html_email += "</ul>"
    
    enviar_email(f"Alerta: {count} Novos Erros Detectados", html_email) # Dispara o e-mail

# ==============================================================================
# --- 6. FUNÇÕES AUXILIARES PARA O SITE (FLASK) ---
# ==============================================================================
def formatar_nome_sistema(nome_tabela):
    """Pega o nome técnico 'logs_site_legado' e deixa bonito 'Site Legado' para aparecer no site."""
    nome = nome_tabela.replace('logs_', '')
    return nome.replace('_', ' ').title()

# Injeta essa função formatadora dentro de todas as páginas HTML do seu site
@app.context_processor
def utility_processor():
    return dict(formatar_nome=formatar_nome_sistema)

# ==============================================================================
# --- 7. ROTAS DO SITE (O DASHBOARD) ---
# ==============================================================================
@app.route('/') # Rota principal (quando você digita só localhost:5000)
def index():
    try:
        inspector = inspect(engine)
        tabelas_logs = [t for t in inspector.get_table_names() if t.startswith('logs_')]
        
        resumo = []
        with engine.connect() as conn:
            for tabela in tabelas_logs:
                # Conta quantos erros ocorreram na data de HOJE para mostrar no painel principal
                sql = text(f"SELECT COUNT(*) FROM {tabela} WHERE nivel = 'ERROR' AND data_hora::date = CURRENT_DATE")
                count = conn.execute(sql).scalar() # scalar() pega apenas o número exato do resultado
                
                resumo.append({
                    'tabela': tabela,
                    'nome_exibicao': formatar_nome_sistema(tabela),
                    'erros_hoje': count
                })
        
        # Manda as informações resumidas para a tela HTML desenhar o gráfico/painel
        return render_template('index.html', sistemas=resumo)
    except Exception as e:
        return f"<h1>Erro ao conectar no Banco de Dados</h1><p>{str(e)}</p>"

@app.route('/logs/<nome_tabela>') # Rota detalhada (Ex: localhost:5000/logs/logs_site_legado)
def ver_logs(nome_tabela):
    """Carrega os últimos 200 logs de um sistema específico para você ler na tela."""
    if not nome_tabela.startswith('logs_'): # Segurança: Impede acesso a tabelas que não são de log
        return redirect(url_for('index'))
    
    filtro_nivel = request.args.get('nivel') # Pega a informação da barra de busca se você usou o filtro do site
    query = f"SELECT * FROM {nome_tabela} WHERE 1=1" # 1=1 é um truque pra facilitar adicionar 'AND' depois
    params = {}
    
    if filtro_nivel and filtro_nivel != 'TODOS':
        query += " AND nivel = :nivel" # Filtra só ERROR ou só INFO, dependendo do que você clicou no site
        params['nivel'] = filtro_nivel
        
    query += " ORDER BY data_hora DESC LIMIT 200" # Puxa do mais novo para o mais velho (DESC) limitado a 200 pra não travar a página
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            logs = result.mappings().all() # Pega o resultado da busca
            
        # Pega as informações de erro e entrega pro site desenhar a tabela
        return render_template('logs.html', 
                               logs=logs, 
                               tabela=nome_tabela, 
                               filtro_atual=filtro_nivel)
    except Exception as e:
        return f"<h1>Erro ao ler logs</h1><p>{str(e)}</p>"

@app.route('/relatorio') # Rota de teste/antiga
def enviar_relatorio_dia():
    return "O monitoramento agora é automático em tempo real! Verifique o console."

# ==============================================================================
# --- O GRANDE GATILHO ---
# ==============================================================================
if __name__ == '__main__':
    # 1. Cria a linha de execução paralela (Thread) pro cão de guarda
    # daemon=True: Se você parar o site, o cão de guarda morre junto e não fica consumindo RAM escondido
    monitor_thread = threading.Thread(target=checar_novos_erros, daemon=True)
    
    # 2. Solta o cão de guarda!
    monitor_thread.start()
    
    # Textos de status
    print(f"--> Servidor rodando na pasta: {diretorio_base}")
    print("--> Monitoramento em Tempo Real: ATIVO")
    print("--> Acesse: http://127.0.0.1:5000")
    
    # 3. Liga o Servidor Web (o Site)
    # use_reloader=False: Evita um bug famoso do Flask que reinicia o código duas vezes e acabaria rodando DOIS cães de guarda.
    app.run(debug=True, use_reloader=False)