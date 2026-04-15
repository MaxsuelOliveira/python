import os

BASE_PATH = "src"

MODULES = {
    "system": [],
    "company": [],
    "identity": [],
    "billing": [],
    "messaging": [],
    "conversation": [],
    "automation": [],
    "reporting": [],
}

MODULE_STRUCTURE = [
    "controllers",
    "services",
    "models",
    "repositories",
    "lib",
]

SHARED_STRUCTURE = [
    "errors",
    "logger",
    "utils",
    "constants",
]

INFRA_STRUCTURE = {
    "database": [
        "prisma",
        "repositories",
    ],
    "providers": [
        "whatsapp",
        "payment",
    ],
    "http": [],
}

TESTS_STRUCTURE = [
    "unit",
    "integration",
]


def create_folder(path):
    os.makedirs(path, exist_ok=True)
    print(f"📁 Criado: {path}")


def create_file(path, filename):
    full_path = os.path.join(path, filename)
    if not os.path.exists(full_path):
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(f"// {filename}\n")
            f.write("// Arquivo gerado automaticamente\n")
        print(f"📄 Criado: {full_path}")


def create_module(module_name):
    module_path = os.path.join(BASE_PATH, "modules", module_name)
    create_folder(module_path)

    for folder in MODULE_STRUCTURE:
        folder_path = os.path.join(module_path, folder)
        create_folder(folder_path)
        create_file(folder_path, "index.js")

    create_file(module_path, "index.js")


def create_shared():
    shared_path = os.path.join(BASE_PATH, "shared")
    create_folder(shared_path)

    for folder in SHARED_STRUCTURE:
        folder_path = os.path.join(shared_path, folder)
        create_folder(folder_path)
        create_file(folder_path, "index.js")


def create_infra():
    infra_path = os.path.join(BASE_PATH, "infra")
    create_folder(infra_path)

    for parent, children in INFRA_STRUCTURE.items():
        parent_path = os.path.join(infra_path, parent)
        create_folder(parent_path)

        for child in children:
            child_path = os.path.join(parent_path, child)
            create_folder(child_path)
            create_file(child_path, "index.js")

        create_file(parent_path, "index.js")


def create_tests():
    tests_path = os.path.join(BASE_PATH, "tests")
    create_folder(tests_path)

    for folder in TESTS_STRUCTURE:
        folder_path = os.path.join(tests_path, folder)
        create_folder(folder_path)


def main():
    print("🚀 Criando arquitetura MVC modular...")

    create_folder(BASE_PATH)
    create_folder(os.path.join(BASE_PATH, "modules"))

    for module in MODULES:
        create_module(module)

    create_shared()
    create_infra()
    create_tests()

    create_file(BASE_PATH, "server.js")

    print("✅ Estrutura MVC criada com sucesso!")


if __name__ == "__main__":
    main()
