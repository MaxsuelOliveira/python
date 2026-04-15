import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

URL_SEFAZ = os.getenv("URL_SEFAZ")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

status_map = {
    "bola_verde_P": "OK",
    "bola_amarela_P": "Instável",
    "bola_vermelha_P": "Indisponível"
}

def enviar_telegram(mensagem: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

def obter_status():
    headers = {
        "accept-language": "pt-BR,pt;q=0.9",
        "Referer": URL_SEFAZ,
        "cookie": "AspxAutoDetectCookieSupport=1"
    }

    res = requests.get(URL_SEFAZ, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    tabela = soup.find("table", class_="tabelaListagemDados")
    if not tabela:
        return {}

    raw_headers = [th.get_text(strip=True) for th in tabela.find_all("tr")[0].find_all("th")]
    headers = raw_headers[1:]

    resultado = {}
    for row in tabela.find_all("tr")[1:]:
        cols = row.find_all("td")
        if not cols:
            continue
        estado = cols[0].get_text(strip=True)
        valores = []
        for col in cols[1:]:
            img = col.find("img")
            if img:
                nome = img['src'].split("/")[-1].replace(".png", "")
                valor = status_map.get(nome, "Desconhecido")
            else:
                valor = col.get_text(strip=True) or "-"
            valores.append(valor)
        resultado[estado] = dict(zip(headers, valores))
    return resultado

def monitorar():
    status = obter_status()
    indisponiveis = []

    for estado, servicos in status.items():
        for servico, situacao in servicos.items():
            if situacao == "Indisponível":
                indisponiveis.append(f"{estado} - {servico}")

    if indisponiveis:
        mensagem = "<b>🚨 SERVIÇOS INDISPONÍVEIS DETECTADOS</b>\n\n"
        mensagem += "\n".join(f"❌ {item}" for item in indisponiveis)
        enviar_telegram(mensagem)
    else:
        print("✔️ MONITOR SEFAZ - ONLINE.")

