import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from PIL import Image, ExifTags

# === CONFIGURAÇÕES ===
PASTA_ORIGEM = './upload'
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
PASTA_DESTINO = f'./files_{TIMESTAMP}'
PASTA_SEM_DATA = os.path.join(PASTA_DESTINO, 'SEM-DATA')

EXTENSOES_IMAGEM = ['.jpg', '.jpeg', '.png']
EXTENSOES_VIDEO = ['.mp4', '.mov', '.avi', '.mkv']


def extrair_data_exif_imagem(caminho):
    try:
        img = Image.open(caminho)
        exif = img._getexif()
        if not exif:
            return None
        for tag_id, valor in exif.items():
            tag = ExifTags.TAGS.get(tag_id)
            if tag == 'DateTimeOriginal':
                return datetime.strptime(valor, '%Y:%m:%d %H:%M:%S')
    except:
        pass
    return None


def extrair_data_video_ffprobe(caminho):
    try:
        comando = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format_tags=creation_time",
            "-of", "default=noprint_wrappers=1:nokey=0",
            caminho
        ]
        resultado = subprocess.run(comando, capture_output=True, text=True)
        for linha in resultado.stdout.splitlines():
            if "creation_time" in linha:
                data_str = linha.split('=')[1].strip()
                return datetime.fromisoformat(data_str.replace('Z', '+00:00')).astimezone()
    except:
        pass
    return None


def organizar_arquivos_por_data():
    print(f"🗂️  Organizando arquivos de: {PASTA_ORIGEM}")
    print(f"📁 Saída: {PASTA_DESTINO}\n")

    total_organizados = 0
    total_sem_data = 0

    for root, _, files in os.walk(PASTA_ORIGEM):
        for nome in files:
            caminho = os.path.join(root, nome)
            extensao = Path(nome).suffix.lower()

            data = None
            if extensao in EXTENSOES_IMAGEM:
                data = extrair_data_exif_imagem(caminho)
            elif extensao in EXTENSOES_VIDEO:
                data = extrair_data_video_ffprobe(caminho)

            if data:
                ano_mes = data.strftime('%Y-%m')
                semana = f"semana-{data.isocalendar().week:02d}"
                destino = os.path.join(PASTA_DESTINO, ano_mes, semana)
            else:
                destino = PASTA_SEM_DATA
                total_sem_data += 1

            os.makedirs(destino, exist_ok=True)
            destino_final = os.path.join(destino, nome)

            shutil.move(caminho, destino_final)
            print(f"[✔] {nome} → {destino_final}")
            total_organizados += 1

    print(f"\n✅ Total movidos: {total_organizados}")
    print(f"⚠️  Arquivos sem data: {total_sem_data}")
    print(f"📦 Tudo organizado em: {PASTA_DESTINO}")


if __name__ == '__main__':
    organizar_arquivos_por_data()
