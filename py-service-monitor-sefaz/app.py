import atexit
import ast
import os
import pkgutil
import sys
import threading
import time
from functools import wraps

# Compatibilidade para stacks Flask/Werkzeug antigos rodando em Python 3.14.
if not hasattr(ast, "Str"):
    class _CompatStr(ast.Constant):
        def __init__(self, s="", **kwargs):
            super().__init__(value=s, **kwargs)
            self.s = s

    setattr(ast, "Str", _CompatStr)

if not hasattr(ast, "Num"):
    class _CompatNum(ast.Constant):
        def __init__(self, n=0, **kwargs):
            super().__init__(value=n, **kwargs)
            self.n = n

    setattr(ast, "Num", _CompatNum)

if not hasattr(ast, "Bytes"):
    class _CompatBytes(ast.Constant):
        def __init__(self, s=b"", **kwargs):
            super().__init__(value=s, **kwargs)
            self.s = s

    setattr(ast, "Bytes", _CompatBytes)

if not hasattr(ast, "NameConstant"):
    class _CompatNameConstant(ast.Constant):
        def __init__(self, value=None, **kwargs):
            super().__init__(value=value, **kwargs)

    setattr(ast, "NameConstant", _CompatNameConstant)

if not hasattr(pkgutil, "get_loader"):
    import importlib.util

    def _compat_get_loader(name):
        spec = importlib.util.find_spec(name)
        return spec.loader if spec else None

    setattr(pkgutil, "get_loader", _compat_get_loader)

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from models.database import (
    get_auth_settings,
    get_config,
    get_public_config,
    init_db,
    list_alert_history,
    update_config,
    update_panel_credentials,
    verify_panel_credentials,
)
from models.monitor_service import MonitorService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

init_db()

app = Flask(
    "sefaz_monitor",
    root_path=BASE_DIR,
    instance_path=BASE_DIR,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates"),
)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")
monitor_service = MonitorService()
monitor_service.start()


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get("authenticated"):
            return view_func(*args, **kwargs)

        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "message": "Nao autenticado."}), 401

        return redirect(url_for("login"))

    return wrapped_view


def restart_process():
    def delayed_restart():
        time.sleep(1)
        python_executable = sys.executable
        os.execv(python_executable, [python_executable] + sys.argv)

    threading.Thread(target=delayed_restart, daemon=True, name="app-restart").start()


@app.get("/login")
def login():
    if session.get("authenticated"):
        return redirect(url_for("index"))
    return render_template("login.html", error=None)


@app.post("/login")
def login_submit():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if not verify_panel_credentials(username, password):
        return render_template("login.html", error="Usuario ou senha invalidos."), 401

    session["authenticated"] = True
    session["panel_username"] = username
    return redirect(url_for("index"))


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/")
@login_required
def index():
    return render_template("index.html")


@app.get("/api/config")
@login_required
def api_get_config():
    return jsonify(get_public_config())


@app.put("/api/config")
@login_required
def api_update_config():
    payload = request.get_json(silent=True) or {}

    try:
        config = update_config(payload)
    except ValueError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400

    monitor_service.reload()
    return jsonify({"ok": True, "config": config})


@app.get("/api/status")
@login_required
def api_status():
    return jsonify({"ok": True, "status": monitor_service.get_status()})


@app.get("/api/alerts")
@login_required
def api_alerts():
    limit = request.args.get("limit", default=20, type=int)
    return jsonify({"ok": True, "alerts": list_alert_history(limit=limit)})


@app.get("/api/auth/me")
@login_required
def api_auth_me():
    return jsonify({"ok": True, "auth": get_auth_settings()})


@app.put("/api/auth/credentials")
@login_required
def api_auth_credentials():
    payload = request.get_json(silent=True) or {}

    try:
        auth = update_panel_credentials(
            current_password=payload.get("current_password", ""),
            new_username=payload.get("new_username", ""),
            new_password=payload.get("new_password") or None,
        )
    except ValueError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400

    session["panel_username"] = auth["panel_username"]
    return jsonify({"ok": True, "auth": auth})


@app.get("/api/webhook/schema")
@login_required
def api_webhook_schema():
    return jsonify(
        {
            "ok": True,
            "schema_version": "1.0",
            "method": "POST",
            "content_type": "application/json",
            "example": {
                "event": "sefaz_alert",
                "source": "py-service-monitor-sefaz",
                "generated_at": "2026-04-20T20:00:00+00:00",
                "summary": {
                    "message": "<b>🚨 SERVIÇOS INDISPONÍVEIS DETECTADOS</b>\\n\\n❌ BA - Status Servico4",
                    "indisponiveis_count": 1,
                },
                "indisponiveis": ["BA - Status Servico4"],
                "status": {
                    "BA": {
                        "Status Servico4": "Indisponível",
                    }
                },
            },
        }
    )


@app.post("/api/actions/run-now")
@login_required
def api_run_now():
    monitor_service.run_now()
    return jsonify({"ok": True, "message": "Execucao manual agendada."})


@app.post("/api/actions/start")
@login_required
def api_start_monitor():
    config = update_config({"monitor_enabled": True})
    monitor_service.reload()
    return jsonify({"ok": True, "config": config, "message": "Monitor ativado."})


@app.post("/api/actions/stop")
@login_required
def api_stop_monitor():
    config = update_config({"monitor_enabled": False})
    monitor_service.reload()
    return jsonify({"ok": True, "config": config, "message": "Monitor pausado."})


@app.post("/api/actions/restart")
@login_required
def api_restart():
    restart_process()
    return jsonify({"ok": True, "message": "Reinicio solicitado."}), 202


@app.get("/api/health")
def api_health():
    return jsonify({"ok": True})


@atexit.register
def shutdown_monitor():
    monitor_service.stop()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)