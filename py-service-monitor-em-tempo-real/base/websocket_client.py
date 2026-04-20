"""Cliente WebSocket simples para enviar notificações JSON.
"""
import asyncio
import json
from typing import Any

import websockets


async def _send(ws_url: str, message: Any):
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps(message))


def send_notification(ws_url: str, message: Any, timeout: float = 5.0):
    """Envia a mensagem assincronamente para o WebSocket.

    Bloqueia até conclusão (usa asyncio.run internamente).
    """
    try:
        asyncio.run(asyncio.wait_for(_send(ws_url, message), timeout=timeout))
    except Exception:
        # Repasse a exceção para o chamador lidar (ex: host indisponível)
        raise
