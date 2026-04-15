import os
import shutil

# Pasta raiz (onde o script será executado)
ROOT_DIR = os.getcwd()

for root, dirs, files in os.walk(ROOT_DIR):
    # ignora a própria raiz
    if root == ROOT_DIR:
        continue

    for file in files:
        source_path = os.path.join(root, file)
        dest_path = os.path.join(ROOT_DIR, file)

        # evita sobrescrever arquivos com o mesmo nome
        if os.path.exists(dest_path):
            name, ext = os.path.splitext(file)
            counter = 1

            while True:
                new_name = f"{name}_{counter}{ext}"
                new_dest = os.path.join(ROOT_DIR, new_name)
                if not os.path.exists(new_dest):
                    dest_path = new_dest
                    break
                counter += 1

        shutil.move(source_path, dest_path)
        print(f"Movido: {source_path} → {dest_path}")

def remove_empty_dirs(root_dir):
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        # ignora a raiz
        if dirpath == root_dir:
            continue
        if not os.listdir(dirpath):
            os.rmdir(dirpath)
            print(f"Pasta vazia removida: {dirpath}")

remove_empty_dirs(ROOT_DIR)
print("\n✅ Completo! Todos os arquivos foram movidos para a pasta raiz e pastas vazias removidas.")