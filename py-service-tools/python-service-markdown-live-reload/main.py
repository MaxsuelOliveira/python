from flask import Flask, render_template_string
from livereload import Server
import markdown

app = Flask(__name__)

def render_markdown():
    with open("MAX.md", "r", encoding="utf-8") as f:
        md_content = f.read()
    return markdown.markdown(md_content, extensions=["extra"])

def render_styles():
    styles = """
    body {
        font-family: Arial, sans-serif;
        line-height: 1.6;
        margin: 20px;
    }
    h1, h2, h3 {
        color: #333;
    }
    p {
        margin-bottom: 15px;
    }
    a {
        color: #007BFF;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    """
    return styles

@app.route("/")
def index():
    html_content = render_markdown()
    full_page = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Visualizador Markdown</title>
        <style>
        {render_styles()}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    return render_template_string(full_page)

if __name__ == "__main__":
    server = Server(app.wsgi_app)
    server.watch("MAX.md")  # Observa o .md para atualizar
    server.serve(host="0.0.0.0", port=5500, debug=True)