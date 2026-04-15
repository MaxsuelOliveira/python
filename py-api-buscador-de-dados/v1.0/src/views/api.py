from typing import Any, Dict, List
import os
import hmac
import hashlib
import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Header, Request
from pydantic import BaseModel, EmailStr

from ..controllers.user_controller import (
    UserController,
    PlanController,
    PaymentController,
    TokenController,
    TestController,
)
from ..models.domain_core import (
    User,
    UserCreate,
    UserUpdate,
    Plan,
    Payment,
    AssignPlanRequest,
    PaymentMethodUpdate,
    DashboardOverview,
    UserPlanTokens,
    TokenConsumeRequest,
)
from ..services.api_service import ThirdPartyAPIService, RateLimitExceeded


router = APIRouter()


API_ADMIN_KEY = os.getenv("ADMIN_API_KEY", "").strip()
PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "").strip()


async def require_admin(x_api_key: str = Header(..., alias="X-API-Key")) -> None:

    if not API_ADMIN_KEY or x_api_key != API_ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nao autorizado: X-API-Key invalida ou nao configurada",
        )


def _verify_webhook_signature(body: bytes, signature: str | None) -> None:
    """Valida a assinatura HMAC do webhook usando PAYMENT_WEBHOOK_SECRET.

    Assinatura esperada: hexdigest de HMAC-SHA256(body, secret).
    """

    if not PAYMENT_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PAYMENT_WEBHOOK_SECRET nao configurado no servidor",
        )

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura de webhook ausente",
        )

    expected = hmac.new(
        PAYMENT_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura de webhook invalida",
        )


class TestLoginRequest(BaseModel):
    """Payload de teste para login simples + plano + dados do usuário externo."""

    email: EmailStr
    plan_id: int
    user_data: Dict[str, Any]


class AdminHealthResponse(BaseModel):
    status: str
    timestamp: str
    dashboard: DashboardOverview


# -----------------------------
# Users
# -----------------------------


@router.get("/users", response_model=List[User])
async def get_all_users_view(_: None = Depends(require_admin)):  # GET ALL
    return UserController.get_all()


@router.get("/users/{user_id}", response_model=User)
async def get_user_by_id_view(user_id: int, _: None = Depends(require_admin)):  # GET BY ID
    user = UserController.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return user


@router.get("/users/by-name/{name}", response_model=List[User])
async def get_user_by_name_view(name: str, _: None = Depends(require_admin)):  # GET BY NAME
    return UserController.get_by_name(name)


@router.get("/users/by-cpf/{cpf}", response_model=User)
async def get_user_by_cpf_view(cpf: str, _: None = Depends(require_admin)):  # GET BY CPF
    user = UserController.get_by_cpf(cpf)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return user


@router.get("/users/by-email/{email}", response_model=User)
async def get_user_by_email_view(email: str, _: None = Depends(require_admin)):  # GET BY EMAIL
    user = UserController.get_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return user


@router.get("/users/by-phone/{phone}", response_model=List[User])
async def get_user_by_phone_view(phone: str, _: None = Depends(require_admin)):  # GET BY PHONE
    return UserController.get_by_phone(phone)


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user_view(data: UserCreate, _: None = Depends(require_admin)):  # POST NEW USER SYSTEM
    return UserController.create(data)


@router.put("/users/{user_id}", response_model=User)
async def update_user_view(user_id: int, data: UserUpdate, _: None = Depends(require_admin)):  # PUT UPDATE USER SYSTEM BY ID
    user = UserController.update(user_id, data)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_view(user_id: int, _: None = Depends(require_admin)):  # DELETE USER SYSTEM BY ID
    ok = UserController.delete(user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return None


@router.get("/users/by-role/{role}", response_model=List[User])
async def get_user_by_role_view(role: str, _: None = Depends(require_admin)):  # GET USER SYSTEM BY ROLE
    return UserController.get_by_role(role)


# -----------------------------
# Plans
# -----------------------------


@router.get("/plans", response_model=List[Plan])
async def get_all_plans_view(_: None = Depends(require_admin)):
    return PlanController.get_all_plans()


@router.get("/plans/{plan_id}", response_model=Plan)
async def get_plan_by_id_view(plan_id: int, _: None = Depends(require_admin)):
    plan = PlanController.get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado")
    return plan


@router.get("/users/{user_id}/plans", response_model=List[Plan])
async def get_plans_by_user_id_view(user_id: int, _: None = Depends(require_admin)):  # GET PLAN BY USER SYSTEM ID
    return PlanController.get_plans_by_user_id(user_id)


@router.post("/users/{user_id}/plans", status_code=status.HTTP_204_NO_CONTENT)
async def assign_plan_to_user_view(user_id: int, req: AssignPlanRequest, _: None = Depends(require_admin)):  # ASSIGN PLAN TO USER SYSTEM
    ok = PlanController.assign_plan(user_id, req)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário ou plano inválido")
    return None


@router.delete("/users/{user_id}/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_plan_from_user_view(user_id: int, plan_id: int, _: None = Depends(require_admin)):  # REMOVE PLAN FROM USER SYSTEM
    ok = PlanController.remove_plan(user_id, plan_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assinatura não encontrada")
    return None


@router.get("/users/{user_id}/plans/{plan_id}/tokens", response_model=UserPlanTokens)
async def get_user_plan_tokens_view(user_id: int, plan_id: int, _: None = Depends(require_admin)):
    """Retorna o saldo de tokens de um plano especifico do usuario."""
    data = TokenController.get_tokens(user_id, plan_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assinatura não encontrada")
    return data


@router.post("/users/{user_id}/plans/{plan_id}/consume-tokens", response_model=UserPlanTokens)
async def consume_tokens_view(user_id: int, plan_id: int, req: TokenConsumeRequest, _: None = Depends(require_admin)):
    """Consome uma quantidade de tokens de um plano do usuario."""
    data = TokenController.consume_tokens(user_id, plan_id, req)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assinatura não encontrada ou tokens insuficientes",
        )
    return data


# -----------------------------
# Payments
# -----------------------------


@router.get("/users/{user_id}/payments", response_model=List[Payment])
async def get_payments_by_user_id_view(user_id: int, _: None = Depends(require_admin)):  # PAYMENT HISTORY BY USER SYSTEM ID
    return PaymentController.get_history_by_user_id(user_id)


class PaymentCreateRequest(BaseModel):
    """Cria um pagamento pendente vinculado a um plano.

    Este endpoint deve ser chamado antes do gateway de pagamento.
    Depois, o webhook de confirmacao usa payment_id para confirmar.
    """

    plan_id: int
    amount: float
    method: str


@router.post("/users/{user_id}/payments", response_model=Payment, status_code=status.HTTP_201_CREATED)
async def create_pending_payment_view(user_id: int, body: PaymentCreateRequest, _: None = Depends(require_admin)):
    """Cria um registro de pagamento pendente para o usuario/plano."""

    payment = PaymentController.create_pending(
        user_id=user_id,
        plan_id=body.plan_id,
        amount=body.amount,
        method=body.method,
    )
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario ou plano invalido para criacao de pagamento",
        )

    return payment


@router.put("/users/{user_id}/payment-method", response_model=User)
async def update_payment_method_view(user_id: int, req: PaymentMethodUpdate, _: None = Depends(require_admin)):  # UPDATE PAYMENT METHOD BY USER SYSTEM ID
    user = PaymentController.update_payment_method(user_id, req)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return user


class PaymentPlanLinkRequest(BaseModel):
    """Payload para vincular um pagamento a um plano especifico.

    Pode ser usado diretamente ou via webhook de confirmacao.
    """

    user_id: int
    payment_id: int
    plan_id: int


@router.post("/payments/link-plan", response_model=Payment)
async def link_payment_to_plan_view(
    body: PaymentPlanLinkRequest,
    request: Request,
    x_signature: str | None = Header(None, alias="X-Webhook-Signature"),
):
    """Endpoint explicito para vincular plan_id a um pagamento confirmado.

    - Atualiza o registro em `payments` com plan_id e status=success.
    - Garante assinatura ativa em `user_plans` para o usuario/plano.
    """

    # Valida assinatura HMAC do webhook
    body_bytes = await request.body()
    _verify_webhook_signature(body_bytes, x_signature)

    payment = PaymentController.confirm_and_link_payment(
        user_id=body.user_id,
        payment_id=body.payment_id,
        plan_id=body.plan_id,
    )
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pagamento nao encontrado para o usuario informado",
        )

    return payment


# -----------------------------
# Webhooks de pagamento (simples / mock)
# -----------------------------


@router.post("/webhook/payment/notification")
async def webhook_payment_notification(
    request: Request,
    payload: dict,
    x_signature: str | None = Header(None, alias="X-Webhook-Signature"),
):  # WEBHOOK PAYMENT NOTIFICATION
    body_bytes = await request.body()
    _verify_webhook_signature(body_bytes, x_signature)
    # Aqui você pode adicionar lógica para registrar a notificação
    return {"received": True, "type": "notification", "payload": payload}


@router.post("/webhook/payment/confirmation")
async def webhook_payment_confirmation(
    request: Request,
    payload: Dict[str, Any],
    x_signature: str | None = Header(None, alias="X-Webhook-Signature"),
):  # WEBHOOK PAYMENT CONFIRMATION
    """Webhook de confirmacao de pagamento.

    Espera um JSON com, no minimo:
    - user_id: id do usuario no sistema
    - payment_id: id do pagamento criado anteriormente
    - plan_id: id do plano contratado

    Qualquer campo extra do gateway pode ser ignorado ou logado a parte.
    """

    # Valida assinatura HMAC do webhook
    body_bytes = await request.body()
    _verify_webhook_signature(body_bytes, x_signature)

    try:
        user_id_raw = payload.get("user_id")
        payment_id_raw = payload.get("payment_id")
        plan_id_raw = payload.get("plan_id")

        if user_id_raw is None or payment_id_raw is None or plan_id_raw is None:
            raise TypeError("Missing required fields")

        user_id = int(user_id_raw)
        payment_id = int(payment_id_raw)
        plan_id = int(plan_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload invalido: user_id, payment_id e plan_id sao obrigatorios e devem ser inteiros",
        )

    payment = PaymentController.confirm_and_link_payment(
        user_id=user_id,
        payment_id=payment_id,
        plan_id=plan_id,
    )
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pagamento nao encontrado para o usuario informado",
        )

    return {"received": True, "type": "confirmation", "payment": payment}


# -----------------------------
# Dashboard
# -----------------------------


@router.get("/dashboard/overview", response_model=DashboardOverview)
async def dashboard_overview_view(_: None = Depends(require_admin)):  # DASHBOARD STATS OVERVIEW ADMIN SYSTEM
    return PaymentController.get_dashboard_overview()


@router.get("/admin/health", response_model=AdminHealthResponse)
async def admin_health_view(_: None = Depends(require_admin)) -> AdminHealthResponse:
    overview = PaymentController.get_dashboard_overview()
    return AdminHealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat(),
        dashboard=overview,
    )


# -----------------------------
# Teste: login + consulta em API de terceiro
# -----------------------------


@router.post("/test/consulta-terceiro")
async def test_consulta_terceiro(req: TestLoginRequest, _: None = Depends(require_admin)):
    """Endpoint de teste real integrando com a API de terceiro.

    - Login simples por email + id do plano.
    - user_data: JSON com telefone, ip, nome, username etc.
    - Admin (role == "admin") nao consome tokens; demais consomem 1 token.
    - Aplica rate-limit de 30 req/min.
    - Salva o JSON do usuario externo e registra log em banco separado.
    """

    service = ThirdPartyAPIService()
    try:
        # Executa perform_query em thread separada para nao bloquear o event loop
        result = await asyncio.to_thread(
            service.perform_query,
            system_user_email=req.email,
            plan_id=req.plan_id,
            external_user_payload=req.user_data,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error") or "Falha na consulta em API de terceiro",
        )

    return result
