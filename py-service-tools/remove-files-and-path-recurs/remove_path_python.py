import os
import shutil
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# =========================
# CONFIGURAÇÃO
# =========================

ROOT_DIR = r"F:\Development"  # ALTERE AQUI
MAX_WORKERS = (os.cpu_count() or 1) * 2
TARGET_FOLDER_NAME = "node_modules"

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
LOG_FILE = f"cleanup_node_modules_{TIMESTAMP}.log"
JSON_REPORT_FILE = f"cleanup_node_modules_{TIMESTAMP}.json"

# Diretórios ignorados (Windows)
SYSTEM_DIRS = {
    "Windows",
    "Program Files",
    "Program Files (x86)",
    "ProgramData",
    "$Recycle.Bin",
    "System Volume Information",
}

# =========================
# LOG SETUP
# =========================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# =========================
# CONTROLE DE CONCORRÊNCIA
# =========================

lock = Lock()

report_data = {
    "start_time": datetime.now().isoformat(),
    "root_directory": ROOT_DIR,
    "scanned_directories": [],
    "removed_directories": [],
    "errors": [],
}

# =========================
# FUNÇÕES
# =========================

def should_ignore(path):
    parts = set(path.split(os.sep))
    return bool(parts.intersection(SYSTEM_DIRS))


def remove_folder(path):
    try:
        shutil.rmtree(path)
        with lock:
            report_data["removed_directories"].append(path)
        logging.info(f"REMOVIDO: {path}")
    except Exception as e:
        with lock:
            report_data["errors"].append({"path": path, "error": str(e)})
        logging.error(f"ERRO ao remover {path}: {e}")


def scan_and_collect(root_path):
    targets = []

    for dirpath, dirnames, _ in os.walk(root_path):
        if should_ignore(dirpath):
            continue

        with lock:
            report_data["scanned_directories"].append(dirpath)

        if TARGET_FOLDER_NAME in dirnames:
            full_path = os.path.join(dirpath, TARGET_FOLDER_NAME)
            targets.append(full_path)

    return targets


# =========================
# EXECUÇÃO
# =========================

if __name__ == "__main__":
    print("ATENÇÃO: Todas as pastas 'node_modules' serão removidas.")
    confirm = input("Deseja continuar? (s/n): ")

    if confirm.lower() != "s":
        print("Operação cancelada.")
        exit()

    logging.info("=== INÍCIO DA EXECUÇÃO ===")

    print("Escaneando diretórios...")
    targets = scan_and_collect(ROOT_DIR)

    print(f"{len(targets)} pastas encontradas. Iniciando remoção paralela...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(remove_folder, path) for path in targets]

        for _ in as_completed(futures):
            pass

    report_data["end_time"] = datetime.now().isoformat()
    report_data["total_scanned"] = len(report_data["scanned_directories"])
    report_data["total_removed"] = len(report_data["removed_directories"])
    report_data["total_errors"] = len(report_data["errors"])

    logging.info("=== FIM DA EXECUÇÃO ===")
    logging.info(f"Total varrido: {report_data['total_scanned']}")
    logging.info(f"Total removido: {report_data['total_removed']}")

    # Gerar JSON
    with open(JSON_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4, ensure_ascii=False)

    print("Processo concluído.")
    print(f"Log: {LOG_FILE}")
    print(f"Relatório JSON: {JSON_REPORT_FILE}")