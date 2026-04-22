import asyncio
import tkinter as tk
from tkinter import messagebox, colorchooser
from bleak import BleakScanner, BleakClient

selected_device_address = None
connected_client = None
CHAR_UUID = None

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

def log(msg):
    print(f"[LOG] {msg}")

def set_botoes_estado(conectado=False):
    btn_escaneamento.config(state=tk.NORMAL if not conectado else tk.DISABLED)
    btn_conectar.config(state=tk.NORMAL if not conectado else tk.DISABLED)
    btn_desconectar.config(state=tk.NORMAL if conectado else tk.DISABLED)
    btn_cor.config(state=tk.NORMAL if conectado else tk.DISABLED)

def iniciar_escaneamento():
    lista_dispositivos.delete(0, tk.END)

    async def escanear():
        try:
            dispositivos = await BleakScanner.discover(timeout=5)
            if not dispositivos:
                messagebox.showinfo("BLE", "Nenhum dispositivo BLE encontrado.")
                return
            for d in dispositivos:
                lista_dispositivos.insert(tk.END, f"{d.name or 'Desconhecido'} | {d.address}")
            log(f"{len(dispositivos)} dispositivos encontrados.")
        except Exception as e:
            messagebox.showerror("Erro de escaneamento", str(e))

    loop.create_task(escanear())

def conectar_dispositivo():
    global selected_device_address, connected_client, CHAR_UUID


    selecao = lista_dispositivos.curselection()
    if not selecao:
        messagebox.showwarning("Aviso", "Selecione um dispositivo na lista.")
        return

    selected_line = lista_dispositivos.get(selecao[0])
    selected_device_address = selected_line.split("|")[1].strip()

    async def conectar():

        # if client.is_connected:
        #     await client.disconnect()


        global connected_client, CHAR_UUID
        try:
            log(f"Tentando conectar ao dispositivo {selected_device_address} ...")

            if connected_client and connected_client.is_connected:
                await connected_client.disconnect()
                log("Desconectado do cliente anterior.")

            client = BleakClient(selected_device_address)
            # Timeout para evitar travar indefinidamente
            await asyncio.wait_for(client.connect(), timeout=10.0)

            if await client.is_connected():
                connected_client = client
                log("Conectado com sucesso!")

                services = await connected_client.get_services()
                CHAR_UUID = None
                for service in services:
                    for char in service.characteristics:
                        # Procurar característica com permissão de escrita
                        if "write" in char.properties or "write-without-response" in char.properties:
                            CHAR_UUID = char.uuid
                            log(f"Encontrado UUID para escrita: {CHAR_UUID}")
                            break
                    if CHAR_UUID:
                        break

                if CHAR_UUID:
                    messagebox.showinfo("Conectado", f"Conectado ao dispositivo {selected_device_address}\nUUID para escrita: {CHAR_UUID}")
                else:
                    messagebox.showwarning("Conectado", "Dispositivo conectado, mas nenhuma característica de escrita foi encontrada.")

                set_botoes_estado(conectado=True)
            else:
                messagebox.showerror("Erro", "Não foi possível conectar ao dispositivo.")
                set_botoes_estado(conectado=False)

        except asyncio.TimeoutError:
            messagebox.showerror("Timeout", "Tempo esgotado ao tentar conectar. Tente novamente.")
            log("Timeout na conexão.")
            set_botoes_estado(conectado=False)
        except Exception as e:
            messagebox.showerror("Erro de conexão", str(e))
            log(f"Erro de conexão: {e}")
            set_botoes_estado(conectado=False)

    loop.create_task(conectar())

def desconectar_dispositivo():
    global connected_client, CHAR_UUID, selected_device_address
    async def desconectar():
        global connected_client, CHAR_UUID, selected_device_address
        if connected_client and connected_client.is_connected:
            await connected_client.disconnect()
            log(f"Desconectado do dispositivo {selected_device_address}")
            connected_client = None
            CHAR_UUID = None
            selected_device_address = None
            set_botoes_estado(conectado=False)
            label_cor.config(text="Nenhuma cor selecionada", bg="white")
        else:
            messagebox.showinfo("Desconectar", "Nenhum dispositivo conectado.")

    loop.create_task(desconectar())

def escolher_cor():
    if not connected_client or not CHAR_UUID:
        messagebox.showerror("Erro", "Conecte-se a um dispositivo antes de escolher a cor.")
        return

    cor = colorchooser.askcolor()[0]
    if not cor:
        return

    r, g, b = map(int, cor)
    label_cor.config(text=f"Cor RGB: {r}, {g}, {b}", bg=f'#{r:02x}{g:02x}{b:02x}')

    # Montar pacote para envio (exemplo)
    pacote = bytes([0x7E, 0x00, 0x05, 0x03, r, g, b, 0xEF])

    async def enviar_cor():
        try:
            await connected_client.write_gatt_char(CHAR_UUID, pacote, response=False)
            log(f"Pacote enviado: {pacote}")
        except Exception as e:
            messagebox.showerror("Erro ao enviar cor", str(e))
            log(f"Erro ao enviar cor: {e}")

    loop.create_task(enviar_cor())


# GUI
janela = tk.Tk()
janela.title("Controle BLE - Fita LED RGB")
janela.geometry("400x450")

tk.Label(janela, text="Dispositivos BLE encontrados:").pack(pady=5)
lista_dispositivos = tk.Listbox(janela, width=50, height=10)
lista_dispositivos.pack(pady=5)

btn_escaneamento = tk.Button(janela, text="Escanear BLE", command=iniciar_escaneamento)
btn_escaneamento.pack(pady=5)

btn_conectar = tk.Button(janela, text="Conectar ao Dispositivo", command=conectar_dispositivo)
btn_conectar.pack(pady=5)

btn_desconectar = tk.Button(janela, text="Desconectar", command=desconectar_dispositivo, state=tk.DISABLED)
btn_desconectar.pack(pady=5)

btn_cor = tk.Button(janela, text="Escolher Cor RGB", command=escolher_cor, state=tk.DISABLED)
btn_cor.pack(pady=10)

label_cor = tk.Label(janela, text="Nenhuma cor selecionada", bg="white", font=("Arial", 12), width=30)
label_cor.pack(pady=20)

# Loop do asyncio integrado com tkinter
def processar_eventos():
    loop.call_soon(loop.stop)
    loop.run_forever()
    janela.after(100, processar_eventos)

janela.after(100, processar_eventos)
janela.mainloop()
