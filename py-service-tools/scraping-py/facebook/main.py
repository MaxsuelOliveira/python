import time
import requests
from bs4 import BeautifulSoup

# Função para baixar o vídeo
def baixar_video(video_url, file_name):
    video_response = requests.get(video_url)
    with open(file_name, 'wb') as video_file:
        video_file.write(video_response.content)
    print(f"Vídeo {file_name} baixado com sucesso!")

# URL do reel do Facebook
reel_url = 'https://www.facebook.com/reel/485006604512334'


time.sleep(60)

# Fazer a requisição para obter o HTML da página
response = requests.get(reel_url)

# Usar BeautifulSoup para analisar o HTML
soup = BeautifulSoup(response.text, 'lxml')

print()

with open('facebook.html', 'w', encoding='utf-8') as file:
    file.write(soup.prettify())


# Procurar a tag de vídeo
video_tag = soup.find('video')

if video_tag:
    # Extrair a URL do vídeo
    video_url = video_tag['src']
    print(f"URL do vídeo: {video_url}")
    
    # Baixar o vídeo
    baixar_video(video_url, 'video_facebook.mp4')
else:
    print("Nenhum vídeo encontrado na página.")
