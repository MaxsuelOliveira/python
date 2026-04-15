import asyncio
import tkinter as tk
from tkinter import messagebox, colorchooser
from bleak import BleakScanner, BleakClient

CHAR_UUIDS = ["0000fff3-0000-1000-8000-00805f9b34fb", "0000fff4-0000-1000-8000-00805f9b34fb"]

class BLEControllerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Controle BLE - Fita LED RGB")
        self.root.geometry("400x450")

        self.selected_device_address = None

        tk.Label(root, text="Dispositivos BLE encontrados:").pack(pady=5)
        self.lista_dispositivos = tk.Listbox(root, width=50, height=10)
        self.lista_dispositivos.pack(pady=5)

        tk.Button(root, text="Escanear BLE", command=self.escaneia).pack(pady=5)
        tk.Button(root, text="Conectar ao Dispositivo", command=self.conectar).pack(pady=5)
        tk.Button(root, text="Escolher Cor RGB", command=self.escolher_cor).pack(pady=10)

        self.label_cor = tk.Label(root, text="Nenhuma cor selecionada", bg="white", font=("Arial", 12), width=30)
        self.label_cor.pack(pady=20)

    def escaneia(self):
        self.lista_dispositivos.delete(0, tk.END)
        asyncio.create_task(self._escaneia_async())

    async def _escaneia_async(self):
        try:
            dispositivos = await BleakScanner.discover(timeout=5.0)
            if not dispositivos:
                messagebox.showinfo("BLE", "Nenhum dispositivo BLE encontrado.")
            for d in dispositivos:
                nome = d.name if d.name else "Desconhecido"
                self.lista_dispositivos.insert(tk.END, f"{nome} | {d.address}")
        except Exception as e:
            messagebox.showerror("Erro de escaneamento", str(e))

    def conectar(self):
        selecao = self.lista_dispositivos.curselection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um dispositivo na lista.")
            return
        linha = self.lista_dispositivos.get(selecao[0])
        self.selected_device_address = linha.split("|")[1].strip()
        asyncio.create_task(self._conectar_async())

    async def _conectar_async(self):
        try:
            async with BleakClient(self.selected_device_address) as client:
                conectado = await client.is_connected()
                if conectado:
                    messagebox.showinfo("Conectado", f"Conectado ao dispositivo:\n{self.selected_device_address}")
                else:
                    messagebox.showerror("Erro", "Não foi possível conectar.")
        except Exception as e:
            messagebox.showerror("Erro de conexão", str(e))

    def escolher_cor(self):
        if not self.selected_device_address:
            messagebox.showerror("Erro", "Conecte-se a um dispositivo primeiro.")
            return
        cor = colorchooser.askcolor()[0]
        if not cor:
            return

        r, g, b = map(int, cor)
        self.label_cor.config(text=f"Cor RGB: {r}, {g}, {b}", bg=f'#{r:02x}{g:02x}{b:02x}')

        pacote = bytes([0x7E, 0x00, 0x05, 0x03, r, g, b, 0xEF])

        asyncio.create_task(self._enviar_cor_async(pacote))

    async def _enviar_cor_async(self, pacote):
        try:
            async with BleakClient(self.selected_device_address) as client:
                for uuid in CHAR_UUIDS:
                    await client.write_gatt_char(uuid, pacote, response=False)
                    print(f"Enviado pacote para {uuid}: {pacote}")
                messagebox.showinfo("Sucesso", "Cor enviada para a fita LED.")
        except Exception as e:
            messagebox.showerror("Erro ao enviar cor", str(e))

def main():
    root = tk.Tk()

    # Configurar o loop asyncio para rodar junto com o Tkinter no Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    app = BLEControllerApp(root)

    # Rodar o loop de eventos do Tkinter
    async def tk_loop():
        while True:
            try:
                root.update()
            except tk.TclError:
                break
            await asyncio.sleep(0.01)

    asyncio.run(tk_loop())

if __name__ == "__main__":
    main()
