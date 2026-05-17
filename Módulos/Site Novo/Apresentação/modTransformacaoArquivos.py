# ==============================================================================
# --- IMPORTAÇÕES ---
# Ferramentas para manipulação de arquivos, tempo, tabelas e localização geográfica.
# ==============================================================================
import os  # Para navegar pelas pastas e arquivos do seu computador (Windows)
import datetime  # Para trabalhar com datas e medir o tempo (ex: arquivos baixados há X dias)
import pandas as pd  # Para abrir, editar e salvar as planilhas do Excel
from geopy.geocoders import Nominatim  # Uma biblioteca que acessa um mapa global gratuito (OpenStreetMap) para buscar coordenadas

# ==============================================================================
# --- CONFIGURAÇÕES INICIAIS ---
# ==============================================================================
# Onde estão as pastas criadas pelos seus scripts anteriores
diretorio_base = r"C:\Users\Charllys_Brauwol\Downloads\Arquivos_BD"

# Pega o dia e hora exatos de agora (usado para comparar a idade dos arquivos depois)
data_atual = datetime.datetime.today()

# Prepara o "GPS" do Python. O 'user_agent' é como se fosse o seu crachá. 
# A API gratuita do Nominatim exige que você se identifique para não te bloquear.
geolocator = Nominatim(user_agent="geo_correction")

# ==============================================================================
# --- FUNÇÃO: VALIDAR COORDENADAS ---
# Verifica se a Latitude ou Longitude escrita na planilha faz sentido real.
# ==============================================================================
def validar_coordenada(valor):
    try:
        # Transforma o valor em texto, troca a vírgula do Brasil por ponto (padrão gringo) e tenta virar número (float)
        valor = float(str(valor).replace(",", "."))  
        # Uma latitude no planeta Terra só existe entre -90 (Polo Sul) e 90 (Polo Norte). Retorna Verdadeiro se for válido.
        return -90 <= valor <= 90  
    except ValueError: # Se a célula estiver vazia, com letras ou travada
        return False # Retorna Falso (coordenada inválida)

# ==============================================================================
# --- FUNÇÃO: BUSCAR COORDENADAS NA INTERNET (GEOLOCAÇÃO) ---
# Se a planilha não tem a coordenada, o robô pesquisa o nome da cidade no mapa.
# ==============================================================================
def obter_coordenadas(municipio_estado):
    try:
        # Manda o nome da cidade (Ex: "Campinas/SP") pro OpenStreetMap procurar
        localizacao = geolocator.geocode(municipio_estado)
        
        if localizacao: # Se o mapa achou a cidade...
            # Devolve a Latitude e Longitude arredondadas para 6 casas decimais (padrão ideal para precisão de GPS)
            return round(localizacao.latitude, 6), round(localizacao.longitude, 6)  
    except Exception as e: # Se a internet cair ou a API negar o acesso
        print(f"Erro ao buscar coordenadas de {municipio_estado}: {e}")
    
    # Se não achou a cidade ou deu erro, devolve "Nada" (None)
    return None, None

# ==============================================================================
# --- FUNÇÃO: EXTRAIR O ANO DE UMA DATA COMPLETA ---
# ==============================================================================
def extrair_ano(data):
    try:
        if isinstance(data, str): # Se a data for apenas um texto (Ex: "15/05/2023")
            # Força o Pandas a tentar transformar esse texto numa Data oficial. 'coerce' transforma os erros em valores nulos.
            data = pd.to_datetime(data, errors="coerce")  
        if pd.notna(data):  # Se a variável 'data' não for nula (ou seja, se a conversão deu certo)
            return str(data.year)  # Arranca só o pedaço do "ano" e devolve como texto
    except Exception:
        pass # Ignora qualquer erro doido que aconteça
    
    return "-" # Se tudo falhar (ex: a célula não tinha data), devolve um traço

# ==============================================================================
# --- LOOP PRINCIPAL: VARRENDO PASTAS E PLANILHAS ---
# ==============================================================================
# O os.listdir lista tudo que tem dentro da sua pasta Arquivos_BD (ex: AC, AL, AM...)
for orgao in os.listdir(diretorio_base):
    # Junta o caminho base com o nome da pasta (Ex: C:\...\Arquivos_BD\SP)
    caminho_orgao = os.path.join(diretorio_base, orgao)

    if os.path.isdir(caminho_orgao):  # Confere se o item atual é realmente uma pasta (e não um arquivo solto)
        
        for arquivo in os.listdir(caminho_orgao): # Lista todos os arquivos dentro da pasta do estado
            caminho_arquivo = os.path.join(caminho_orgao, arquivo) # Monta o caminho completo do arquivo

            # O robô só vai olhar para o arquivo se ele terminar com '.xlsx' (Planilha de Excel)
            if arquivo.endswith(".xlsx"):
                
                # --- VERIFICAÇÃO DE IDADE DO ARQUIVO ---
                # Pega a "data de modificação/criação" do arquivo diretamente do Windows
                timestamp = os.path.getctime(caminho_arquivo)
                data_download = datetime.datetime.fromtimestamp(timestamp) # Traduz o código do Windows para data normal

                # Faz uma conta matemática: Data de Hoje - Data do Arquivo. 
                # Se o arquivo for mais velho que 2 dias, o 'continue' pula ele. 
                # (Isso deixa o script SUPER RÁPIDO porque ele só processa o que você baixou recentemente!)
                if (data_atual - data_download).days > 2:
                    continue

                print(f"Lendo arquivo: {arquivo}")

                try:
                    # --- ABERTURA DO EXCEL ---
                    # Lê a planilha. dtype=str força o Pandas a ler TUDO como texto.
                    # Por que? Para evitar que ele apague o zero à esquerda de ceps ou CNPJs acidentalmente.
                    df = pd.read_excel(caminho_arquivo, dtype=str)  

                    alterado = False  # Um interruptor! Começa desligado. Se a gente alterar a planilha, a gente liga ele.

                    # --- CORREÇÃO 1: LATITUDE E LONGITUDE ---
                    # Só tenta corrigir se essas três colunas existirem na planilha
                    if "Latitude" in df.columns and "Longitude" in df.columns and "Município" in df.columns:
                        
                        # Percorre linha por linha da planilha
                        for i, row in df.iterrows():
                            latitude = row["Latitude"]
                            longitude = row["Longitude"]

                            # Chama a nossa função que confere se as coordenadas são válidas
                            if not (validar_coordenada(latitude) and validar_coordenada(longitude)):
                                municipio_estado = row["Município"] # Se as coordenadas estão erradas, pega o nome da cidade

                                # Só pesquisa se o nome da cidade tiver a barra de estado (Ex: 'Manaus/AM')
                                if "/" in municipio_estado:
                                    # Manda a cidade pro mapa (API) pesquisar a coordenada certa
                                    lat, lon = obter_coordenadas(municipio_estado)
                                    
                                    if lat and lon: # Se o mapa achou a cidade
                                        # Substitui a célula velha pela coordenada nova, garantindo o formato de ponto
                                        df.at[i, "Latitude"] = str(lat).replace(",", ".")
                                        df.at[i, "Longitude"] = str(lon).replace(",", ".")
                                        print(f"Corrigido: {municipio_estado} -> ({lat}, {lon})")
                                        alterado = True # Liga o interruptor: a planilha foi modificada!
                        
                    # --- CORREÇÃO 2: CAMPOS VAZIOS ---
                    # Substitui os temidos campos 'NaN' (Not a Number, quando a célula do Excel é completamente vazia) por '-'
                    df.fillna("-", inplace=True)  
                    # Se tiver células que não eram nulas, mas tinham só um texto vazio "", troca por '-' também
                    df.replace("", "-", inplace=True)  

                    # --- CORREÇÃO 3: ANOS FALTANDO ---
                    # Se a coluna de "Ano Início Obra" existir...
                    if "Ano Início Obra" in df.columns and "Data Início" in df.columns:
                        for i, row in df.iterrows(): # Olha linha por linha
                            if row["Ano Início Obra"] == "-": # Se não preencheram o ano...
                                ano_inicio = extrair_ano(row["Data Início"]) # ...Pede pra nossa função adivinhar o ano usando a data inteira
                                if ano_inicio != "-": # Se a função conseguiu adivinhar
                                    df.at[i, "Ano Início Obra"] = ano_inicio # Preenche a célula
                                    alterado = True # Liga o interruptor

                    # Faz exatamente a mesma coisa que o bloco acima, mas agora para a data de Fim da Obra
                    if "Ano Fim Obra" in df.columns and "Data Fim" in df.columns:
                        for i, row in df.iterrows():
                            if row["Ano Fim Obra"] == "-":
                                ano_fim = extrair_ano(row["Data Fim"])
                                if ano_fim != "-":
                                    df.at[i, "Ano Fim Obra"] = ano_fim
                                    alterado = True

                    # --- SALVAMENTO FINAL ---
                    # Só sobrescreve e salva o Excel se o interruptor estiver Ligado (ou seja, economiza seu HD de não salvar arquivos intocados)
                    if alterado:
                        # Abre o "canudo" de gravação do Pandas em modo escrita ('w') usando o motor do Excel ('openpyxl')
                        with pd.ExcelWriter(caminho_arquivo, engine='openpyxl', mode='w') as writer:
                            # Tira a tabela da memória (df) e joga no arquivo. index=False impede que ele crie aquela coluna chata "0, 1, 2, 3..." no canto.
                            df.to_excel(writer, index=False)
                        print(f"Arquivo atualizado: {arquivo}")

                except Exception as e: # Se a planilha estiver corrompida ou travada (ex: você com o Excel aberto olhando pra ela)
                    print(f"Erro ao processar {arquivo}: {e}")