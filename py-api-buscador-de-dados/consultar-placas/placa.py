import base64
import os
from colorama import Fore, Style, init
import pyfiglet
import requests
from bs4 import BeautifulSoup
import json

# Inicializa o colorama
init(autoreset=True)

def exibir_banner():
    branco = "\033[37m"  # Cor branca
    resetar_cor = "\033[0m"
    
    # Gerar o texto ASCII para "placas - SkipGov"
    banner = pyfiglet.figlet_format("placas - SkipGov", font="slant")
    
    # Exibir o banner
    print(f"{branco}{banner}{resetar_cor}")
    print(f"{branco}(マウリ |ミゲル){resetar_cor}")

# Função para buscar os dados da placa
def bruxovaisefoder(placa):
    url = f'https://placafipe.com/placa/{placa}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise Exception('Error fetching the URL')
    
    soup = BeautifulSoup(response.content, 'html.parser')

    # Ajustar verificações para evitar erros com None
    data = {
        'consultas': 'skipgov Syndicate',
        'ミゲル': 'マウリ',
        'placa': placa,
        'marca': soup.select_one("table.fipeTablePriceDetail tr:nth-child(1) td:nth-child(2)").get_text(strip=True) if soup.select_one("table.fipeTablePriceDetail tr:nth-child(1) td:nth-child(2)") else 'Desconhecido',
        'genero': soup.select_one("table.fipeTablePriceDetail tr:nth-child(2) td:nth-child(2)").get_text(strip=True) if soup.select_one("table.fipeTablePriceDetail tr:nth-child(2) td:nth-child(2)") else 'Desconhecido',
        'modelo': soup.select_one("table.fipeTablePriceDetail tr:nth-child(3) td:nth-child(2)").get_text(strip=True) if soup.select_one("table.fipeTablePriceDetail tr:nth-child(3) td:nth-child(2)") else 'Desconhecido',
        'importado': 'não' if soup.select_one("table.fipeTablePriceDetail tr:nth-child(4) td:nth-child(2)").get_text(strip=True).lower() == 'não' else 'sim' if soup.select_one("table.fipeTablePriceDetail tr:nth-child(4) td:nth-child(2)") else 'Desconhecido',
        'ano': soup.select_one("table.fipeTablePriceDetail tr:nth-child(5) td:nth-child(2)").get_text(strip=True) if soup.select_one("table.fipeTablePriceDetail tr:nth-child(5) td:nth-child(2)") else 'Desconhecido',
        'cor': soup.select_one("table.fipeTablePriceDetail tr:nth-child(6) td:nth-child(2)").get_text(strip=True).lower() if soup.select_one("table.fipeTablePriceDetail tr:nth-child(6) td:nth-child(2)") else 'Desconhecido',
        'Potencia': soup.select_one("table.fipeTablePriceDetail tr:nth-child(7) td:nth-child(2)").get_text(strip=True) if soup.select_one("table.fipeTablePriceDetail tr:nth-child(7) td:nth-child(2)") else 'Desconhecido',
        'combustivel': soup.select_one("table.fipeTablePriceDetail tr:nth-child(8) td:nth-child(2)").get_text(strip=True).lower() if soup.select_one("table.fipeTablePriceDetail tr:nth-child(8) td:nth-child(2)") else 'Desconhecido',
        'uf': soup.select_one("table.fipeTablePriceDetail tr:nth-child(10) td:nth-child(2)").get_text(strip=True).upper() if soup.select_one("table.fipeTablePriceDetail tr:nth-child(10) td:nth-child(2)") else 'Desconhecido',
        'municipio': soup.select_one("table.fipeTablePriceDetail tr:nth-child(11) td:nth-child(2)").get_text(strip=True).lower() if soup.select_one("table.fipeTablePriceDetail tr:nth-child(11) td:nth-child(2)") else 'Desconhecido',
        'image': f'https://placafipe.com/images/placas/reais/ABC/tabelafipebrasil.com-placa-{placa}.png',
        'fipe': soup.select_one("table.fipe-mobile tr:nth-child(1) td").get_text(strip=True).replace('FIPE: ', '') if soup.select_one("table.fipe-mobile tr:nth-child(1) td") else 'Desconhecido'
    }

    return json.dumps(data, ensure_ascii=False, indent=4, separators=(',', ': '))

# Exibir o banner no início
exibir_banner()

# Solicitar a placa do usuário
placa = input('qual placa deseja consultar?: ')

# Consultar os dados da placa e exibir o resultado
print(bruxovaisefoder(placa))