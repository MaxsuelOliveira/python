import os
from app.models.Git import Git
from app.models.Github import Github
from app.services.Utils import listar_arquivos, carregar_env
from app.views.ConsoleView import exibir_mensagem

def processar_repositorios():
    visibilidade = carregar_env()

    for pasta in listar_arquivos('./'):
        if os.path.isdir(pasta):
            exibir_mensagem(f"\n📦 Processando: {pasta}")
            os.chdir(pasta)

            git = Git()
            github = Github()

            if not git.inicializado():
                git.iniciar()

            if git.tem_modificacoes():
                git.adicionar_arquivos()
                git.commitar("first commit")
                git.criar_branch("main")

                if not github.repositorio_existe(pasta):
                    if visibilidade == "public":
                        github.criar_repositorio(pasta, publico=True)
                    else:
                        github.criar_repositorio(pasta, publico=False)

                url = github.obter_url(pasta)
                git.adicionar_remoto(url)

                if not git.tem_tracking():
                    git.configurar_tracking()

                git.enviar()
            else:
                exibir_mensagem("🟡 Nenhuma modificação para comitar.")

            os.chdir('..')
