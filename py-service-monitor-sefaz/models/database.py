import os
import json
import sqlite3
from contextlib import contextmanager

from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "config.db")

DEFAULT_CONFIG = {
    "url_sefaz": os.getenv(
        "URL_SEFAZ",
        "https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx?versao=0.00&tipoConteudo=P2c98tUpxrI=&AspxAutoDetectCookieSupport=1",
    ),
    "telegram_token": os.getenv("TELEGRAM_TOKEN", ""),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
    "webhook_url": os.getenv("WEBHOOK_URL", ""),
    "check_interval_seconds": "60",
    "request_timeout_seconds": "30",
    "telegram_enabled": "1",
    "webhook_enabled": "0",
    "monitor_enabled": "1",
    "panel_username": os.getenv("PANEL_USERNAME", "admin"),
    "panel_password_hash": generate_password_hash(os.getenv("PANEL_PASSWORD", "admin123")),
}

BOOLEAN_KEYS = {"telegram_enabled", "webhook_enabled", "monitor_enabled"}
INTEGER_KEYS = {"check_interval_seconds", "request_timeout_seconds"}
SENSITIVE_KEYS = {"panel_password_hash"}
PUBLIC_CONFIG_KEYS = {
    "url_sefaz",
    "telegram_token",
    "telegram_chat_id",
    "webhook_url",
    "check_interval_seconds",
    "request_timeout_seconds",
    "telegram_enabled",
    "webhook_enabled",
    "monitor_enabled",
}


@contextmanager
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_app_config_updated_at
            AFTER UPDATE ON app_config
            FOR EACH ROW
            BEGIN
                UPDATE app_config
                SET updated_at = CURRENT_TIMESTAMP
                WHERE key = OLD.key;
            END
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                destination TEXT,
                success INTEGER NOT NULL,
                response_status INTEGER,
                error_message TEXT,
                indisponiveis_count INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    seed_defaults()


def seed_defaults():
    with get_connection() as connection:
        for key, value in DEFAULT_CONFIG.items():
            connection.execute(
                "INSERT OR IGNORE INTO app_config (key, value) VALUES (?, ?)",
                (key, str(value)),
            )


def parse_config_value(key: str, value: str):
    if key in BOOLEAN_KEYS:
        return value == "1"
    if key in INTEGER_KEYS:
        return int(value)
    return value


def serialize_config_value(key: str, value):
    if key in BOOLEAN_KEYS:
        return "1" if bool(value) else "0"
    if key in INTEGER_KEYS:
        return str(int(value))
    return str(value).strip()


def get_config(include_sensitive: bool = False):
    with get_connection() as connection:
        rows = connection.execute("SELECT key, value FROM app_config").fetchall()

    config = DEFAULT_CONFIG.copy()
    config.update({row["key"]: row["value"] for row in rows})
    parsed = {key: parse_config_value(key, value) for key, value in config.items()}
    if include_sensitive:
        return parsed
    return {key: value for key, value in parsed.items() if key not in SENSITIVE_KEYS}


def get_public_config():
    config = get_config()
    return {key: config[key] for key in PUBLIC_CONFIG_KEYS}


def get_auth_settings():
    config = get_config(include_sensitive=True)
    return {"panel_username": config["panel_username"]}


def update_config(updates: dict):
    if not updates:
        return get_public_config()

    current = get_public_config()
    sanitized = {}

    for key, value in updates.items():
        if key not in current:
            continue
        if key in INTEGER_KEYS:
            numeric_value = int(value)
            if numeric_value <= 0:
                raise ValueError(f"{key} deve ser maior que zero.")
            sanitized[key] = serialize_config_value(key, numeric_value)
            continue

        if key in BOOLEAN_KEYS:
            sanitized[key] = serialize_config_value(key, value)
            continue

        text_value = str(value).strip()
        if key == "url_sefaz" and not text_value:
            raise ValueError("url_sefaz nao pode estar vazia.")
        if key == "webhook_url" and updates.get("webhook_enabled") and not text_value:
            raise ValueError("webhook_url nao pode estar vazia quando o webhook estiver habilitado.")
        sanitized[key] = serialize_config_value(key, text_value)

    with get_connection() as connection:
        for key, value in sanitized.items():
            connection.execute(
                "UPDATE app_config SET value = ? WHERE key = ?",
                (value, key),
            )

    return get_public_config()


def verify_panel_credentials(username: str, password: str):
    config = get_config(include_sensitive=True)
    return username == config["panel_username"] and check_password_hash(
        config["panel_password_hash"],
        password,
    )


def update_panel_credentials(current_password: str, new_username: str, new_password: str | None = None):
    config = get_config(include_sensitive=True)

    if not check_password_hash(config["panel_password_hash"], current_password):
        raise ValueError("Senha atual invalida.")

    username_value = (new_username or config["panel_username"]).strip()
    if not username_value:
        raise ValueError("panel_username nao pode estar vazio.")

    with get_connection() as connection:
        connection.execute(
            "UPDATE app_config SET value = ? WHERE key = 'panel_username'",
            (username_value,),
        )

        if new_password:
            connection.execute(
                "UPDATE app_config SET value = ? WHERE key = 'panel_password_hash'",
                (generate_password_hash(new_password),),
            )

    return get_auth_settings()


def record_alert_history(delivery: dict):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO alert_history (
                channel,
                destination,
                success,
                response_status,
                error_message,
                indisponiveis_count,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delivery.get("channel", "unknown"),
                delivery.get("destination", ""),
                1 if delivery.get("success") else 0,
                delivery.get("response_status"),
                delivery.get("error_message"),
                int(delivery.get("indisponiveis_count", 0)),
                json.dumps(delivery.get("payload", {}), ensure_ascii=False),
            ),
        )


def list_alert_history(limit: int = 20):
    safe_limit = max(1, min(int(limit), 100))

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, channel, destination, success, response_status, error_message,
                   indisponiveis_count, payload_json, created_at
            FROM alert_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    history = []
    for row in rows:
        history.append(
            {
                "id": row["id"],
                "channel": row["channel"],
                "destination": row["destination"],
                "success": bool(row["success"]),
                "response_status": row["response_status"],
                "error_message": row["error_message"],
                "indisponiveis_count": row["indisponiveis_count"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
        )

    return history