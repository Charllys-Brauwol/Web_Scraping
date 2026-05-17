# ==============================================================================
# --- IMPORTAÇÕES ---
# Bibliotecas para banco de dados, requisições web e manipulação de tabelas.
# ==============================================================================
import psycopg2  # Adaptador para o Python conversar com o banco de dados PostgreSQL
import requests  # Para fazer as chamadas na API do governo
import pandas as pd  # Para manipular os dados em formato de tabela (DataFrames)
from sqlalchemy import create_engine  # Motor para conectar o Pandas diretamente ao banco de dados
from psycopg2 import OperationalError  # Para tratar erros específicos de conexão do banco
import time  # Para controlar pausas fixas no script
import sys  # Para comandos do sistema (como encerrar o programa bruscamente)
import random # Para gerar tempos de pausa aleatórios e enganar bloqueios de robôs

# ==============================================================================
# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# Dados de acesso ao seu servidor PostgreSQL local.
# ==============================================================================
DB_HOST = "localhost" # Informa que o servidor está rodando na sua própria máquina
DB_USER = "postgres" # Usuário administrador padrão do Postgres
DB_PASSWORD = "cb2907cb"  # Sua senha de acesso
DB_PORT = "5432" # Porta de comunicação padrão em que o Postgres roda
TARGET_DB_NAME = "minhas_obras" # Nome do banco de dados onde as tabelas serão lidas/salvas

# ==============================================================================
# --- CONFIGURAÇÕES DA API ---
# ==============================================================================
# Endereço direto da API pública do governo que devolve os dados financeiros
API_URL = "https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira"
# Cabeçalho da requisição avisando ao servidor que aceitamos qualquer formato de resposta (*/*)
API_HEADERS = {"accept": "*/*"}

# Lista completa com a sigla de todos os estados do Brasil que o loop vai percorrer
estados = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

# ==============================================================================
# --- FUNÇÃO: CONEXÃO COM O BANCO DE DADOS ---
# ==============================================================================
def conexaobd():
    """Cria e retorna o 'motor' de conexão entre o script Python e o PostgreSQL."""
    try:
        # Monta a string de conexão exata no formato que a biblioteca SQLAlchemy exige
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TARGET_DB_NAME}')
        print("Conexão com o banco de dados estabelecida com sucesso.")
        return engine # Retorna o motor pronto e conectado para o script usar
    except Exception as e: # Se a senha estiver errada, ou o banco estiver desligado...
        print(f"Erro ao conectar ao banco de dados '{TARGET_DB_NAME}': {e}")
        return None

# ==============================================================================
# --- FUNÇÃO: BUSCAR IDs DOS PROJETOS NO BANCO ---
# ==============================================================================
def obter_id_uf(engine, estado):
    """Vai na tabela do estado específico e pega a lista com todos os Identificadores Únicos."""
    # Monta o nome da tabela com base na sigla. Ex: se for 'SP', vira a string 'estados_sp'
    source_table_name = f'estados_{estado}'.lower()
    print(f"Buscando identificadores únicos na tabela '{source_table_name}'...")
    
    # Cria a instrução em linguagem SQL para selecionar apenas a coluna que nos importa
    query = f'SELECT "identificador_único" FROM {source_table_name}'
    
    try:
        # A mágica do Pandas: envia a query (SELECT) pro banco e já devolve a resposta formatada em tabela (DataFrame)
        df_ids = pd.read_sql(query, con=engine)
        print(f"Encontrados {len(df_ids)} identificadores para o estado de {estado}.")
        
        # Pega a coluna da tabela do Pandas e converte em uma lista simples do Python para o loop usar
        return df_ids['identificador_único'].tolist()
    except Exception as e: # Se a tabela daquele estado não existir no banco de dados...
        print(f"Erro ao consultar a tabela '{source_table_name}': {e}")
        return [] # Retorna uma lista vazia e a vida segue

# ==============================================================================
# --- FUNÇÃO: CONSULTAR A API DO GOVERNO ---
# ==============================================================================
def buscar_dados_financeiros(id_projeto):
    """Bate na porta da API do governo pedindo os detalhes financeiros de UM projeto específico."""
    todos_dados = [] # Caixinha vazia para guardar os resultados conforme as páginas forem lidas
    pag = 0 # Controle da página atual da API
    limpar_pid = str(id_projeto).strip() # Limpa o número do ID (remove espaços acidentais no começo ou fim)
    
    while True: # Loop infinito. Só vai parar quando as páginas da API acabarem (no comando 'break')
        # Parâmetros que são enviados embutidos na URL (Ex: ...?idProjetoInvestimento=123&pagina=0&tamanhoDaPagina=100)
        params = {
            "idProjetoInvestimento": limpar_pid,
            "pagina": pag,
            "tamanhoDaPagina": 100 # Pede até 100 registros de uma vez para não ter que trocar de página toda hora
        }
        try:
            # Dispara a requisição (tipo GET) para a API, esperando no máximo 30 segundos
            response = requests.get(API_URL, params=params, headers=API_HEADERS, timeout=30)
            
            # --- TRATAMENTO DE BLOQUEIO (RATE LIMIT) ---
            # O Erro 429 significa "Too Many Requests" (O governo percebeu que você está pedindo rápido demais)
            if response.status_code == 429:
                print(f"!!! ERRO 429 - LIMITE ATINGIDO para {limpar_pid}. Esperando 60 segundos...")
                time.sleep(60) # O robô dorme 1 minuto inteiro para o firewall do governo liberar seu IP de novo
                continue # O 'continue' ignora o resto do código abaixo e recomeça o loop 'while' da mesma página
            # -------------------------------------------

            response.raise_for_status() # Verifica se a API deu qualquer outro erro (404, 500) e "grita" se deu
            data = response.json() # Traduz o texto da resposta da web para um formato Dicionário do Python
            
            content = data.get("content", []) # Pega a chave "content" onde os dados estão. Se não existir, devolve vazio []
            if not content: # Se a lista de dados vier vazia, quer dizer que acabou.
                break # Quebra o loop infinito
            
            # Como a resposta da API não vem com o ID da obra colado nela, nós injetamos esse ID manualmente em cada linha
            for item in content:
                item['id_unico'] = limpar_pid
            
            todos_dados.extend(content) # Junta os dados dessa página com os dados das páginas anteriores
            
            if data.get("last", False): # A API do governo avisa se essa é a última ("last") página. Se for...
                break # ...Quebra o loop infinito
            
            pag += 1 # Soma 1 na contagem de páginas para o próximo ciclo do loop buscar a continuação
            time.sleep(random.uniform(1, 2)) # Pausa curta e aleatória entre as trocas de página

        except requests.exceptions.RequestException as e: # Se a internet cair ou o site travar geral
            print(f"AVISO: Erro na requisição para o ID {limpar_pid} (página {pag}): {e}")
            break # Desiste desse ID e quebra o loop
    
    return todos_dados # Devolve o pacote completo com todas as páginas daquele projeto

# ==============================================================================
# --- FUNÇÃO PRINCIPAL: ORQUESTRAÇÃO GERAL ---
# ==============================================================================
def processar_carregar_dados():
    """Função mestre que coordena tudo: conecta no banco, lê as listas, busca na web e devolve os dados pro banco."""
    engine = conexaobd() # Abre a conexão com o PostgreSQL
    if not engine: # Se falhou...
        sys.exit(1) # Encerra o programa

    # Uma lista fixa com os nomes exatos das colunas que a API deveria devolver
    nomes_colunas = [
        'id_unico', 'nomeEsferaOrcamentaria', 'nomeTipoEmpenho', 'fonteRecurso', 'naturezaDespesa',
        'numeroProcesso', 'descricaoEmpenho', 'planoInterno', 'resultadoPrimario',
        'tipoCredito', 'ugEmitente', 'codigoAmparoLegal', 'informacoesComplementares',
        'nomeFavorecido', 'unidadeOrcamentaria', 'ugResponsavel', 'planoOrcamentario',
        'autorEmenda', 'numeroNotaEmpenhoGerada', 'localEntrega', 'valorEmpenho',
        'nrPtres', 'idProjetoInvestimento'
    ]

    # Inicia a varredura Estado por Estado
    for estado in estados:
        print(f"\n--- Iniciando processamento para o estado: {estado} ---")
        
        ids_projetos = obter_id_uf(engine, estado) # Manda o banco de dados devolver os IDs do estado atual
        if not ids_projetos: # Se a tabela não tiver nada
            print(f"Nenhum ID de projeto encontrado para o estado {estado}. Pulando para o próximo.")
            continue # Pula pra próxima UF da lista
        
        estado_dados = [] # Bolsão vazio que vai acumular todos os dados financeiros desse estado inteiro
        
        # Loop secundário passando projeto por projeto (ID por ID)
        for pid in ids_projetos:
            
            limpar_pid = str(pid).strip() # Limpa a string do ID
            
            # Chama a nossa função que vai na web buscar o extrato desse ID
            dados_da_api = buscar_dados_financeiros(limpar_pid)
            
            if dados_da_api: # Se a API devolveu resultados...
                print(f"Dados encontrados para o projeto ID: {limpar_pid}. Total de registros: {len(dados_da_api)}")
                estado_dados.extend(dados_da_api) # ...guarda tudo no bolsão do estado
            else:
                # Se não vier ABSOLUTAMENTE NADA da API para este projeto, cria uma linha "fantasma" (placeholder)
                print(f"Nenhum dado encontrado para o projeto ID: {limpar_pid}. Criando registro placeholder...")
                
                # Preenche todas as colunas da lista lá de cima com o símbolo '-'
                registro_vazio = {col: '-' for col in nomes_colunas}
                
                # Sobrescreve apenas os IDs para sabermos de qual obra é essa linha fantasma
                registro_vazio['id_unico'] = limpar_pid
                registro_vazio['idProjetoInvestimento'] = limpar_pid
                estado_dados.append(registro_vazio) # Guarda a linha fantasma no bolsão
            
            # --- PAUSA DE SEGURANÇA ---
            # O robô dorme um valor quebrado entre 2 e 3 segundos antes de buscar a próxima obra (evita o erro 429)
            time.sleep(random.uniform(2, 3)) 
            # --------------------------------------------------------

        if not estado_dados: # Se ao final do estado não tiver nenhuma obra válida (ou fantasma)
            print(f"Nenhum dado, nem registro placeholder, encontrado para o estado {estado}. Nenhuma tabela será criada.")
            continue # Pula pro próximo estado

        # Pega a "sacola" gigante de dicionários que juntamos e transforma em uma planilha oficial do Pandas
        df = pd.DataFrame(estado_dados)

        # --- PADRONIZAÇÃO DAS COLUNAS PARA O POSTGRESQL ---
        # Renomeia o padrão da web (camelCase: ex 'nomeTipoEmpenho') para o padrão do banco (snake_case: ex 'nome_tipo_empenho')
        df = df.rename(columns={
            'id_unico': 'id_unico',
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
        })

        # Define qual será o nome exato da tabela que será criada/substituída no PostgreSQL
        nome_tabela = f'estados_{estado.lower()}_execucaofinanceira_detalhes'

        try:
            print(f"\nSalvando {len(df)} registros na tabela '{nome_tabela}'...")
            
            # A cartada final: o Pandas pega o dataframe gigante e empurra pro PostgreSQL de uma vez só!
            # if_exists='replace' significa: "se essa tabela já existir lá no banco, apague ela e crie essa nova por cima".
            df.to_sql(name=nome_tabela, con=engine, if_exists='replace', index=False)
            
            print(f"Dados financeiros de {estado} salvos com sucesso na tabela '{nome_tabela}'.")
        except Exception as e: # Se o banco recusar a tabela ou travar a gravação
            print(f"ERRO ao salvar dados na tabela '{nome_tabela}': {e}")
    
    print("\nProcessamento de todos os estados concluído.")

# Ordem de execução: quando você aperta o botão de "Run" (rodar), o Python entra aqui primeiro e chama a função mestra.
if __name__ == "__main__":
    processar_carregar_dados()