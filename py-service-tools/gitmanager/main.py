from app.controllers.RepoController import processar_repositorios

if __name__ == "__main__":
    try:
        processar_repositorios()
    except Exception as e:
        print('[❌] Erro geral ao processar repositórios:', e)