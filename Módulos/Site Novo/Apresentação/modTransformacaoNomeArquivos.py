# ==============================================================================
# --- IMPORTAÇÕES ---
# Módulos básicos do Python para ler pastas do sistema e trabalhar com datas.
# ==============================================================================
import os  # Para navegar e modificar arquivos e pastas no Windows
import datetime  # Para manipular datas, medir tempo e formatar textos como data

# ==============================================================================
# --- CONFIGURAÇÕES INICIAIS ---
# ==============================================================================
# Caminho principal (pasta "mãe") onde os arquivos e subpastas foram baixados
diretorio_base = r"C:\\Users\\Charllys_Brauwol\\Downloads\\Arquivos_BD"

# Obtém a data e hora exatas de agora (usado como referência para saber a idade do arquivo)
data_atual = datetime.datetime.today()

# ==============================================================================
# --- LOOP PRINCIPAL: VARRENDO AS PASTAS ---
# ==============================================================================
# Percorre todos os itens (pastas de cada órgão/estado) dentro do diretório base
for orgao in os.listdir(diretorio_base):
    # Junta o caminho base com o nome da pasta (Ex: C:\...\Arquivos_BD\SP)
    caminho_orgao = os.path.join(diretorio_base, orgao)

    # Verifica se o item atual no loop é realmente uma pasta (diretório) e não um arquivo solto
    if os.path.isdir(caminho_orgao):
        
        # --- LOOP SECUNDÁRIO: VARRENDO OS ARQUIVOS DA PASTA ---
        # Percorre todos os arquivos que estão dentro da pasta desse órgão/estado
        for arquivo in os.listdir(caminho_orgao):
            # Monta o caminho completo do arquivo (Ex: C:\...\Arquivos_BD\SP\planilha.xlsx)
            caminho_antigo = os.path.join(caminho_orgao, arquivo)

            # Verifica se o arquivo tem a extensão do Excel (.xlsx). Ignora PDFs, TXTs, etc.
            if arquivo.endswith(".xlsx"):
                # Quebra o nome do arquivo em duas partes: o nome em si e a extensão
                # Exemplo: de "planilha.xlsx", nome_base vira "planilha" e extensao vira ".xlsx"
                nome_base, extensao = os.path.splitext(arquivo)

                # ==============================================================================
                # --- VERIFICAÇÃO DE IDADE DO ARQUIVO ---
                # ==============================================================================
                # Obtém a data de criação/modificação do arquivo direto do sistema operacional (Windows)
                timestamp = os.path.getctime(caminho_antigo)  
                # Transforma o código numérico do Windows (timestamp) em uma data real legível
                data_download = datetime.datetime.fromtimestamp(timestamp)

                # Faz a conta: Data de Hoje - Data do Arquivo.
                # Se a diferença de dias for maior que 3...
                if (data_atual - data_download).days > 3:
                    continue  # ...o comando 'continue' pula este arquivo (ignora planilhas velhas)

                # ==============================================================================
                # --- VERIFICAÇÃO DO NOME (FORMATO DA DATA) ---
                # ==============================================================================
                # Tenta verificar se o arquivo JÁ FOI renomeado anteriormente para não fazer o trabalho duas vezes
                try:
                    # Tenta converter o nome do arquivo (ex: "2023-10-25") para um formato de Data oficial do Python
                    datetime.datetime.strptime(nome_base, "%Y-%m-%d")
                    # Se não der erro, significa que o nome já é uma data perfeita. Imprime o aviso.
                    print(f"O arquivo {arquivo} já está no formato correto. Nenhuma alteração feita.")
                    continue  # Pula para o próximo arquivo, deixando este intacto
                
                except ValueError:
                    # Se der erro (ValueError), significa que o nome é diferente de uma data (ex: "planilha_final").
                    pass  # O comando 'pass' diz pro Python: "Tudo bem, siga em frente e renomeie o arquivo abaixo".

                # ==============================================================================
                # --- RENOMEAÇÃO DO ARQUIVO ---
                # ==============================================================================
                # Monta o novo nome juntando a Data do Download (formatada como Ano-Mês-Dia) e a extensão (.xlsx)
                novo_nome = f"{data_download.strftime('%Y-%m-%d')}{extensao}"
                
                # Monta o caminho completo com o novo nome que o arquivo vai receber
                caminho_novo = os.path.join(caminho_orgao, novo_nome)

                # Executa o comando no Windows que efetivamente troca o nome antigo pelo novo
                os.rename(caminho_antigo, caminho_novo)
                
                # Imprime no terminal o resultado para você acompanhar o que está acontecendo
                print(f"Arquivo renomeado: {arquivo} -> {novo_nome}")