import asyncio
import websockets

async def receber_mensagem(websocket, path):
    async for mensagem in websocket:
        print(f"Cliente disse: {mensagem}")
        resposta = input("Digite a resposta: ")
        await websocket.send(resposta)

asyncio.get_event_loop().run_until_complete(websockets.serve(receber_mensagem, 'localhost', 5000))
asyncio.get_event_loop().run_forever()