import os
import glob
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import pandas as pd



# Ler a lista de órgãos e termos de pesquisa do arquivo de texto
with open("pesquisaautomatica.txt", "r", encoding="utf-8") as file:
    linhas = file.read().splitlines()

# Certificar-se de que há um número par de linhas
if len(linhas) % 2 != 0:
    raise ValueError("O arquivo deve conter pares consecutivos de linhas, cada par representando um órgão e um termo de pesquisa.")

# Iterar sobre pares consecutivos de linhas
for i in range(0, len(linhas), 2):
    orgao = linhas[i]
    termo = linhas[i + 1]

    diretorio_destino = f"C:\\Users\\charl\\Downloads\\Arquivos_BD\\{orgao}" 
    nome_do_arquivo = f"{orgao}.xlsx"  # Substitua pelo nome desejado e extensão

    #Configurar o WebDriver
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": diretorio_destino,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })

    driver = webdriver.Chrome(options=chrome_options)

    url = "https://obras.paineis.gov.br/extensions/painel-obras/painel-obras.html"
    driver.get(url)

    time.sleep(5)

    try:
        #Localizar e clicar no primeiro filtro
        seletor_do_campo = "fltr-orgao-sup"
        campo_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, seletor_do_campo))
        )
        campo_input.click()

        time.sleep(5)

        #Aguardar o campo de pesquisa aparecer
        novo_seletor_do_campo = "Pesquisar na caixa de listagem"
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{novo_seletor_do_campo}']"))
        )
        time.sleep(5)

        #   Inserir texto da pesquisa
        texto_para_escrever = termo
        novo_campo_input.send_keys(texto_para_escrever)

        #Seleciona os itens
        novo_campo_input.send_keys(Keys.ENTER)

        time.sleep(5)

        # Confirma a seleção
        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(5)

        #Identifica todos os arquivos no diretório e os exclui
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*'))
        for arquivo in arquivos_no_diretorio:
            os.remove(arquivo)

        #Seleciona o botão de download da planilha
        seletor_do_link = "a[title='Exportar dados da tabela Detalhes das Obras']"
        link_exportacao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_link))
        )
        link_exportacao.click()

        time.sleep(10)

        # Aguarda o download
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx.crdownload'))
        while arquivos_no_diretorio:
            time.sleep(1)
            arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx.crdownload'))

        # Identifica o arquivo mais recente
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx'))
        if arquivos_no_diretorio:
            arquivo_mais_recente = max(arquivos_no_diretorio, key=os.path.getctime)

        # Converte o arquivo Excel para CSV
        df = pd.read_excel(arquivo_mais_recente)

        # Converte todas as colunas para o tipo de dados string (object)
        df = df.astype(str)

        # Substitui apenas os valores NaN por uma string vazia
        df.replace({'nan': ''}, inplace=True)

        # Salva o DataFrame para CSV
        novo_caminho_do_arquivo_csv = os.path.join(diretorio_destino, nome_do_arquivo.replace('.xlsx', '.csv'))
        df.to_csv(novo_caminho_do_arquivo_csv, index=False, sep=';', encoding='utf-8-sig')

        # Apaga o cabeçalho
        df_csv = pd.read_csv(novo_caminho_do_arquivo_csv, sep=';', encoding='utf-8-sig', low_memory=False)
        df_csv.to_csv(novo_caminho_do_arquivo_csv, index=False, sep=';', encoding='utf-8-sig', header=False)

        time.sleep(5)

    except Exception as e:
        print(f"Erro na consulta para {orgao} - {termo}: {str(e)}")

    finally:
        # Certifique-se de fechar o navegador, mesmo em caso de exceção
        driver.quit()

    # Adicione um pequeno atraso entre as iterações, se necessário
    time.sleep(2)













##########################PARTE DO MIN. CIDADES E MIN. DA EDUCAÇÃO########################################

# Ler a lista de órgãos e termos de pesquisa do arquivo de texto
with open("pesquisacidadeeeducacao.txt", "r", encoding="utf-8") as file:
    linhas = file.read().splitlines()

# Certificar-se de que há um número par de linhas
if len(linhas) % 3 != 0:
    raise ValueError("O arquivo deve conter pares consecutivos de linhas, cada par representando um órgão e um termo de pesquisa.")

# Iterar sobre pares consecutivos de linhas
for i in range(0, len(linhas), 3):
    orgaosup = linhas[i]
    termoorgsup = linhas[i + 1]
    termosituacao = linhas[i + 2]

    # Diretório e o nome do arquivo desejado
    diretorio_destino = f"C:\\Users\\charl\\Downloads\\Arquivos_BD\\{orgaosup}" 
    nome_do_arquivo = f"{orgaosup}.xlsx"  # Substitua pelo nome desejado e extensão

    # Configurar o WebDriver
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": diretorio_destino,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })

    try:
        driver = webdriver.Chrome(options=chrome_options)

        url = "https://obras.paineis.gov.br/extensions/painel-obras/painel-obras.html"
        driver.get(url)

        time.sleep(5)

        # Localizar e clicar no primeiro filtro
        seletor_do_campo = "fltr-orgao-sup"
        campo_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, seletor_do_campo))
        )
        campo_input.click()

        # Aguardar o campo de pesquisa aparecer
        novo_seletor_do_campo = "Pesquisar na caixa de listagem"
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{novo_seletor_do_campo}']"))
        )

         #   Inserir texto da pesquisa
        texto_para_escrever = termoorgsup
        novo_campo_input.send_keys(texto_para_escrever)

        # Seleciona os itens
        novo_campo_input.send_keys(Keys.ENTER)

        time.sleep(5)

        # Confirma a seleção
        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(10)

        # Localizar e clicar no primeiro filtro
        seletor_do_campo = "fltr-situacao-atual"
        campo_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, seletor_do_campo))
        )
        campo_input.click()

        # Aguardar o campo de pesquisa aparecer
        novo_seletor_do_campo = "Pesquisar na caixa de listagem"
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{novo_seletor_do_campo}']"))
        )

         #   Inserir texto da pesquisa
        texto_para_escrever = termosituacao
        novo_campo_input.send_keys(texto_para_escrever)

        # Seleciona os itens
        novo_campo_input.send_keys(Keys.ENTER)

        time.sleep(5)

        # Confirma a seleção
        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(10)

        # Identifica todos os arquivos no diretório e os exclui
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*'))
        for arquivo in arquivos_no_diretorio:
            os.remove(arquivo)

        # Seleciona o botão de download da planilha
        seletor_do_link = "a[title='Exportar dados da tabela Detalhes das Obras']"
        link_exportacao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_link))
        )
        link_exportacao.click()

        time.sleep(15)

        # Aguarda o download
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx.crdownload'))
        while arquivos_no_diretorio:
            time.sleep(1)
            arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx.crdownload'))

        # Identifica o arquivo mais recente
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx'))
        if arquivos_no_diretorio:
            arquivo_mais_recente = max(arquivos_no_diretorio, key=os.path.getctime)

        # Converte o arquivo Excel para CSV
        df = pd.read_excel(arquivo_mais_recente)

        # Converte todas as colunas para o tipo de dados string (object)
        df = df.astype(str)

        # Substitui apenas os valores NaN por uma string vazia
        df.replace({'nan': ''}, inplace=True)

        # Salva o DataFrame para CSV
        novo_caminho_do_arquivo_csv = os.path.join(diretorio_destino, nome_do_arquivo.replace('.xlsx', '.csv'))
        df.to_csv(novo_caminho_do_arquivo_csv, index=False, sep=';', encoding='utf-8-sig')

        # Apaga o cabeçalho
        df_csv = pd.read_csv(novo_caminho_do_arquivo_csv, sep=';', encoding='utf-8-sig', low_memory=False)
        df_csv.to_csv(novo_caminho_do_arquivo_csv, index=False, sep=';', encoding='utf-8-sig', header=False)

        time.sleep(5)

    except Exception as e:
        print(f"Erro na consulta para {orgaosup} - {termoorgsup} - {termosituacao}: {str(e)}")

    finally:
        # Certifique-se de fechar o navegador, mesmo em caso de exceção
        if 'driver' in locals() and driver:
            driver.quit()

    # Adicione um pequeno atraso entre as iterações, se necessário
    time.sleep(2)














##########################PARTE DO MIN. DA SAUDE########################################


# Ler a lista de órgãos e termos de pesquisa do arquivo de texto
with open("pesquisasaude.txt", "r", encoding="utf-8") as file:
    linhas = file.read().splitlines()

# Certificar-se de que há um número par de linhas
if len(linhas) % 3 != 0:
    raise ValueError("O arquivo deve conter pares consecutivos de linhas, cada par representando um órgão e um termo de pesquisa.")

# Iterar sobre pares consecutivos de linhas
for i in range(0, len(linhas), 3):
    orgaosup = linhas[i]
    termoorgsup = linhas[i + 1]
    orgao = linhas[i + 2]


    diretorio_destino = f"C:\\Users\\charl\\Downloads\\Arquivos_BD\\{orgaosup}"
    nome_do_arquivo = f"{orgaosup}.xlsx"

    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": diretorio_destino,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })

    try:
        driver = webdriver.Chrome(options=chrome_options)

        url = "https://obras.paineis.gov.br/extensions/painel-obras/painel-obras.html"
        driver.get(url)

        time.sleep(5)

        seletor_do_campo = "fltr-orgao-sup"
        campo_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, seletor_do_campo))
        )
        campo_input.click()

        novo_seletor_do_campo = "Pesquisar na caixa de listagem"
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{novo_seletor_do_campo}']"))
        )

         #   Inserir texto da pesquisa
        texto_para_escrever = termoorgsup
        novo_campo_input.send_keys(texto_para_escrever)


        novo_campo_input.send_keys(Keys.ENTER)

        time.sleep(5)

        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(10)

        seletor_do_campo = "fltr-orgao"
        campo_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, seletor_do_campo))
        )
        campo_input.click()

        novo_seletor_do_campo = "Pesquisar na caixa de listagem"
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{novo_seletor_do_campo}']"))
        )

         #   Inserir texto da pesquisa
        texto_para_escrever = orgao
        novo_campo_input.send_keys(texto_para_escrever)

        novo_campo_input.send_keys(Keys.ENTER)

        time.sleep(5)

        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(10)

        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*'))
        for arquivo in arquivos_no_diretorio:
            os.remove(arquivo)

        seletor_do_link = "a[title='Exportar dados da tabela Detalhes das Obras']"
        link_exportacao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_link))
        )
        link_exportacao.click()

        time.sleep(15)

        # Aguarda o download
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx.crdownload'))
        while arquivos_no_diretorio:
            time.sleep(1)
            arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx.crdownload'))

            # Identifica o arquivo mais recente
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx'))
        if arquivos_no_diretorio:
            arquivo_mais_recente = max(arquivos_no_diretorio, key=os.path.getctime)

            # Converte o arquivo Excel para CSV
        df = pd.read_excel(arquivo_mais_recente)

            # Converte todas as colunas para o tipo de dados string (object)
        df = df.astype(str)

            # Substitui apenas os valores NaN por uma string vazia
        df.replace({'nan': ''}, inplace=True)

            # Salva o DataFrame para CSV
        novo_caminho_do_arquivo_csv = os.path.join(diretorio_destino, nome_do_arquivo.replace('.xlsx', '.csv'))
        df.to_csv(novo_caminho_do_arquivo_csv, index=False, sep=';', encoding='utf-8-sig')

            # Apaga o cabeçalho
        df_csv = pd.read_csv(novo_caminho_do_arquivo_csv, sep=';', encoding='utf-8-sig', low_memory=False)
        df_csv.to_csv(novo_caminho_do_arquivo_csv, index=False, sep=';', encoding='utf-8-sig', header=False)

        time.sleep(5)

    except Exception as e:
        print(f"Erro na consulta para {orgaosup} - {termoorgsup} - {orgao}: {str(e)}")

    finally:
        if 'driver' in locals() and driver:
            driver.quit()

    time.sleep(2)






# Ler a lista de órgãos e termos de pesquisa do arquivo de texto
with open("pesquisasaude2.txt", "r", encoding="utf-8") as file:
    linhas = file.read().splitlines()

# Certificar-se de que há um número par de linhas
if len(linhas) % 4 != 0:
    raise ValueError("O arquivo deve conter pares consecutivos de linhas, cada par representando um órgão e um termo de pesquisa.")

# Iterar sobre pares consecutivos de linhas
for i in range(0, len(linhas), 4):
    orgaosup = linhas[i]
    termoorgsup = linhas[i + 1]
    orgao = linhas[i + 2]
    termosituacao = linhas[i + 3]


    diretorio_destino = f"C:\\Users\\charl\\Downloads\\Arquivos_BD\\{orgaosup}"
    nome_do_arquivo = f"{orgaosup}.xlsx"

    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": diretorio_destino,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })

    try:
        driver = webdriver.Chrome(options=chrome_options)

        url = "https://obras.paineis.gov.br/extensions/painel-obras/painel-obras.html"
        driver.get(url)

        time.sleep(5)

        seletor_do_campo = "fltr-orgao-sup"
        campo_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, seletor_do_campo))
        )
        campo_input.click()

        novo_seletor_do_campo = "Pesquisar na caixa de listagem"
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{novo_seletor_do_campo}']"))
        )

         #   Inserir texto da pesquisa
        texto_para_escrever = termoorgsup
        novo_campo_input.send_keys(texto_para_escrever)

        novo_campo_input.send_keys(Keys.ENTER)

        time.sleep(5)

        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(10)

        seletor_do_campo = "fltr-orgao"
        campo_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, seletor_do_campo))
        )
        campo_input.click()

        novo_seletor_do_campo = "Pesquisar na caixa de listagem"
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{novo_seletor_do_campo}']"))
        )

         #   Inserir texto da pesquisa
        texto_para_escrever = orgao
        novo_campo_input.send_keys(texto_para_escrever)

        novo_campo_input.send_keys(Keys.ENTER)

        time.sleep(5)

        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(5)

        seletor_do_campo = "fltr-situacao-atual"
        campo_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, seletor_do_campo))
        )
        campo_input.click()

        novo_seletor_do_campo = "Pesquisar na caixa de listagem"
        novo_campo_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{novo_seletor_do_campo}']"))
        )

         #   Inserir texto da pesquisa
        texto_para_escrever = termosituacao
        novo_campo_input.send_keys(texto_para_escrever)

        novo_campo_input.send_keys(Keys.ENTER)

        time.sleep(10)

        seletor_do_botao = "button[title='Confirmar seleção']"
        botao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_botao))
        )
        botao.click()

        time.sleep(10)

        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*'))
        for arquivo in arquivos_no_diretorio:
            os.remove(arquivo)

        seletor_do_link = "a[title='Exportar dados da tabela Detalhes das Obras']"
        link_exportacao = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_do_link))
        )
        link_exportacao.click()

        time.sleep(15)

        # Aguarda o download
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx.crdownload'))
        while arquivos_no_diretorio:
            time.sleep(1)
            arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx.crdownload'))

            # Identifica o arquivo mais recente
        arquivos_no_diretorio = glob.glob(os.path.join(diretorio_destino, '*.xlsx'))
        if arquivos_no_diretorio:
            arquivo_mais_recente = max(arquivos_no_diretorio, key=os.path.getctime)

            # Converte o arquivo Excel para CSV
        df = pd.read_excel(arquivo_mais_recente)

            # Converte todas as colunas para o tipo de dados string (object)
        df = df.astype(str)

            # Substitui apenas os valores NaN por uma string vazia
        df.replace({'nan': ''}, inplace=True)

            # Salva o DataFrame para CSV
        novo_caminho_do_arquivo_csv = os.path.join(diretorio_destino, nome_do_arquivo.replace('.xlsx', '.csv'))
        df.to_csv(novo_caminho_do_arquivo_csv, index=False, sep=';', encoding='utf-8-sig')

            # Apaga o cabeçalho
        df_csv = pd.read_csv(novo_caminho_do_arquivo_csv, sep=';', encoding='utf-8-sig', low_memory=False)
        df_csv.to_csv(novo_caminho_do_arquivo_csv, index=False, sep=';', encoding='utf-8-sig', header=False)

        time.sleep(5)

    except Exception as e:
        print(f"Erro na consulta para {orgaosup} - {termoorgsup} - {orgao} - {termosituacao}: {str(e)}")

    finally:
        if 'driver' in locals() and driver:
            driver.quit()

    time.sleep(2)