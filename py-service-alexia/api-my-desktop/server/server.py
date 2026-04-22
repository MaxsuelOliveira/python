import time
import json
import asyncio
from urllib import response
import websockets

import os
import sys
import socket


async def hello(websocket):

    # Mensagem que foi recebida pelo cliente.
    data = await websocket.recv()
    function = json.loads(data)['function']
    print(function)

    # Mensagem para o cliente
    logs = f'"estamo execultando a função {function}"'
    # await websocket.send(greeting)

    match function:
        case "tempo":
            tempo = str(time.time())
            response = '{ "resultado" : ' + tempo + ', "logs" : ' + logs + '}'
            await websocket.send(response)

        case "clima":
            os.system("start spotify.exe")

        case "rede":

            ipAddress = socket.gethostbyname(socket.gethostname())
            print(ipAddress)

            for ports in range(1, 65535):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                if s.connect_ex((ipAddress, ports)) == 0:
                    print(f"Porta {ports} Aberta!")
                    # await websocket.send(response)
                    s.close()

        case _:
            print("Não foi informado nenhuma função")

# Alguem se conectou ao websocekt


async def main():
    async with websockets.serve(hello, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
