import logging
import os
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import asyncio

import smtplib
from email.mime.text import MIMEText

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependencia opcional
    load_dotenv = None

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from src.controllers.user_controller import (
    UserController,
    PlanController,
    PaymentController,
    BotUserController,
)
from src.models.domain_core import (
    UserCreate,
    get_user_plan_tokens,
    get_external_logs_by_user,
    get_today_daily_free_tokens,
    get_revenue_for_period,
    get_external_logs_global,
)
from src.services.api_service import ThirdPartyAPIService, RateLimitExceeded


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# Sessao simples em memoria: chat_id -> email de login
SESSIONS: Dict[int, str] = {}

# Controle de expiracao de sessao (6 horas apos login)
SESSION_EXPIRATIONS: Dict[int, datetime] = {}

# Fluxo de verificacao via codigo (cadastro e login)
PENDING_SIGNUPS: Dict[int, Dict[str, Any]] = {}
PENDING_LOGINS: Dict[int, Dict[str, Any]] = {}

# Controle de logins ativos por email (para evitar multi-login da mesma conta)
ACTIVE_LOGINS: Dict[str, int] = {}


BUSY_FLAG_KEY = "request_in_progress"


def _is_busy(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.user_data.get(BUSY_FLAG_KEY))


def _start_busy(context: ContextTypes.DEFAULT_TYPE, label: str) -> None:
    context.user_data[BUSY_FLAG_KEY] = label


def _end_busy(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(BUSY_FLAG_KEY, None)


def _get_logged_out_keyboard() -> ReplyKeyboardMarkup:
    """Teclado principal para usuarios nao logados."""

    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("/registrar"), KeyboardButton("/login")],
            [KeyboardButton("/planos"), KeyboardButton("/menu")],
        ],
        resize_keyboard=True,
    )


def _get_logged_in_keyboard() -> ReplyKeyboardMarkup:
    """Teclado principal para usuarios logados."""

    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("/menu"), KeyboardButton("/consultar")],
            [KeyboardButton("/meus_tokens"), KeyboardButton("/comprar_tokens")],
            [KeyboardButton("/logout")],
        ],
        resize_keyboard=True,
    )


def _get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Teclado para admin: mesmo menu do usuario + atalho de admin."""

    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("/menu"), KeyboardButton("/consultar")],
            [KeyboardButton("/meus_tokens"), KeyboardButton("/comprar_tokens")],
            [KeyboardButton("/admin_menu"), KeyboardButton("/logout")],
        ],
        resize_keyboard=True,
    )


def _is_admin(email: str) -> bool:
    """Verifica se o usuario logado e admin via UserController."""

    user = UserController.get_by_email(email)
    return bool(user and getattr(user, "role", "user") == "admin")


def _generate_code(length: int = 6) -> str:
    """Gera um codigo numerico simples para verificacao (nao e retornado ao frontend)."""

    return "".join(random.choices(string.digits, k=length))


def _generate_fake_cpf() -> str:
    """Gera um CPF ficticio (11 digitos) para contatos criados apenas com nome/email/telefone."""

    return "".join(random.choices(string.digits, k=11))


def _send_verification_email(email: str, code: str, purpose: str) -> None:
    """Envia o codigo de verificacao por email sem nunca expor o codigo no frontend.

    Usa configuracoes de SMTP via variaveis de ambiente:
      - SMTP_HOST, SMTP_PORT (opcional, padrao 587)
      - SMTP_USER, SMTP_PASSWORD (opcionais)
      - SMTP_USE_TLS ("true"/"false", padrao true)
      - SMTP_FROM (opcional, usa SMTP_USER ou no-reply@example.com)
    """

    host = os.getenv("SMTP_HOST")
    if not host:
        # Sem configuracao de SMTP, apenas registra aviso em log (sem mostrar o codigo)
        logger.warning(
            "SMTP nao configurado; nao foi possivel enviar email de %s para %s",
            purpose,
            email,
        )
        return

    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    from_addr = os.getenv("SMTP_FROM", user or "no-reply@example.com")

    if purpose == "signup":
        subject = "Codigo de verificacao de cadastro - Puxador"
        body = (
            "Seu codigo de verificacao para cadastro no Puxador e: "
            f"{code}\n\n"
            "Se voce nao solicitou este cadastro, ignore este email."
        )
    else:
        subject = "Codigo de login - Puxador"
        body = (
            "Seu codigo de login para acessar o Puxador e: "
            f"{code}\n\n"
            "Se voce nao solicitou este acesso, ignore este email."
        )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = email

    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP

    with smtp_class(host, port) as server:
        # Para conexoes TLS explicitas (porta 587), mantemos starttls;
        # para SSL implicito (porta 465), assumimos canal ja criptografado.
        if use_tls and not use_ssl:
            server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(msg)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mensagem inicial do bot."""

    await update.message.reply_text(
        "👋 Olá, seja muito bem-vindo ao bot do *Puxador*!\n\n"
        "Aqui você pode:\n"
        "• 🔐 Criar sua conta e logar com código por e-mail\n"
        "• 📦 Comprar pacotes de tokens de consulta\n"
        "• 🔎 Puxar dados por CPF, e-mail, telefone e muito mais\n\n"
        "📌 *Comandos principais*:\n"
        "• /registrar – Criar conta (nome, e-mail, telefone)\n"
        "• /confirmar_registro <codigo> – Confirmar cadastro enviado por e-mail\n"
        "• /login <email> – Receber código de login neste e-mail e digitar aqui\n"
        "• /planos – Ver pacotes de tokens disponíveis\n"
        "• /menu – Abrir o menu de consultas interativas 🚀\n"
    )

    # Teclado rapido com comandos principais, variando se ja estiver logado
    email = _get_logged_email(update)
    if email:
        if _is_admin(email):
            keyboard = _get_admin_keyboard()
        else:
            keyboard = _get_logged_in_keyboard()
        text = "✅ Você já está logado. Use os botões abaixo para navegar:"
    else:
        keyboard = _get_logged_out_keyboard()
        text = "👇 Use os botões abaixo para navegar com mais facilidade:"

    await update.message.reply_text(
        text,
        reply_markup=keyboard,
    )

    # GIF de boas-vindas (substitua pela URL do seu GIF preferido)
    try:
        await update.message.reply_animation(
            animation="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExd3dxbzMzNTRidTBmZzZqMGYzNTBmeGd5c2Y1bGZpZ3R6a3Qwd2lubyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/3o7aD2saalBwwftBIY/giphy.gif",
            caption="Bora começar? Escolha uma opção do menu 👆",
        )
    except Exception:  # noqa: BLE001
        # Se der erro no envio do GIF, apenas ignora para nao quebrar o fluxo
        logger.warning("Nao foi possivel enviar GIF de boas-vindas")


async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Formato esperado: /registrar Nome Completo;email;telefone
    # Exemplo: /registrar Fulano da Silva;fulano@example.com;+550000000003
    if not context.args:
        await update.message.reply_text(
            "📝 *Cadastro rápido!*\n\n"
            "Envie no formato:\n"
            "`/registrar Nome Completo;email;telefone`\n\n"
            "Exemplo:\n"
            "`/registrar Fulano da Silva;fulano@example.com;+550000000003`",
            parse_mode="Markdown",
        )
        return

    raw = " ".join(context.args)
    parts = [p.strip() for p in raw.split(";")]
    if len(parts) != 3:
        await update.message.reply_text(
            "⚠️ Formato inválido.\n"
            "Use: `/registrar Nome Completo;email;telefone`",
            parse_mode="Markdown",
        )
        return

    nome, email, telefone = parts

    chat_id = update.effective_chat.id

    code = _generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    PENDING_SIGNUPS[chat_id] = {
        "name": nome,
        "email": email,
        "phone": telefone,
        "code": code,
        "expires_at": expires_at,
    }

    try:
        _send_verification_email(email, code, purpose="signup")
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao enviar email de verificacao de cadastro")
        PENDING_SIGNUPS.pop(chat_id, None)
        await update.message.reply_text(
            "❌ Não foi possível enviar o código de verificação por e-mail.\n"
            "Tente novamente mais tarde ou fale com o suporte."
        )
        return

    await update.message.reply_text(
        "✅ Código de verificação enviado para o seu e-mail!\n\n"
        "📩 Abra sua caixa de entrada, copie o código e volte aqui.\n"
        "Depois use: `/confirmar_registro SEU_CODIGO_AQUI`",
        parse_mode="Markdown",
    )


async def confirmar_registro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirma o cadastro usando o codigo recebido por email e cria o contato."""

    chat_id = update.effective_chat.id
    pending = PENDING_SIGNUPS.get(chat_id)
    if not pending:
        await update.message.reply_text(
            "ℹ️ Nenhum cadastro pendente encontrado para este chat.\n"
            "Use `/registrar` para iniciar um novo cadastro.",
            parse_mode="Markdown",
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Use: `/confirmar_registro CODIGO_RECEBIDO`",
            parse_mode="Markdown",
        )
        return

    code_informed = context.args[0].strip()

    if datetime.now(timezone.utc) > pending["expires_at"]:
        PENDING_SIGNUPS.pop(chat_id, None)
        await update.message.reply_text(
            "⏰ Seu código de cadastro expirou (15 minutos).\n"
            "Use `/registrar` novamente para receber um novo código.",
            parse_mode="Markdown",
        )
        return

    if code_informed != pending["code"]:
        await update.message.reply_text(
            "❌ Código inválido.\n"
            "Confira o código enviado ao seu e-mail e tente novamente."
        )
        return

    # Codigo valido: cria o usuario com CPF ficticio e efetua login
    try:
        user = UserController.create(
            UserCreate(
                name=pending["name"],
                email=pending["email"],
                cpf=_generate_fake_cpf(),
                phone=pending["phone"],
            )
        )
    except Exception:  # noqa: BLE001
        logger.exception("Erro ao criar usuario apos confirmacao de registro")
        await update.message.reply_text(
            "❌ Não foi possível concluir o cadastro.\n"
            "Tente novamente mais tarde ou fale com o suporte."
        )
        return

    PENDING_SIGNUPS.pop(chat_id, None)
    SESSIONS[chat_id] = user.email
    SESSION_EXPIRATIONS[chat_id] = datetime.now(timezone.utc) + timedelta(hours=6)

    # Registra/atualiza o chat_id deste usuario no banco para broadcast futuro
    try:
        BotUserController.register_or_update(chat_id=chat_id, user_id=user.id, email=user.email)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar bot_user apos confirmacao de registro")

    await update.message.reply_text(
        "🎉 *Cadastro confirmado com sucesso!*\n\n"
        f"📧 E-mail: `{user.email}`\n"
        "Você já está logado e pode usar:\n"
        "• /menu – abrir o menu de consultas\n"
        "• /consultar – iniciar uma nova consulta\n"
        "• /meus_tokens – ver seus saldos de tokens\n"
        "• /comprar_tokens – ver pacotes para comprar mais tokens",
        parse_mode="Markdown",
        reply_markup=_get_logged_in_keyboard(),
    )


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia fluxo de login enviando codigo por email."""

    if not context.args:
        await update.message.reply_text("Use: /login seu_email@example.com")
        return

    email = context.args[0].strip()
    user = UserController.get_by_email(email)
    if not user:
        await update.message.reply_text("Usuario nao encontrado com esse email. Use /registrar.")
        return

    chat_id = update.effective_chat.id

    code = _generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    PENDING_LOGINS[chat_id] = {
        "email": email,
        "code": code,
        "expires_at": expires_at,
        "attempts": 0,
    }

    try:
        _send_verification_email(email, code, purpose="login")
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao enviar email de login")
        PENDING_LOGINS.pop(chat_id, None)
        await update.message.reply_text(
            "Nao foi possivel enviar o codigo de login por email. Tente novamente mais tarde."
        )
        return

    # Marca que o proximo texto do usuario (nao-comando) sera tratado como codigo de login
    context.user_data["login_code_pending"] = True

    await update.message.reply_text(
        "Enviamos um codigo de login para o seu email.\n"
        "Digite o codigo aqui nesta conversa para concluir o login."
    )


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Efetua logout do usuario no chat atual, limpando a sessao."""

    chat_id = update.effective_chat.id
    email = SESSIONS.get(chat_id)

    if not email:
        await update.message.reply_text(
            "Voce nao esta logado neste chat. Use /login seu_email@example.com para entrar."
        )
        return

    # Limpa sessao em memoria
    SESSIONS.pop(chat_id, None)
    SESSION_EXPIRATIONS.pop(chat_id, None)

    # Se este usuario do Telegram era o login ativo desse email, limpa o controle
    telegram_user_id = update.effective_user.id
    existing_user_id = ACTIVE_LOGINS.get(email)
    if existing_user_id is not None and existing_user_id == telegram_user_id:
        ACTIVE_LOGINS.pop(email, None)

    # Limpa possiveis estados de fluxo
    context.user_data.pop("login_code_pending", None)
    context.user_data.pop("consulta_tipo", None)
    context.user_data.pop("admin_broadcast_mode", None)
    context.user_data.pop(BUSY_FLAG_KEY, None)

    await update.message.reply_text(
        "Voce saiu da sua conta neste chat.\n"
        "Para entrar novamente, use /login seu_email@example.com.",
        reply_markup=_get_logged_out_keyboard(),
    )


async def confirmar_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirma o login usando o codigo recebido por email."""

    chat_id = update.effective_chat.id
    pending = PENDING_LOGINS.get(chat_id)
    if not pending:
        await update.message.reply_text(
            "Nenhum login pendente encontrado para este chat. Use /login primeiro."
        )
        return

    if not context.args:
        await update.message.reply_text("Use: /confirmar_login <codigo_recebido_por_email>")
        return

    code_informed = context.args[0].strip()

    if datetime.now(timezone.utc) > pending["expires_at"]:
        PENDING_LOGINS.pop(chat_id, None)
        await update.message.reply_text(
            "Codigo expirado. Use /login novamente para receber um novo codigo."
        )
        return

    if code_informed != pending["code"]:
        await update.message.reply_text("Codigo invalido. Verifique o codigo enviado ao seu email.")
        return

    email = pending["email"]
    user = UserController.get_by_email(email)
    if not user:
        PENDING_LOGINS.pop(chat_id, None)
        await update.message.reply_text("Usuario nao encontrado. Use /registrar.")
        return

    PENDING_LOGINS.pop(chat_id, None)
    SESSIONS[chat_id] = user.email
    SESSION_EXPIRATIONS[chat_id] = datetime.now(timezone.utc) + timedelta(hours=6)

    # Registra login ativo para este email e usuario do Telegram
    ACTIVE_LOGINS[user.email] = update.effective_user.id

    # Garante registro persistente do chat_id para este usuario
    try:
        BotUserController.register_or_update(chat_id=chat_id, user_id=user.id, email=user.email)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar bot_user apos confirmar_login")

    await update.message.reply_text(
        f"Login efetuado para {user.email}. Agora voce pode usar /menu, /consultar, /meus_tokens e /comprar_tokens.",
        reply_markup=_get_logged_in_keyboard(),
    )


def _get_logged_email(update: Update) -> str | None:
    chat_id = update.effective_chat.id
    email = SESSIONS.get(chat_id)
    if not email:
        return None

    expires_at = SESSION_EXPIRATIONS.get(chat_id)
    if expires_at is None:
        return email

    if datetime.now(timezone.utc) > expires_at:
        # Sessao expirada: limpa dados e exige novo login
        SESSIONS.pop(chat_id, None)
        SESSION_EXPIRATIONS.pop(chat_id, None)
        return None

    return email


async def planos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    plans = PlanController.get_all_plans()
    if not plans:
        await update.message.reply_text("Nenhum plano cadastrado.")
        return

    lines = ["Planos disponiveis:"]
    keyboard = []
    for p in plans:
        lines.append(
            f"ID {p.id} - {p.name}: R$ {p.price:.2f}, {p.duration_days} dias, {p.total_tokens} tokens"
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"Assinar {p.name} (ID {p.id})",
                    callback_data=f"assinar:{p.id}",
                )
            ]
        )

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def assinar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cria pagamento pendente para um plano (simulando PIX)."""

    email = _get_logged_email(update)
    if not email:
        await update.message.reply_text(
            "Sua sessao expirou ou voce ainda nao fez login. "
            "Use /login seu_email@example.com para continuar."
        )
        return

    if not context.args:
        await update.message.reply_text("Use: /assinar <plan_id>")
        return

    try:
        plan_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("plan_id deve ser um numero inteiro.")
        return

    user = UserController.get_by_email(email)
    if not user:
        await update.message.reply_text("Usuario nao encontrado. Use /registrar.")
        return

    plan = PlanController.get_plan_by_id(plan_id)
    if not plan:
        if update.message:
            await update.message.reply_text("Plano nao encontrado.")
        return

    payment = PaymentController.create_pending(
        user_id=user.id,
        plan_id=plan_id,
        amount=float(plan.price),
        method="pix",
    )
    if not payment:
        await update.message.reply_text("Nao foi possivel criar pagamento pendente.")
        return

    # Confirmacao automatica do pagamento e liberacao de tokens
    confirmed = PaymentController.confirm_and_link_payment(
        user_id=user.id,
        payment_id=payment.id,
        plan_id=plan_id,
    )
    if not confirmed:
        await update.message.reply_text("Nao foi possivel confirmar o pagamento automaticamente.")
        return

    await update.message.reply_text(
        "Compra de tokens realizada com sucesso!\n\n"
        f"Plano: {plan.name}\n"
        f"Valor: R$ {plan.price:.2f}\n"
        f"Tokens liberados: {plan.total_tokens}\n\n"
        "Voce ja pode usar /menu para consultar usando seus tokens."
    )
async def assinar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback de botao para assinar plano e comprar tokens automaticamente."""

    query = update.callback_query
    await query.answer()

    email = _get_logged_email(update)
    if not email:
        await query.message.reply_text(
            "Sua sessao expirou ou voce ainda nao fez login. "
            "Use /login seu_email@example.com para continuar."
        )
        return

    data = query.data or ""
    try:
        _, plan_id_str = data.split(":", 1)
        plan_id = int(plan_id_str)
    except ValueError:
        await query.message.reply_text("Dados de plano invalidos.")
        return

    user = UserController.get_by_email(email)
    if not user:
        await query.message.reply_text("Usuario nao encontrado. Use /registrar.")
        return

    plan = PlanController.get_plan_by_id(plan_id)
    if not plan:
        await query.message.reply_text("Plano nao encontrado.")
        return

    payment = PaymentController.create_pending(
        user_id=user.id,
        plan_id=plan_id,
        amount=float(plan.price),
        method="pix",
    )
    if not payment:
        await query.message.reply_text("Nao foi possivel criar pagamento pendente.")
        return

    confirmed = PaymentController.confirm_and_link_payment(
        user_id=user.id,
        payment_id=payment.id,
        plan_id=plan_id,
    )
    if not confirmed:
        await query.message.reply_text("Nao foi possivel confirmar o pagamento automaticamente.")
        return

    await query.message.reply_text(
        "Compra de tokens realizada com sucesso!\n\n"
        f"Plano: {plan.name}\n"
        f"Valor: R$ {plan.price:.2f}\n"
        f"Tokens liberados: {plan.total_tokens}\n\n"
        "Voce ja pode usar /menu para consultar usando seus tokens."
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Abre menu de tipos de consulta (CPF, email, telefone)."""

    email = _get_logged_email(update)
    if not email:
        await update.message.reply_text(
            "Sua sessao expirou ou voce ainda nao fez login. "
            "Use /login seu_email@example.com para continuar."
        )
        return

    if _is_busy(context):
        await update.message.reply_text(
            "Ja existe uma operacao em andamento. Aguarde a resposta antes de clicar em /menu novamente."
        )
        return

    _start_busy(context, "menu")

    user = UserController.get_by_email(email)
    if not user:
        await update.message.reply_text("Usuario nao encontrado. Use /registrar.")
        return

    # Informacoes de tokens (primeiro plano ativo)
    user_plans = PlanController.get_plans_by_user_id(user.id)
    tokens_line = "Voce nao possui nenhum plano ativo."
    if user_plans:
        current_plan = user_plans[0]
        tokens = get_user_plan_tokens(user.id, current_plan.id)
        if tokens:
            tokens_line = (
                f"Plano atual: {tokens.plan_name} | "
                f"Tokens: {tokens.remaining_tokens}/{tokens.total_tokens}"
            )
        else:
            tokens_line = f"Plano atual: {current_plan.name}, sem informacao de tokens."

    # Informacoes de tokens gratis diarios
    daily = get_today_daily_free_tokens(user.id)
    daily_remaining = daily.total_tokens - daily.used_tokens
    daily_line = f"Tokens gratis de hoje: {daily_remaining}/{daily.total_tokens}"

    # Historico recente de consultas externas
    logs = get_external_logs_by_user(user.id, limit=5)
    if logs:
        history_lines = ["Historico recente de consultas:"]
        for entry in logs:
            status = "ok" if entry["success"] else "erro"
            # Tenta extrair apenas o caminho final da URL para ficar mais legivel
            url = entry["request_url"] or "-"
            short_url = url.rsplit("/", 1)[-1] if "/" in url else url
            history_lines.append(
                f"- {entry['created_at']} | {status} | {short_url}"
            )
    else:
        history_lines = ["Nenhuma consulta registrada ainda."]

    await update.message.reply_text("\n".join([tokens_line, daily_line] + history_lines))

    keyboard = [
        [
            InlineKeyboardButton("Consultar por CPF", callback_data="consulta_cpf"),
        ],
        [
            InlineKeyboardButton("Consultar por Email", callback_data="consulta_email"),
        ],
        [
            InlineKeyboardButton("Consultar por Telefone", callback_data="consulta_phone"),
        ],
    ]

    await update.message.reply_text(
        "Escolha o tipo de consulta:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    _end_busy(context)


async def meus_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra o saldo de tokens pagos e gratuitos do usuario logado."""

    email = _get_logged_email(update)
    if not email:
        await update.message.reply_text(
            "Sua sessao expirou ou voce ainda nao fez login. "
            "Use /login seu_email@example.com para continuar."
        )
        return

    user = UserController.get_by_email(email)
    if not user:
        await update.message.reply_text("Usuario nao encontrado. Use /registrar.")
        return

    user_plans = PlanController.get_plans_by_user_id(user.id)
    tokens_line = "Voce nao possui nenhum plano ativo."
    if user_plans:
        current_plan = user_plans[0]
        tokens = get_user_plan_tokens(user.id, current_plan.id)
        if tokens:
            tokens_line = (
                f"Plano atual: {tokens.plan_name} | "
                f"Tokens: {tokens.remaining_tokens}/{tokens.total_tokens}"
            )
        else:
            tokens_line = f"Plano atual: {current_plan.name}, sem informacao de tokens."

    daily = get_today_daily_free_tokens(user.id)
    daily_remaining = daily.total_tokens - daily.used_tokens
    daily_line = f"Tokens gratis de hoje: {daily_remaining}/{daily.total_tokens}"

    await update.message.reply_text("\n".join([tokens_line, daily_line]))


async def consultar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Alias para abrir o menu de consulta rapidamente."""

    await menu(update, context)


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menu principal do admin com opcoes de relatorios e logs."""

    email = _get_logged_email(update)
    if not email or not _is_admin(email):
        await update.message.reply_text("Este comando e exclusivo para administradores.")
        return

    keyboard = [
        [
            InlineKeyboardButton("💰 Lucro hoje", callback_data="admin_profit_today"),
            InlineKeyboardButton("📆 Lucro 7 dias", callback_data="admin_profit_7d"),
        ],
        [
            InlineKeyboardButton("📆 Lucro 30 dias", callback_data="admin_profit_30d"),
        ],
        [
            InlineKeyboardButton("📄 Logs recentes", callback_data="admin_logs_recent"),
        ],
        [
            InlineKeyboardButton("👥 Usuarios", callback_data="admin_users"),
            InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton("🤖 Bot users ativos", callback_data="admin_bot_users"),
        ],
    ]

    await update.message.reply_text(
        "Painel do admin – escolha uma opcao:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trata botoes do painel admin (lucro e logs)."""

    query = update.callback_query
    await query.answer()

    email = _get_logged_email(update)
    if not email or not _is_admin(email):
        await query.message.reply_text("Acesso negado: apenas administradores.")
        return

    data = query.data or ""

    now = datetime.utcnow()

    if data == "admin_profit_today":
        start = datetime(now.year, now.month, now.day)
        end = now
    elif data == "admin_profit_7d":
        end = now
        start = end - timedelta(days=7)
    elif data == "admin_profit_30d":
        end = now
        start = end - timedelta(days=30)
    elif data == "admin_logs_recent":
        logs = get_external_logs_global(limit=10)
        if not logs:
            await query.message.reply_text("Nenhum log recente encontrado.")
            return

        lines = ["Logs recentes de consultas:"]
        for entry in logs:
            status = "ok" if entry["success"] else "erro"
            url = entry["request_url"] or "-"
            short_url = url.rsplit("/", 1)[-1] if "/" in url else url
            lines.append(
                f"- {entry['created_at']} | {status} | {short_url} | {entry['system_user_email']}"
            )

        await query.message.reply_text("\n".join(lines))
        return
    elif data == "admin_users":
        users = UserController.get_all()
        if not users:
            await query.message.reply_text("Nenhum usuario cadastrado.")
            return

        # Limita a 30 usuarios por mensagem para evitar texto muito longo
        users_slice = users[:30]
        lines = ["Usuarios cadastrados (primeiros 30):"]
        for u in users_slice:
            lines.append(
                f"- ID {u.id} | {u.name} | {u.email} | role={u.role}"
            )

        await query.message.reply_text("\n".join(lines))
        return
    elif data == "admin_bot_users":
        try:
            total = len(BotUserController.get_all_chat_ids(only_active=False))
            active = len(BotUserController.get_all_chat_ids(only_active=True))
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao obter estatisticas de bot_users")
            await query.message.reply_text("Nao foi possivel obter as estatisticas de bot_users.")
            return

        await query.message.reply_text(
            "Relatorio de bot_users:\n"
            f"Total de chats conhecidos: {total}\n"
            f"Chats marcados como ativos: {active}"
        )
        return
    elif data == "admin_broadcast":
        context.user_data["admin_broadcast_mode"] = True
        await query.message.reply_text(
            "Modo broadcast ativado. Envie agora a mensagem que deseja enviar a todos os usuarios."
        )
        return
    else:
        await query.message.reply_text("Acao de admin desconhecida.")
        return

    # Se chegamos aqui, e um dos casos de lucro
    summary = get_revenue_for_period(start, end)
    dias = (end - start).days or 1
    media_dia = summary.total_amount / dias if dias > 0 else summary.total_amount

    await query.message.reply_text(
        "Resumo de faturamento:\n"
        f"Periodo: {summary.start_date} ate {summary.end_date}\n"
        f"Total recebido: R$ {summary.total_amount:.2f}\n"
        f"Pagamentos (sucesso): {summary.total_success}\n"
        f"Ticket medio diario (aprox.): R$ {media_dia:.2f}"
    )


async def consulta_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trata clique nos botoes de consulta e pede o valor."""

    query = update.callback_query
    await query.answer()

    kind = query.data  # consulta_cpf / consulta_email / consulta_phone
    context.user_data["consulta_tipo"] = kind

    if kind == "consulta_cpf":
        msg = "Envie o CPF para consulta:"
    elif kind == "consulta_email":
        msg = "Envie o email para consulta:"
    else:
        msg = "Envie o telefone para consulta:"

    await query.message.reply_text(msg)


async def mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trata mensagens de texto apos escolha do tipo de consulta.

    Tambem usa para fluxo de codigo de login e modo broadcast do admin.
    """

    chat_id = update.effective_chat.id

    # Modo broadcast do admin: proxima mensagem enviada vira comunicado global
    if context.user_data.get("admin_broadcast_mode"):
        email = _get_logged_email(update)
        if not email or not _is_admin(email):
            context.user_data.pop("admin_broadcast_mode", None)
            await update.message.reply_text("Modo broadcast cancelado: apenas administradores podem enviar.")
            return

        text = update.message.text.strip()
        if not text:
            await update.message.reply_text("Mensagem vazia. Envie o texto que deseja enviar a todos ou /admin_menu para sair.")
            return

        # Envia a mensagem para todos os chats conhecidos do bot (persistidos em banco)
        enviados = 0
        try:
            chat_ids = BotUserController.get_all_chat_ids(only_active=True)
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao buscar chat_ids de bot_users; revertendo para SESSIONS")
            chat_ids = list(SESSIONS.keys())

        if not chat_ids:
            # Se ainda nao houver registros persistidos, usa SESSIONS como fallback
            chat_ids = list(SESSIONS.keys())

        for chat in chat_ids:
            try:
                await context.bot.send_message(chat_id=chat, text=text)
                enviados += 1
            except Exception:  # noqa: BLE001
                logger.exception("Falha ao enviar broadcast para chat %s", chat)

                # Marca chat como inativo para evitar tentativas futuras
                try:
                    BotUserController.deactivate(chat_id=chat)
                except Exception:  # noqa: BLE001
                    logger.exception("Falha ao desativar bot_user para chat %s", chat)

        context.user_data.pop("admin_broadcast_mode", None)
        await update.message.reply_text(
            f"Broadcast enviado para {enviados} chats cadastrados no bot."
        )
        return

    # Primeiro, trata fluxo de codigo de login (apos /login)
    if context.user_data.get("login_code_pending"):
        pending = PENDING_LOGINS.get(chat_id)
        if not pending:
            context.user_data.pop("login_code_pending", None)
            await update.message.reply_text(
                "Nenhum login pendente encontrado. Use /login seu_email@example.com."
            )
            return

        code_informed = update.message.text.strip()

        if datetime.now(timezone.utc) > pending["expires_at"]:
            PENDING_LOGINS.pop(chat_id, None)
            context.user_data.pop("login_code_pending", None)
            await update.message.reply_text(
                "Codigo expirado. Use /login novamente para receber um novo codigo."
            )
            return

        if code_informed != pending["code"]:
            # Controle de tentativas invalidas de codigo
            attempts = pending.get("attempts", 0) + 1
            pending["attempts"] = attempts

            if attempts >= 5:
                PENDING_LOGINS.pop(chat_id, None)
                context.user_data.pop("login_code_pending", None)
                await update.message.reply_text(
                    "Muitas tentativas invalidas de codigo. Use /login novamente para gerar um novo codigo."
                )
                return

            await update.message.reply_text(
                "Codigo invalido. Verifique o codigo enviado ao seu email."
            )
            return

        email = pending["email"]
        user = UserController.get_by_email(email)
        if not user:
            PENDING_LOGINS.pop(chat_id, None)
            context.user_data.pop("login_code_pending", None)
            await update.message.reply_text("Usuario nao encontrado. Use /registrar.")
            return

        # Verifica se este email ja esta logado em outro usuario do Telegram
        existing_user_id = ACTIVE_LOGINS.get(user.email)
        telegram_user_id = update.effective_user.id
        if existing_user_id is not None and existing_user_id != telegram_user_id:
            await update.message.reply_text(
                "Esta conta ja esta logada em outro dispositivo. "
                "Efetue logout la antes de tentar novamente."
            )
            return

        PENDING_LOGINS.pop(chat_id, None)
        context.user_data.pop("login_code_pending", None)
        SESSIONS[chat_id] = user.email
        SESSION_EXPIRATIONS[chat_id] = datetime.now(timezone.utc) + timedelta(hours=6)
        ACTIVE_LOGINS[user.email] = telegram_user_id

        # Garante registro persistente do chat_id para este usuario
        try:
            BotUserController.register_or_update(chat_id=chat_id, user_id=user.id, email=user.email)
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao registrar bot_user apos login_code_pending")

        await update.message.reply_text(
            f"Login efetuado para {user.email}. Agora voce pode usar /menu, /consultar, /meus_tokens e /comprar_tokens.",
            reply_markup=_get_logged_in_keyboard(),
        )
        return

    email = _get_logged_email(update)
    if not email:
        await update.message.reply_text(
            "Sua sessao expirou ou voce ainda nao fez login. "
            "Use /login seu_email@example.com para continuar."
        )
        return

    if _is_busy(context):
        await update.message.reply_text(
            "Ja existe uma consulta em andamento. Aguarde a resposta antes de enviar outra."
        )
        return

    tipo = context.user_data.get("consulta_tipo")
    if not tipo:
        return  # mensagem normal, fora do fluxo de consulta

    valor = update.message.text.strip()

    # Descobrir um plano ativo (pega o primeiro plano do usuario)
    user = UserController.get_by_email(email)
    if not user:
        await update.message.reply_text("Usuario nao encontrado. Use /registrar.")
        return

    user_plans = PlanController.get_plans_by_user_id(user.id)
    plan = user_plans[0] if user_plans else None

    service = ThirdPartyAPIService()

    # Monta payload generico para a API externa
    payload: Dict[str, Any] = {
        "search_type": tipo.replace("consulta_", ""),
        "search_value": valor,
        "telegram": {
            "id": update.effective_user.id,
            "username": update.effective_user.username,
            "first_name": update.effective_user.first_name,
            "last_name": update.effective_user.last_name,
        },
    }

    _start_busy(context, "consulta")

    try:
        # Executa perform_query em thread separada para nao bloquear o event loop do bot
        result = await asyncio.to_thread(
            service.perform_query,
            system_user_email=email,
            plan_id=plan.id if plan is not None else None,
            external_user_payload=payload,
        )
    except RateLimitExceeded as exc:
        await update.message.reply_text(f"Limite de 30 requisicoes/min atingido: {exc}")
        _end_busy(context)
        return

    if not result.get("success"):
        await update.message.reply_text(
            f"Falha na consulta: {result.get('error') or 'erro desconhecido'}"
        )
        _end_busy(context)
        return

    remaining = result.get("remaining_tokens")
    total = result.get("total_tokens")
    using_daily_free = bool(result.get("using_daily_free_tokens"))
    plan_active = result.get("plan_active")
    seconds_to_renew = result.get("seconds_to_renew")

    summary_lines = [
        "Consulta realizada com sucesso!",
        f"Tipo: {payload['search_type']}",
        f"Valor: {payload['search_value']}",
        "",
        f"Plano ativo: {'sim' if plan_active else 'nao'}",
        f"Tokens: {remaining}/{total if total is not None else '?'}",
    ]

    if using_daily_free:
        summary_lines.append("(Uso de tokens gratuitos diarios)")

    if seconds_to_renew is not None:
        hours = seconds_to_renew // 3600
        minutes = (seconds_to_renew % 3600) // 60
        summary_lines.append(
            f"Tempo restante para expiracao: {hours}h {minutes}min (aprox.)",
        )

    await update.message.reply_text("\n".join(summary_lines))

    # Opcional: mostrar parte da resposta externa (limitado)
    external_response = result.get("external_response")
    if isinstance(external_response, dict):
        preview = str({k: external_response.get(k) for k in list(external_response.keys())[:5]})
        await update.message.reply_text(f"Resposta da API externa (preview):\n{preview}")

    # Limpa o estado de consulta para nao reaproveitar
    context.user_data.pop("consulta_tipo", None)

    _end_busy(context)


def main() -> None:
    # Carrega variaveis do arquivo .env se python-dotenv estiver instalado
    if load_dotenv is not None:
        load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN nao definido nas variaveis de ambiente. "
            "Configure no seu .env antes de iniciar o bot."
        )

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("registrar", registrar))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(CommandHandler("confirmar_registro", confirmar_registro))
    application.add_handler(CommandHandler("confirmar_login", confirmar_login))
    application.add_handler(CommandHandler("planos", planos))
    application.add_handler(CommandHandler("assinar", assinar))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("consultar", consultar))
    application.add_handler(CommandHandler("meus_tokens", meus_tokens))
    application.add_handler(CommandHandler("comprar_tokens", planos))
    application.add_handler(CommandHandler("admin_menu", admin_menu))

    application.add_handler(
        # Botoes relacionados a consulta (cpf/email/telefone)
        CallbackQueryHandler(consulta_callback, pattern="^consulta_")
    )

    application.add_handler(
        # Botoes para assinar planos / comprar tokens
        CallbackQueryHandler(assinar_callback, pattern="^assinar:")
    )

    application.add_handler(
        # Botoes do painel admin
        CallbackQueryHandler(admin_callback, pattern="^admin_")
    )

    application.add_handler(
        # Mensagens de texto genericas, usadas apos escolha do tipo de consulta
        MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem)
    )

    logger.info("Iniciando bot do Telegram...")
    application.run_polling()


if __name__ == "__main__":
    main()
