import os

def listar_arquivos(diretorio):
    return os.listdir(diretorio)

def carregar_env():
    try:
        with open(".env", "r") as f:
            for linha in f:
                if "VISIBILIDADE=" in linha:
                    return linha.strip().split("=")[1].lower()
    except:
        pass
    return "private"  # padrão
