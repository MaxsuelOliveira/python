import requests
from datetime import datetime, timezone

from bs4 import BeautifulSoup

status_map = {
    "bola_verde_P": "OK",
    "bola_amarela_P": "Instável",
    "bola_vermelha_P": "Indisponível"
}

def enviar_telegram(mensagem: str, telegram_token: str, telegram_chat_id: str, timeout_seconds: int):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {
        "chat_id": telegram_chat_id,
        "text": mensagem,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload, timeout=timeout_seconds)
    response.raise_for_status()
    return response


def montar_payload_webhook(indisponiveis, status):
    mensagem = montar_mensagem_alerta(indisponiveis)
    return {
        "event": "sefaz_alert",
        "source": "py-service-monitor-sefaz",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "message": mensagem,
            "indisponiveis_count": len(indisponiveis),
        },
        "indisponiveis": indisponiveis,
        "status": status,
    }


def enviar_webhook(webhook_url: str, payload: dict, timeout_seconds: int):
    response = requests.post(webhook_url, json=payload, timeout=timeout_seconds)
    response.raise_for_status()
    return response

def obter_status(url_sefaz: str, timeout_seconds: int):
    headers = {
        "accept-language": "pt-BR,pt;q=0.9",
        "Referer": url_sefaz,
        "cookie": "AspxAutoDetectCookieSupport=1"
    }

    res = requests.get(url_sefaz, headers=headers, timeout=timeout_seconds)
    res.raise_for_status()
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

def construir_indisponibilidades(status):
    indisponiveis = []

    for estado, servicos in status.items():
        for servico, situacao in servicos.items():
            if situacao == "Indisponível":
                indisponiveis.append(f"{estado} - {servico}")

    return indisponiveis

def montar_mensagem_alerta(indisponiveis):
    mensagem = "<b>🚨 SERVIÇOS INDISPONÍVEIS DETECTADOS</b>\n\n"
    mensagem += "\n".join(f"❌ {item}" for item in indisponiveis)
    return mensagem

def monitorar(config: dict):
    status = obter_status(config["url_sefaz"], config["request_timeout_seconds"])
    indisponiveis = construir_indisponibilidades(status)

    if indisponiveis:
        mensagem_alerta = montar_mensagem_alerta(indisponiveis)
        payload_webhook = montar_payload_webhook(indisponiveis, status)
        deliveries = []

        if config["telegram_enabled"] and config["telegram_token"] and config["telegram_chat_id"]:
            try:
                response = enviar_telegram(
                    mensagem_alerta,
                    config["telegram_token"],
                    config["telegram_chat_id"],
                    config["request_timeout_seconds"],
                )
                deliveries.append(
                    {
                        "channel": "telegram",
                        "destination": config["telegram_chat_id"],
                        "success": True,
                        "response_status": response.status_code,
                        "error_message": None,
                        "indisponiveis_count": len(indisponiveis),
                        "payload": {
                            "message": mensagem_alerta,
                            "chat_id": config["telegram_chat_id"],
                        },
                    }
                )
            except Exception as exc:
                deliveries.append(
                    {
                        "channel": "telegram",
                        "destination": config["telegram_chat_id"],
                        "success": False,
                        "response_status": None,
                        "error_message": str(exc),
                        "indisponiveis_count": len(indisponiveis),
                        "payload": {
                            "message": mensagem_alerta,
                            "chat_id": config["telegram_chat_id"],
                        },
                    }
                )

        if config.get("webhook_enabled") and config.get("webhook_url"):
            try:
                response = enviar_webhook(
                    config["webhook_url"],
                    payload_webhook,
                    config["request_timeout_seconds"],
                )
                deliveries.append(
                    {
                        "channel": "webhook",
                        "destination": config["webhook_url"],
                        "success": True,
                        "response_status": response.status_code,
                        "error_message": None,
                        "indisponiveis_count": len(indisponiveis),
                        "payload": payload_webhook,
                    }
                )
            except Exception as exc:
                deliveries.append(
                    {
                        "channel": "webhook",
                        "destination": config["webhook_url"],
                        "success": False,
                        "response_status": None,
                        "error_message": str(exc),
                        "indisponiveis_count": len(indisponiveis),
                        "payload": payload_webhook,
                    }
                )

        return {
            "ok": True,
            "status": status,
            "indisponiveis": indisponiveis,
            "message": f"{len(indisponiveis)} indisponibilidade(s) encontrada(s).",
            "deliveries": deliveries,
        }

    return {
        "ok": True,
        "status": status,
        "indisponiveis": [],
        "message": "Monitor SEFAZ online.",
        "deliveries": [],
    }

