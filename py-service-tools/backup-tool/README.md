# 🗂️ Backup Tool (unificado)

Ferramenta unificada para backups locais e compactação. Combina funcionalidades dos projetos de backup anteriores em uma única CLI.

---

## ✅ Funcionalidades

- 📦 Copia arquivos/pastas para um diretório temporário
- 🗜️ Compacta em ZIP com timestamp
- 🔁 Suporta `--dry-run` (simulação) e `--remove` (apagar origem)
- ☁️ Stub para upload S3 (opcional)

---

## ⚙️ Requisitos

- Python 3.7+
- Dependências:

```bash
pip install -r requirements.txt
```

## 🚀 Como usar

```powershell
python main.py --source C:\meus_arquivos --target ./temp --zip-dir ./backup --zip-name meus_backup
```

Testar em modo simulação:

```powershell
python main.py --source C:\meus_arquivos --dry-run
```

---

## 🧩 Observações

- Para upload real ao S3 instale `boto3` e configure credenciais via variáveis de ambiente.
- Adicione testes e CI conforme necessário.
