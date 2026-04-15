import requests
from bs4 import BeautifulSoup

url = "https://www.mercadolivre.com.br/notebook-gamer-acer-nitro-v-intel-core-i7-13-geraco-16gb-512gb-rtx4050-linux-gutta-156-fhd-anv15-51-7037/p/MLB38470066"

response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")


status_produto = soup.find("span", {"class": "ui-pdp-subtitle"}).text
loja = soup.find("div", {"class": "ui-pdp-seller"}).text
# loja_link = loja = soup.find("a", {"class": "ui-pdp__header-top-brand__text"})['href']

title = soup.find("h1", {"class": "ui-pdp-title"}).text
promotions = soup.find("a", {"class": "ui-pdp-promotions-pill-label__target"}).text
mais_vendido = soup.find("a", {"class": "ui-pdp-promotions-pill-label__target"}).text

detalhes = []
detalhes_produto = soup.find("div", {"class": "ui-pdp-container__row--highlighted-specs-features"})
detalhes_produto = detalhes_produto.find_all("li")
for i in detalhes_produto:
    detalhes.append(i.text) 

# caracteristicas = soup.find("section", {"class": "ui-vpp-highlighted-specs"}).text

amount = soup.find("span", {"class": "andes-money-amount__fraction"}).text
fraction = soup.find("div", {"class": "ui-pdp-price__second-line"})
fraction = fraction.find("span", {"data-testid": "price-part"}).text
discount = soup.find("span", {"class": "andes-money-amount__discount"}).text

print("Status do produto           : " + status_produto)
print("Loja                        : " + loja)
print("Título do produto           : " + title)
print("Promoções                   : " + promotions)
print("Mais vendido                : " + mais_vendido)
print("Detalhes do produto         : ", detalhes)
# print("Características do produto  : " + caracteristicas)

print("Preço do produto (normal)   : R$" + amount)
print("Desconto                    : " + discount)
print("Preço do produto (desconto) : " + fraction)


# registra no localstorage
