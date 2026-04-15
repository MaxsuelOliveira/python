import os
import subprocess

class Git:
    def inicializado(self):
        return os.path.isdir(".git")

    def iniciar(self):
        os.system("git init")

    def adicionar_arquivos(self):
        os.system("git add *")

    def commitar(self, mensagem):
        os.system(f'git commit -m "{mensagem}"')

    def criar_branch(self, nome):
        os.system(f"git branch -M {nome}")

    def adicionar_remoto(self, url):
        os.system(f"git remote add origin {url}")

    def enviar(self):
        os.system("git push -u origin main")

    def tem_modificacoes(self):
        try:
            output = subprocess.check_output("git status --porcelain", shell=True).decode('utf-8').strip()
            return bool(output)
        except:
            return False

    def tem_tracking(self):
        try:
            subprocess.check_output("git rev-parse --abbrev-ref --symbolic-full-name @{u}", shell=True)
            return True
        except:
            return False

    def configurar_tracking(self):
        os.system("git branch --set-upstream-to=origin/main main")
