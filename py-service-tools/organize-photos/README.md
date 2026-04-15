# 🗂️ Organizador de Imagens e Vídeos por Data com Python

Este script organiza automaticamente **imagens** e **vídeos** da pasta `upload/` em pastas separadas por **ano, mês e semana**, com base na **data original de criação** dos arquivos.

---

## ✅ Funcionalidades

- 📸 Extrai data de imagens via **EXIF** (`DateTimeOriginal`)
- 🎥 Extrai data de vídeos via **ffprobe** (`creation_time`)
- 🗃️ Cria estrutura: `files_YYYYMMDD_HHMM/ano-mes/semana-XX/`
- ❌ Arquivos sem data são movidos para: `files_YYYYMMDD_HHMM/SEM-DATA/`
- 🔒 Gera nova pasta com timestamp para não sobrescrever resultados anteriores

---

## ⚙️ Requisitos

- Python 3.7+
- Dependências:

```bash
pip install Pillow
ffprobe (vem com ffmpeg)
```

## Instalação do ffmpeg

### Linux

```bash
sudo apt install ffmpeg
```

### Windows

```bash
choco install ffmpeg
```

## 🚀 Como usar

1. Coloque seus arquivos em:
./upload/

2. Execute o script:
python main.py

Os arquivos serão organizados em uma nova pasta com timestamp, como:

files_20250622_0215/
    ├── 2025-06/
    │   └── semana-25/
    │       ├── foto1.jpg
    │       └── video1.mp4
    └── SEM-DATA/
        └── arquivo_sem_data.png

## 🧩 Suporte a formatos

Tipo Extensões
Imagens .jpg, .jpeg, .png
Vídeos .mp4, .mov, .avi, .mkv

## 📌 Observações

Arquivos sem data válida são enviados para SEM-DATA/
