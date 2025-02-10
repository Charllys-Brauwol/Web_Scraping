##########################Ministérios Diversos########################################

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options


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

    diretorio_destino = f"D:\\Mestrado\\Orientador\\Código de Web Scraping\\Tópicos\\BD\\{orgao}" 
    nome_do_arquivo = f"{orgao}.xlsx"  

    #Configurar o WebDriver
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": diretorio_destino,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })

    driver = webdriver.Chrome(options=chrome_options)

    url = "https://obras.paineis.gov.br/extensions/obras/obras.html"
    driver.get(url)

    time.sleep(5)

    try:
        # Aguarda e localiza o elemento "Órgão Superior" pelo texto exato
        orgao_superior = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//h6[text()='Órgão Superior']")))

        # Clica no elemento "Órgão Superior"
        orgao_superior.click()

        print("Filtro 'Órgão Superior' selecionado.")

        time.sleep(5)

        # Aguardar o campo de pesquisa aparecer usando data-testid
        novo_campo_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input-field']")))

        time.sleep(5)  # Pequeno atraso para garantir estabilidade

        # Inserir texto da pesquisa
        texto_para_escrever = termo
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

        # Aguarda até que o botão de exportação esteja visível e clicável
        botao_exportar = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.ID, "btn-export-tbl-detalhes-obras"))
)

        # Clica no botão de exportação
        botao_exportar.click()


        time.sleep(10)

    except Exception as e:
        print(f"Erro na consulta para {orgao} - {termo}: {str(e)}")

    finally:
        # Certifique-se de fechar o navegador, mesmo em caso de exceção
        driver.quit()

    # Adicione um pequeno atraso entre as iterações, se necessário
    time.sleep(2)
