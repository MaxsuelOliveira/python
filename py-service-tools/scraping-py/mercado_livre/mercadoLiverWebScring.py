import requests
from bs4 import BeautifulSoup

url = "https://produto.mercadolivre.com.br/MLB-1234567890"

response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

price = soup.find("span", {"class": "price-tag-fraction"}).text

print("Preço do produto: R$" + price)


# registra no localstorage
