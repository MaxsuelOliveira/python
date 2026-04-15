import asyncio
import websockets
import json


async def handler(websocket, path):
    async for message in websocket:
        # print(f"Received message: {message}")
        print(json.loads(message)['message'])
        await websocket.send(f"Conectado com sucesso !")

start_server = websockets.serve(handler, 'localhost', 8765)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
