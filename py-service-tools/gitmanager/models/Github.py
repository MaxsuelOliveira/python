import subprocess

class Github:
    def criar_repositorio(self, nome, publico=True):
        flag = "--public" if publico else "--private"
        os.system(f"gh repo create {nome} {flag} --confirm")

    def repositorio_existe(self, nome):
        try:
            subprocess.check_output(f'gh repo view MaxsuelDavid/{nome} --json name --jq ".name"', shell=True)
            return True
        except:
            return False

    def obter_url(self, nome):
        return f"https://github.com/MaxsuelDavid/{nome}.git"
