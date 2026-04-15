# 🗂️ Organize Files

Script para organizar arquivos por extensão ou por data (modificação).

---

## ✅ Funcionalidades

- 📁 Organiza por extensão (ex: `txt`, `jpg`)
- 🗓️ Organiza por data de modificação (mês ou dia)
- 🔁 Suporta mover ou copiar, e `--dry-run` para simular

---

## ⚙️ Requisitos

- Python 3.7+
- Dependências: `pytest` (para testes), `Pillow` opcional para EXIF

## 🚀 Como usar

```powershell
python main.py --source C:\minha_pasta --dest C:\saida --mode extension
```

Exemplos adicionais e testes estão no repositório.

---

## 🧩 Observações

- Use `--dry-run` para verificar sem mover arquivos.
