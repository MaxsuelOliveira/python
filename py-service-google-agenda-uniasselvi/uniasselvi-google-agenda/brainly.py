import os
import requests
from urllib import request
from bs4 import BeautifulSoup

URL_API = "https://brainly.com.br/tarefa"

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.27'
}

brainly_cookie = os.getenv("BRAINLY_COOKIE", "").strip()
if brainly_cookie:
    headers['cookie'] = brainly_cookie

question = input("ID da questão : ")
# question = 52044973

html_doc = requests.get(f"{URL_API}/{question}", headers=headers)


print(html_doc.url)

soup = BeautifulSoup(html_doc.text, 'html.parser')

# print(soup.prettify())

resposta = soup.find_all("div")

print(soup)

for value in resposta:
    response = value.get_attribute_list('data-testid')[0]

    if response != "None":
        if response == "question_box_text" or response == "question_container":
            print(value.get_text())
        elif  response == "answer_box_content" or  response == "answer_box_text":
            print(value.get_text())

   
    
# print(resposta)