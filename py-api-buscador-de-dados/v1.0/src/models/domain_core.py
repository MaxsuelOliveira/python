from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, date
import sqlite3
import os
import json

from pydantic import BaseModel, EmailStr

from ..database.connection import SQLiteConnection


# Database connections

db = SQLiteConnection()
log_db = SQLiteConnection(db_path=os.getenv("LOG_SQLITE_DB_PATH", "data/logs.sqlite3"))


# -----------------------------
# Pydantic models
# -----------------------------


class UserBase(BaseModel):
    name: str
    cpf: str
    email: EmailStr
    phone: str
    role: str = "user"
    payment_method: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    cpf: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    payment_method: Optional[str] = None


class User(UserBase):
    id: int
    created_at: str
    updated_at: str


class PlanBase(BaseModel):
    name: str
    price: float
    duration_days: int
    total_tokens: int


class Plan(PlanBase):
    id: int


class AssignPlanRequest(BaseModel):
    plan_id: int


class Payment(BaseModel):
    id: int
    user_id: int
    plan_id: Optional[int]
    amount: float
    status: str
    method: str
    created_at: str


class PaymentMethodUpdate(BaseModel):
    payment_method: str


class DashboardOverview(BaseModel):
    total_users: int
    total_plans: int
    active_subscriptions: int
    total_payments: int
    payments_success: int
    payments_failed: int


class RevenueSummary(BaseModel):
    """Resumo de faturamento em um intervalo de datas."""

    start_date: str
    end_date: str
    total_amount: float
    total_success: int


class UserPlanTokens(BaseModel):
    user_id: int
    plan_id: int
    plan_name: str
    total_tokens: int
    remaining_tokens: int
    start_date: str
    end_date: Optional[str]
    active: bool


class TokenConsumeRequest(BaseModel):
    amount: int


class ExternalUserPayload(BaseModel):
    """Representa o JSON de dados do usuário externo que será salvo.

    É flexível (dict genérico) para aceitar telefone, ip, nome, username etc.
    """

    data: Dict[str, Any]


class DailyFreeTokens(BaseModel):
    """Controle de tokens gratuitos diarios por usuario.

    Esta estrutura e persistida em tabela propria para que o saldo
    de "3 tokens gratis por dia" nao se perca entre reinicios.
    """

    user_id: int
    date: str  # ISO YYYY-MM-DD
    total_tokens: int
    used_tokens: int


# -----------------------------
# Helpers
# -----------------------------


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        name=row["name"],
        cpf=row["cpf"],
        email=row["email"],
        phone=row["phone"],
        role=row["role"],
        payment_method=row["payment_method"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_plan(row: sqlite3.Row) -> Plan:
    return Plan(
        id=row["id"],
        name=row["name"],
        price=row["price"],
        duration_days=row["duration_days"],
        total_tokens=row["total_tokens"],
    )


def _row_to_payment(row: sqlite3.Row) -> Payment:
    return Payment(
        id=row["id"],
        user_id=row["user_id"],
        plan_id=row["plan_id"],
        amount=row["amount"],
        status=row["status"],
        method=row["method"],
        created_at=row["created_at"],
    )


def _row_to_daily_free_tokens(row: sqlite3.Row) -> DailyFreeTokens:
    return DailyFreeTokens(
        user_id=row["user_id"],
        date=row["date"],
        total_tokens=row["total_tokens"],
        used_tokens=row["used_tokens"],
    )


# -----------------------------
# Schema helpers
# -----------------------------


def _ensure_column(table: str, column: str, coltype: str) -> None:
    """Ensure that a column exists in a table (simple migration helper)."""
    rows = db.fetch_all(f"PRAGMA table_info({table})", ())
    names = {r["name"] for r in rows}
    if column not in names:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


# -----------------------------
# Schema & seed
# -----------------------------


def init_db() -> None:
    """Create main tables if they do not exist."""

    # Users table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            role TEXT NOT NULL,
            payment_method TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    # Plans table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price REAL NOT NULL,
            duration_days INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL
        )
        """
    )

    # User plans (subscriptions)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS user_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            total_tokens INTEGER,
            remaining_tokens INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE
        )
        """
    )

    # Payments table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            method TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE SET NULL
        )
        """
    )

    # Simple migrations for existing databases
    _ensure_column("plans", "total_tokens", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column("user_plans", "total_tokens", "INTEGER")
    _ensure_column("user_plans", "remaining_tokens", "INTEGER")

    # Tabela para armazenar o JSON de usuário externo (no banco principal)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS external_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system_user_id INTEGER,
            system_user_email TEXT,
            plan_id INTEGER,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    # Banco separado para logs de puxadas (log_db)
    log_db.execute(
        """
        CREATE TABLE IF NOT EXISTS external_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system_user_id INTEGER,
            system_user_email TEXT,
            plan_id INTEGER,
            external_user_id INTEGER,
            request_url TEXT,
            status_code INTEGER,
            success INTEGER NOT NULL,
            error_message TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    # Tokens gratuitos diarios por usuario
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_free_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            used_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 3,
            UNIQUE(user_id, date),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    # Usuarios do bot (mapeamento persistente de chat_id do Telegram)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            email TEXT,
            chat_id INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            last_seen_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(chat_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
        """
    )


def seed_db() -> None:
    """Populate database with some test data if it is empty."""

    existing = db.fetch_one("SELECT id FROM users LIMIT 1")
    if existing:
        return

    now = datetime.utcnow().isoformat()

    # Test users
    users_data = [
        UserCreate(
            name="Admin Master",
            cpf="00000000001",
            email="maxsuel.david@webart3.com",
            phone="+550000000001",
            role="admin",
            payment_method="credit_card",
        ),
        UserCreate(
            name="User Teste 1",
            cpf="00000000002",
            email="kristiyan7794@uorak.com",
            phone="+550000000002",
            role="user",
            payment_method="pix",
        ),
    ]

    for u in users_data:
        db.execute(
            """
            INSERT INTO users (name, cpf, email, phone, role, payment_method, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                u.name,
                u.cpf,
                u.email,
                u.phone,
                u.role,
                u.payment_method,
                now,
                now,
            ),
        )

    # Test plans - pacotes de tokens (venda por quantidade de tokens)
    # Duracao longa (365 dias) apenas para manter compatibilidade de expiracao,
    # mas na pratica o limite principal e o numero de tokens.
    #
    # Estrategia de precificacao:
    # - Pacotes pequenos com preco por token maior (mais margem).
    # - Pacotes grandes com desconto controlado (melhor custo-beneficio, mas ainda rentavel).
    plans_data = [
        PlanBase(name="Pacote 10 tokens", price=14.90, duration_days=365, total_tokens=10),   # ~R$ 1,49/token
        PlanBase(name="Pacote 50 tokens", price=49.90, duration_days=365, total_tokens=50),   # ~R$ 1,00/token
        PlanBase(name="Pacote 100 tokens", price=79.90, duration_days=365, total_tokens=100), # ~R$ 0,80/token
        PlanBase(name="Pacote 1000 tokens", price=499.90, duration_days=365, total_tokens=1000), # ~R$ 0,50/token
    ]

    for p in plans_data:
        db.execute(
            """
            INSERT INTO plans (name, price, duration_days, total_tokens)
            VALUES (?, ?, ?, ?)
            """,
            (
                p.name,
                p.price,
                p.duration_days,
                p.total_tokens,
            ),
        )

    # Link first user to first plan with a payment
    user_row = db.fetch_one("SELECT * FROM users WHERE cpf = ?", ("00000000001",))
    plan_row = db.fetch_one("SELECT * FROM plans WHERE name = ?", ("Mensal",))

    if user_row and plan_row:
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=plan_row["duration_days"])

        total_tokens = plan_row["total_tokens"] if plan_row["total_tokens"] is not None else 0

        db.execute(
            """
            INSERT INTO user_plans (user_id, plan_id, start_date, end_date, active, total_tokens, remaining_tokens)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (
                user_row["id"],
                plan_row["id"],
                start_date.isoformat(),
                end_date.isoformat(),
                total_tokens,
                total_tokens,
            ),
        )

        db.execute(
            """
            INSERT INTO payments (user_id, plan_id, amount, status, method, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_row["id"],
                plan_row["id"],
                plan_row["price"],
                "success",
                user_row["payment_method"] or "pix",
                datetime.utcnow().isoformat(),
            ),
        )


# -----------------------------
# User operations
# -----------------------------


def get_all_users() -> List[User]:
    rows = db.fetch_all("SELECT * FROM users ORDER BY id", ())
    return [_row_to_user(r) for r in rows]


def get_user_by_id(user_id: int) -> Optional[User]:
    row = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    return _row_to_user(row) if row else None


def get_user_by_name(name: str) -> List[User]:
    rows = db.fetch_all(
        "SELECT * FROM users WHERE name LIKE ? ORDER BY id",
        (f"%{name}%",),
    )
    return [_row_to_user(r) for r in rows]


def get_user_by_cpf(cpf: str) -> Optional[User]:
    row = db.fetch_one("SELECT * FROM users WHERE cpf = ?", (cpf,))
    return _row_to_user(row) if row else None


def get_user_by_email(email: str) -> Optional[User]:
    row = db.fetch_one("SELECT * FROM users WHERE email = ?", (email,))
    return _row_to_user(row) if row else None


def get_user_by_phone(phone: str) -> List[User]:
    rows = db.fetch_all(
        "SELECT * FROM users WHERE phone LIKE ? ORDER BY id",
        (f"%{phone}%",),
    )
    return [_row_to_user(r) for r in rows]


def get_users_by_role(role: str) -> List[User]:
    rows = db.fetch_all("SELECT * FROM users WHERE role = ? ORDER BY id", (role,))
    return [_row_to_user(r) for r in rows]


def create_user(data: UserCreate) -> User:
    now = datetime.utcnow().isoformat()
    db.execute(
        """
        INSERT INTO users (name, cpf, email, phone, role, payment_method, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.name,
            data.cpf,
            data.email,
            data.phone,
            data.role,
            data.payment_method,
            now,
            now,
        ),
    )

    row = db.fetch_one("SELECT * FROM users WHERE cpf = ?", (data.cpf,))
    if not row:
        raise RuntimeError("Failed to create user")
    return _row_to_user(row)


def update_user(user_id: int, data: UserUpdate) -> Optional[User]:
    existing = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not existing:
        return None

    current = _row_to_user(existing)

    updated = UserUpdate(**data.dict(exclude_unset=True))

    new_data = current.dict()
    for field, value in updated.dict(exclude_unset=True).items():
        new_data[field] = value

    now = datetime.utcnow().isoformat()

    db.execute(
        """
        UPDATE users
        SET name = ?, cpf = ?, email = ?, phone = ?, role = ?, payment_method = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            new_data["name"],
            new_data["cpf"],
            new_data["email"],
            new_data["phone"],
            new_data["role"],
            new_data["payment_method"],
            now,
            user_id,
        ),
    )

    row = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    return _row_to_user(row) if row else None


def delete_user(user_id: int) -> bool:
    affected = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return affected > 0


# -----------------------------
# Plan operations
# -----------------------------


def get_plans() -> List[Plan]:
    rows = db.fetch_all("SELECT * FROM plans ORDER BY id", ())
    return [_row_to_plan(r) for r in rows]


def get_plan_by_id(plan_id: int) -> Optional[Plan]:
    row = db.fetch_one("SELECT * FROM plans WHERE id = ?", (plan_id,))
    return _row_to_plan(row) if row else None


def get_plans_by_user_id(user_id: int) -> List[Plan]:
    rows = db.fetch_all(
        """
        SELECT p.*
        FROM plans p
        JOIN user_plans up ON up.plan_id = p.id
        WHERE up.user_id = ? AND up.active = 1
        ORDER BY p.id
        """,
        (user_id,),
    )
    return [_row_to_plan(r) for r in rows]


def get_user_plan_tokens(user_id: int, plan_id: int) -> Optional[UserPlanTokens]:
    row = db.fetch_one(
        """
        SELECT up.user_id, up.plan_id, up.total_tokens, up.remaining_tokens,
               up.start_date, up.end_date, up.active, p.name AS plan_name
        FROM user_plans up
        JOIN plans p ON p.id = up.plan_id
        WHERE up.user_id = ? AND up.plan_id = ? AND up.active = 1
        """,
        (user_id, plan_id),
    )
    if not row:
        return None

    return UserPlanTokens(
        user_id=row["user_id"],
        plan_id=row["plan_id"],
        plan_name=row["plan_name"],
        total_tokens=row["total_tokens"] or 0,
        remaining_tokens=row["remaining_tokens"] or 0,
        start_date=row["start_date"],
        end_date=row["end_date"],
        active=bool(row["active"]),
    )


def assign_plan_to_user(user_id: int, plan_id: int) -> bool:
    user = get_user_by_id(user_id)
    plan = get_plan_by_id(plan_id)
    if not user or not plan:
        return False

    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=plan.duration_days)

    db.execute(
        """
        INSERT INTO user_plans (user_id, plan_id, start_date, end_date, active, total_tokens, remaining_tokens)
        VALUES (?, ?, ?, ?, 1, ?, ?)
        """,
        (
            user_id,
            plan_id,
            start_date.isoformat(),
            end_date.isoformat(),
            plan.total_tokens,
            plan.total_tokens,
        ),
    )

    # Optionally register a pending payment
    db.execute(
        """
        INSERT INTO payments (user_id, plan_id, amount, status, method, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            plan_id,
            float(plan.price),
            "pending",
            user.payment_method or "pix",
            datetime.utcnow().isoformat(),
        ),
    )

    return True


def remove_plan_from_user(user_id: int, plan_id: int) -> bool:
    affected = db.execute(
        """
        UPDATE user_plans
        SET active = 0
        WHERE user_id = ? AND plan_id = ? AND active = 1
        """,
        (
            user_id,
            plan_id,
        ),
    )
    return affected > 0


def consume_tokens(user_id: int, plan_id: int, amount: int) -> Optional[UserPlanTokens]:
    if amount <= 0:
        return None

    affected = db.execute(
        """
        UPDATE user_plans
        SET remaining_tokens = remaining_tokens - ?
        WHERE user_id = ? AND plan_id = ? AND active = 1 AND remaining_tokens >= ?
        """,
        (
            amount,
            user_id,
            plan_id,
            amount,
        ),
    )

    if affected == 0:
        return None

    return get_user_plan_tokens(user_id, plan_id)


# -----------------------------
# Daily free token operations
# -----------------------------


def _get_or_create_daily_free_tokens(
    user_id: int,
    target_date: Optional[date] = None,
    default_total: int = 3,
) -> DailyFreeTokens:
    """Obtem (ou cria) o registro de tokens gratis diarios para o usuario/data.

    Mantem o total configuravel (padrao 3 tokens por dia).
    """

    if target_date is None:
        target_date = date.today()

    date_str = target_date.isoformat()

    row = db.fetch_one(
        """
        SELECT user_id, date, total_tokens, used_tokens
        FROM daily_free_tokens
        WHERE user_id = ? AND date = ?
        """,
        (user_id, date_str),
    )

    if not row:
        db.execute(
            """
            INSERT INTO daily_free_tokens (user_id, date, used_tokens, total_tokens)
            VALUES (?, ?, 0, ?)
            """,
            (user_id, date_str, default_total),
        )

        row = db.fetch_one(
            """
            SELECT user_id, date, total_tokens, used_tokens
            FROM daily_free_tokens
            WHERE user_id = ? AND date = ?
            """,
            (user_id, date_str),
        )

    if row is None:
        raise RuntimeError("Failed to create or fetch daily_free_tokens record")

    return _row_to_daily_free_tokens(row)


def get_today_daily_free_tokens(user_id: int) -> DailyFreeTokens:
    """Retorna o controle de tokens gratis do dia atual para o usuario."""

    return _get_or_create_daily_free_tokens(user_id=user_id)


def consume_daily_free_tokens(user_id: int, amount: int = 1) -> Optional[DailyFreeTokens]:
    """Consome tokens gratuitos diarios do usuario.

    Retorna o registro atualizado ou None se nao houver saldo suficiente.
    """

    if amount <= 0:
        return None

    today = date.today()
    date_str = today.isoformat()

    # Tenta atualizar diretamente; se nao existir registro, cria e tenta de novo
    for _ in range(2):
        affected = db.execute(
            """
            UPDATE daily_free_tokens
            SET used_tokens = used_tokens + ?
            WHERE user_id = ? AND date = ? AND used_tokens + ? <= total_tokens
            """,
            (
                amount,
                user_id,
                date_str,
                amount,
            ),
        )

        if affected > 0:
            row = db.fetch_one(
                """
                SELECT user_id, date, total_tokens, used_tokens
                FROM daily_free_tokens
                WHERE user_id = ? AND date = ?
                """,
                (user_id, date_str),
            )
            return _row_to_daily_free_tokens(row) if row else None

        # Se nao afetou nenhuma linha, garante que o registro exista e tenta novamente
        _get_or_create_daily_free_tokens(user_id=user_id, target_date=today)

    return None


# -----------------------------
# Payment operations
# -----------------------------


def get_payments_by_user_id(user_id: int) -> List[Payment]:
    rows = db.fetch_all(
        "SELECT * FROM payments WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    return [_row_to_payment(r) for r in rows]


def create_pending_payment(
    user_id: int,
    plan_id: int,
    amount: float,
    method: str,
) -> Optional[Payment]:
    """Cria um registro de pagamento pendente vinculado a um plano.

    - Valida existencia de usuario e plano.
    - Cria registro em `payments` com status="pending".
    """

    user = get_user_by_id(user_id)
    plan = get_plan_by_id(plan_id)
    if not user or not plan:
        return None

    now = datetime.utcnow().isoformat()

    db.execute(
        """
        INSERT INTO payments (user_id, plan_id, amount, status, method, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            plan_id,
            float(amount),
            "pending",
            method,
            now,
        ),
    )

    row = db.fetch_one(
        "SELECT * FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    return _row_to_payment(row) if row else None


def update_payment_method(user_id: int, payment_method: str) -> Optional[User]:
    user = get_user_by_id(user_id)
    if not user:
        return None

    now = datetime.utcnow().isoformat()

    db.execute(
        """
        UPDATE users
        SET payment_method = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            payment_method,
            now,
            user_id,
        ),
    )

    row = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    return _row_to_user(row) if row else None


# -----------------------------
# Dashboard
# -----------------------------


def get_dashboard_overview() -> DashboardOverview:
    total_users_row = db.fetch_one("SELECT COUNT(*) AS c FROM users", ())
    total_plans_row = db.fetch_one("SELECT COUNT(*) AS c FROM plans", ())
    active_subscriptions_row = db.fetch_one(
        "SELECT COUNT(*) AS c FROM user_plans WHERE active = 1",
        (),
    )
    total_payments_row = db.fetch_one(
        "SELECT COUNT(*) AS c FROM payments",
        (),
    )
    payments_success_row = db.fetch_one(
        "SELECT COUNT(*) AS c FROM payments WHERE status = 'success'",
        (),
    )
    payments_failed_row = db.fetch_one(
        "SELECT COUNT(*) AS c FROM payments WHERE status = 'failed'",
        (),
    )

    return DashboardOverview(
        total_users=total_users_row["c"] if total_users_row else 0,
        total_plans=total_plans_row["c"] if total_plans_row else 0,
        active_subscriptions=active_subscriptions_row["c"] if active_subscriptions_row else 0,
        total_payments=total_payments_row["c"] if total_payments_row else 0,
        payments_success=payments_success_row["c"] if payments_success_row else 0,
        payments_failed=payments_failed_row["c"] if payments_failed_row else 0,
    )


def get_revenue_for_period(start: datetime, end: datetime) -> RevenueSummary:
    """Retorna o faturamento em um intervalo de datas (pagamentos com status success)."""

    start_str = start.isoformat()
    end_str = end.isoformat()

    total_row = db.fetch_one(
        """
        SELECT COALESCE(SUM(amount), 0) AS total_amount,
               COUNT(*) AS total_success
        FROM payments
        WHERE status = 'success' AND created_at BETWEEN ? AND ?
        """,
        (start_str, end_str),
    )

    total_amount = float(total_row["total_amount"]) if total_row else 0.0
    total_success = int(total_row["total_success"]) if total_row else 0

    return RevenueSummary(
        start_date=start_str,
        end_date=end_str,
        total_amount=total_amount,
        total_success=total_success,
    )


# -----------------------------
# Payment confirmation & plan linking
# -----------------------------


def confirm_payment_and_link_plan(
    user_id: int,
    payment_id: int,
    plan_id: int,
    status: str = "success",
) -> Optional[Payment]:
    """Confirma um pagamento, vincula o plano e garante assinatura ativa.

    - Atualiza o registro em payments com plan_id e status.
    - Garante que exista um registro correspondente em user_plans (sem criar novo pagamento).
    """

    payment_row = db.fetch_one(
        "SELECT * FROM payments WHERE id = ? AND user_id = ?",
        (payment_id, user_id),
    )
    if not payment_row:
        return None

    # Atualiza o pagamento
    db.execute(
        """
        UPDATE payments
        SET plan_id = ?, status = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            plan_id,
            status,
            payment_id,
            user_id,
        ),
    )

    # Garante assinatura ativa em user_plans sem criar novo pagamento
    subscription_row = db.fetch_one(
        """
        SELECT * FROM user_plans
        WHERE user_id = ? AND plan_id = ? AND active = 1
        """,
        (user_id, plan_id),
    )

    if not subscription_row:
        plan = get_plan_by_id(plan_id)
        if plan is not None:
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=plan.duration_days)
            db.execute(
                """
                INSERT INTO user_plans (user_id, plan_id, start_date, end_date, active, total_tokens, remaining_tokens)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    user_id,
                    plan_id,
                    start_date.isoformat(),
                    end_date.isoformat(),
                    plan.total_tokens,
                    plan.total_tokens,
                ),
            )

    updated_payment_row = db.fetch_one("SELECT * FROM payments WHERE id = ?", (payment_id,))
    return _row_to_payment(updated_payment_row) if updated_payment_row else None


# -----------------------------
# External user payload & logs
# -----------------------------


def save_external_user_payload(
    system_user_id: int,
    system_user_email: str,
    plan_id: Optional[int],
    payload: Dict[str, Any],
) -> int:
    """Salva o JSON de dados do usuário externo no banco principal.

    Retorna o ID gerado na tabela external_users.
    """

    now = datetime.utcnow().isoformat()
    payload_json = json.dumps(payload, ensure_ascii=False)

    db.execute(
        """
        INSERT INTO external_users (system_user_id, system_user_email, plan_id, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            system_user_id,
            system_user_email,
            plan_id,
            payload_json,
            now,
        ),
    )

    row = db.fetch_one(
        "SELECT id FROM external_users WHERE system_user_id = ? AND plan_id = ? ORDER BY id DESC LIMIT 1",
        (system_user_id, plan_id),
    )
    return int(row["id"]) if row else 0


def log_external_request(
    system_user_id: int,
    system_user_email: str,
    plan_id: Optional[int],
    external_user_id: int,
    request_url: str,
    status_code: int,
    success: bool,
    error_message: Optional[str] = None,
) -> None:
    """Registra um log de puxada no banco separado (logs)."""

    now = datetime.utcnow().isoformat()

    log_db.execute(
        """
        INSERT INTO external_logs (
            system_user_id,
            system_user_email,
            plan_id,
            external_user_id,
            request_url,
            status_code,
            success,
            error_message,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            system_user_id,
            system_user_email,
            plan_id,
            external_user_id,
            request_url,
            status_code,
            1 if success else 0,
            error_message,
            now,
        ),
    )


def get_external_logs_by_user(system_user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Retorna o historico recente de consultas externas de um usuario.

    Os registros sao retornados em ordem decrescente de "created_at".
    """

    rows = log_db.fetch_all(
        """
        SELECT system_user_id, system_user_email, plan_id, external_user_id,
               request_url, status_code, success, error_message, created_at
        FROM external_logs
        WHERE system_user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (system_user_id, limit),
    )

    return [
        {
            "created_at": r["created_at"],
            "request_url": r["request_url"],
            "status_code": r["status_code"],
            "success": bool(r["success"]),
            "error_message": r["error_message"],
            "plan_id": r["plan_id"],
            "external_user_id": r["external_user_id"],
        }
        for r in rows
    ]


def get_external_logs_global(limit: int = 20) -> List[Dict[str, Any]]:
    """Retorna o historico recente de consultas externas (todos os usuarios).

    Usado pelo painel/admin para monitorar o uso geral.
    """

    rows = log_db.fetch_all(
        """
        SELECT system_user_id, system_user_email, plan_id, external_user_id,
               request_url, status_code, success, error_message, created_at
        FROM external_logs
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )

    return [
        {
            "created_at": r["created_at"],
            "request_url": r["request_url"],
            "status_code": r["status_code"],
            "success": bool(r["success"]),
            "error_message": r["error_message"],
            "plan_id": r["plan_id"],
            "external_user_id": r["external_user_id"],
            "system_user_id": r["system_user_id"],
            "system_user_email": r["system_user_email"],
        }
        for r in rows
    ]


def get_all_user_emails() -> List[str]:
    """Retorna a lista de todos os emails de usuarios cadastrados.

    Usado para broadcast de mensagens via bot (admin).
    """

    rows = db.fetch_all("SELECT email FROM users ORDER BY id", ())
    return [r["email"] for r in rows]


def register_or_update_bot_user(
    chat_id: int,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
) -> None:
    """Registra ou atualiza um usuario do bot (chat_id persistente).

    - Se o chat_id ja existir, atualiza user_id/email (quando informados)
      e marca o registro como ativo, atualizando last_seen_at.
    - Se ainda nao existir, cria um novo registro.
    """

    now = datetime.utcnow().isoformat()

    existing = db.fetch_one(
        "SELECT id FROM bot_users WHERE chat_id = ?",
        (chat_id,),
    )

    if existing:
        db.execute(
            """
            UPDATE bot_users
            SET user_id = COALESCE(?, user_id),
                email = COALESCE(?, email),
                is_active = 1,
                last_seen_at = ?,
                updated_at = ?
            WHERE chat_id = ?
            """,
            (
                user_id,
                email,
                now,
                now,
                chat_id,
            ),
        )
    else:
        db.execute(
            """
            INSERT INTO bot_users (
                user_id,
                email,
                chat_id,
                is_active,
                last_seen_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 1, ?, ?, ?)
            """,
            (
                user_id,
                email,
                chat_id,
                now,
                now,
                now,
            ),
        )


def get_all_bot_chat_ids(only_active: bool = True) -> List[int]:
    """Retorna todos os chat_id conhecidos do bot.

    Se only_active=True, considera apenas registros marcados como ativos.
    """

    if only_active:
        rows = db.fetch_all(
            "SELECT chat_id FROM bot_users WHERE is_active = 1 ORDER BY id",
            (),
        )
    else:
        rows = db.fetch_all(
            "SELECT chat_id FROM bot_users ORDER BY id",
            (),
        )

    return [int(r["chat_id"]) for r in rows]


def deactivate_bot_user(chat_id: int) -> None:
    """Marca um chat_id como inativo (ex.: usuario bloqueou o bot)."""

    now = datetime.utcnow().isoformat()
    db.execute(
        """
        UPDATE bot_users
        SET is_active = 0,
            updated_at = ?
        WHERE chat_id = ?
        """,
        (
            now,
            chat_id,
        ),
    )
