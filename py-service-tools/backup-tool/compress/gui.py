import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import os
from backup_tool.compress.functions import create_archive_parallel, create_archive, extract_archive


class App:
    def __init__(self, root):
        self.root = root
        root.title('Compactador — GUI simples')

        tk.Label(root, text='Origem (arquivo ou pasta)').grid(row=0, column=0, sticky='w')
        self.src_entry = tk.Entry(root, width=60)
        self.src_entry.grid(row=0, column=1)
        tk.Button(root, text='Selecionar', command=self.select_src).grid(row=0, column=2)

        tk.Label(root, text='Formato').grid(row=1, column=0, sticky='w')
        self.format_var = tk.StringVar(value='xz')
        tk.OptionMenu(root, self.format_var, 'xz', 'gz', 'zip').grid(row=1, column=1, sticky='w')

        tk.Label(root, text='Nível (0-9)').grid(row=2, column=0, sticky='w')
        self.level_entry = tk.Entry(root, width=5)
        self.level_entry.insert(0, '9')
        self.level_entry.grid(row=2, column=1, sticky='w')

        tk.Button(root, text='Compactar (multithread quando possível)', command=self.compress).grid(row=3, column=0)
        tk.Button(root, text='Extrair', command=self.extract).grid(row=3, column=1)

        self.log = scrolledtext.ScrolledText(root, width=80, height=20)
        self.log.grid(row=4, column=0, columnspan=3)

    def select_src(self):
        path = filedialog.askopenfilename() or filedialog.askdirectory()
        if path:
            self.src_entry.delete(0, tk.END)
            self.src_entry.insert(0, path)

    def _log(self, msg):
        self.log.insert(tk.END, msg + '\n')
        self.log.see(tk.END)

    def compress(self):
        src = self.src_entry.get().strip()
        if not src:
            messagebox.showwarning('Aviso', 'Selecione um arquivo ou pasta')
            return
        fmt = self.format_var.get()
        try:
            level = int(self.level_entry.get())
        except ValueError:
            level = 9

        def job():
            try:
                self._log(f'Iniciando compactação de {src} format={fmt} level={level}')
                out = create_archive_parallel(src, fmt=fmt, compress_level=level)
                self._log(f'Criado: {out}')
            except Exception as e:
                self._log(f'Erro: {e}')

        threading.Thread(target=job, daemon=True).start()

    def extract(self):
        src = self.src_entry.get().strip()
        if not src:
            messagebox.showwarning('Aviso', 'Selecione um arquivo para extrair')
            return
        dest = filedialog.askdirectory()
        if not dest:
            return

        def job():
            try:
                self._log(f'Extraindo {src} para {dest}')
                out = extract_archive(src, dest_dir=dest)
                self._log(f'Extraído para: {out}')
            except Exception as e:
                self._log(f'Erro: {e}')

        threading.Thread(target=job, daemon=True).start()


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
