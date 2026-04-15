# 🗂️ Visualizador Markdown com Live Reload

Este mini-projeto executa um servidor Flask que renderiza um arquivo Markdown (`MAX.md`) e usa livereload para atualizar a página automaticamente quando o arquivo é alterado.
Meu objetivo é criar sites usando o Markdown é compilar em html e css.

---

## ✅ Funcionalidades

- 🔁 Live reload ao editar o arquivo Markdown
- 🌐 Servidor Flask simples para visualização local

---

## ⚙️ Requisitos

- Python 3.7+
- Dependências:

```bash
pip install Flask livereload markdown
```

## 🚀 Como usar

1. Coloque seu arquivo `MAX.md` na mesma pasta.
2. Execute:

```powershell
python main.py
```

3.Abra `http://localhost:5500` no navegador.

---

## 🧩 Observações

- Útil para editar documentação localmente com atualização imediata.
- Adapte templates/CSS em `render_styles` se desejar estilizar a página.
