import os
import schedule
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def update(codigo, produtos):
    try:
        # Ler o JSON existente do arquivo
        with open("rastreios.json", "r") as arquivo:
            dados = json.load(arquivo)
    except (FileNotFoundError, json.JSONDecodeError):
        # Se o arquivo não existir ou estiver corrompido, inicializa com uma lista vazia
        dados = []

    # Atualiza o objeto correspondente, baseado na chave única
    objeto_atualizado = False
    for item in dados:
        if item.get('codigo') == codigo:  # Supondo que 'codigo' seja a chave única
            item.update(produtos)  # Atualiza apenas os campos que mudaram
            objeto_atualizado = True
            break

    # Se a chave não foi encontrada, podemos adicionar um novo item, se necessário
    if not objeto_atualizado:
        dados.append(produtos)

    # Escreve as mudanças no arquivo JSON
    with open("rastreios.json", "w") as arquivo:
        json.dump(dados, arquivo, indent=4)


def compare(dados):
    if not os.path.exists("rastreios.json"):
        with open("rastreios.json", "w") as rastreios:
            rastreios.write(json.dumps(dados, indent=4))
        return  # Retorna após criar o arquivo

    with open("rastreios.json", "r") as rastreios:
        produtos = json.load(rastreios)  # Carrega o JSON como um objeto Python
    
    for produto in produtos:
        for dado in dados:
            if produto["codigo"] == dado["codigo"]:
                # Compara os status e atualiza se houver mudanças
                if dado["info"]["status"] != produto["info"]["status"]:
                    update(dado["codigo"], dado)
                else:
                    print("Status não atualizado ...")


def save():
    response = []
    cards = browser.find_elements(By.CLASS_NAME, 'data-tracking__container__card')
    
    for card in cards:
        # Encontra os detalhes específicos dentro de cada card
        nome_loja = card.find_elements(By.CLASS_NAME, 'data-tracking__container__card__panel__wrapper__details__info')[0].text
        codigo_rastreamento = card.find_elements(By.CLASS_NAME, 'data-tracking__container__card__panel__wrapper__details__info')[1].text
        status = card.find_elements(By.CLASS_NAME, 'data-tracking__container__card__panel__wrapper__details__info')[2].text

        # Cria o dicionário de dados
        data = {
            "codigo": codigo_rastreamento,
            "info": {
                "nome_loja": nome_loja,
                "codigo_rastreamento": codigo_rastreamento,
                "status": status
            }
        }

        response.append(data)

    # Comparação de dados
    return response


def get():
    try:
        browser = webdriver.Chrome()
        browser.implicitly_wait(5)

        # Acessa o site
        browser.get('https://totalconecta.totalexpress.com.br/rastreamento/')
        assert 'Total Conecta | Portal de autoatendimento' in browser.title

        # Tenta localizar o campo de texto e enviar a chave de rastreamento
        elem = browser.find_element(By.CLASS_NAME, 'tex-input__input')  # Localiza a caixa de busca
        elem.send_keys('08552356597' + Keys.RETURN)

        # Aguarda o iframe do reCAPTCHA carregar
        try:
            # Localiza o iframe do reCAPTCHA
            recaptcha_iframe = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha']"))
            )
            
            # Troca o foco para o iframe do reCAPTCHA
            browser.switch_to.frame(recaptcha_iframe)

            # Localiza o checkbox do reCAPTCHA dentro do iframe
            recaptcha_checkbox = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
            )

            # Cria a instância de ActionChains para mover o mouse e clicar no checkbox
            actions = ActionChains(browser)
            actions.move_to_element(recaptcha_checkbox).click().perform()

            print("reCAPTCHA clicado")

            time.sleep(5)

            # Volta ao contexto da página principal antes de clicar no botão submit
            browser.switch_to.default_content()

            # Localiza o botão de envio (ajuste o XPath conforme necessário)
            buttonSubmit = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button"))
            )

            buttonSubmit.click()
            print("Botão")
            time.sleep(5)
            print("Dados carregados ...")

            # Salva os dados
            print("Salvando dados ...")
            rastreios = save()
            # Compara os dados
            print("Comparando dados ...")
            compare(rastreios)
            
        except Exception as e:
            print(f"Erro ao interagir com o reCAPTCHA: {e}")

        browser.quit()
        
        # O loop continua conforme sua lógica
        # while True:
        #     try:
        #         schedule.run_pending()
        #         time.sleep(5)
        #         print("...")
        #     except Exception as e:
        #         print(e)
        #         break

    except Exception as e:
        print(f"Erro na execução: {e}")
    finally:
        # Mantém o navegador aberto sem fechar
        pass


if __name__ == "__main__":
    # Buscando dados
    print("Iniciando o rastreamento ...")
    schedule.every().day.at("07:30:00").do(get)
    schedule.every().day.at("11:30:00").do(get)
    schedule.every().day.at("14:15:00").do(get)
    schedule.every().day.at("16:30:00").do(get)
    schedule.every().day.at("19:30:00").do(get)
    schedule.every().day.at("21:30:00").do(get)
    

while True:
    schedule.run_pending()
    time.sleep(1)