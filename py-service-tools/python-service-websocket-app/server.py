import asyncio
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

clients = set()

async def handler(websocket, path):
    clients.add(websocket)
    print("Cliente conectado!")
    try:
        async for message in websocket:
            # Reenvia o vídeo e áudio para todos os clientes conectados
            for client in clients:
                if client != websocket:
                    try:
                        await client.send(message)
                    except (ConnectionClosedError, ConnectionClosedOK):
                        clients.remove(client)
    except (ConnectionClosedError, ConnectionClosedOK):
        print("Cliente desconectado!")
    finally:
        clients.remove(websocket)

async def main():
    async with websockets.serve(handler, "192.168.3.19", 8765):
        print("Servidor WebSocket escutando em ws://192.168.3.19:8765/")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
