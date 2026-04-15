import requests
from bs4 import BeautifulSoup

url = "https://www.shoppe.com.br/produto/1234567890"

response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

price = soup.find("span", {"class": "price"}).text

print("Preço do produto: " + price)
