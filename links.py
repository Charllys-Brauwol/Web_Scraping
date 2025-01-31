import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

# URL da página que você deseja fazer web scraping
url = "https://portaldatransparencia.gov.br/despesas/orgao?&orgaos=OS39000&ordenarPor=orgaoSuperior&direcao=asc"

# Configurar o WebDriver (certifique-se de ter o chromedriver instalado e no PATH)
driver = webdriver.Chrome()

# Headers da solicitação
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}

# Realize uma solicitação HTTP para obter o conteúdo da página
driver.get(url)
time.sleep(5)  # Aguarde alguns segundos para garantir que a página seja carregada completamente

# Localize o botão de download pelo texto ou outro identificador
# Substitua "btnBaixar" pelo texto real ou identificador do botão
download_button = driver.find_element(By.XPATH, "//*[contains(text(), 'Baixar')]")
download_button.click()

# Aguarde alguns segundos para garantir que o download seja iniciado
time.sleep(10)  # Ajuste conforme necessário

# Use BeautifulSoup para analisar o conteúdo HTML da página após o download (se necessário)
# (Adicione aqui a lógica para trabalhar com o arquivo baixado, se aplicável)

# Feche o navegador
driver.quit()
