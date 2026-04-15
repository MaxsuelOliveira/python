from typing import List, Optional

from ..models.domain_core import (
    User,
    UserCreate,
    UserUpdate,
    Plan,
    Payment,
    DashboardOverview,
    AssignPlanRequest,
    PaymentMethodUpdate,
    UserPlanTokens,
    TokenConsumeRequest,
    register_or_update_bot_user,
    get_all_bot_chat_ids,
    deactivate_bot_user,
    get_all_users,
    get_user_by_id,
    get_user_by_name,
    get_user_by_cpf,
    get_user_by_email,
    get_user_by_phone,
    get_users_by_role,
    create_user,
    update_user,
    delete_user,
    get_plans,
    get_plan_by_id,
    get_plans_by_user_id,
    assign_plan_to_user,
    remove_plan_from_user,
    get_user_plan_tokens,
    consume_tokens,
    get_payments_by_user_id,
    update_payment_method,
    get_dashboard_overview,
    confirm_payment_and_link_plan,
    create_pending_payment,
    get_all_user_emails,
)


class UserController:
    @staticmethod
    def get_all() -> List[User]:
        return get_all_users()

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        return get_user_by_id(user_id)

    @staticmethod
    def get_by_name(name: str) -> List[User]:
        return get_user_by_name(name)

    @staticmethod
    def get_by_cpf(cpf: str) -> Optional[User]:
        return get_user_by_cpf(cpf)

    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        return get_user_by_email(email)

    @staticmethod
    def get_by_phone(phone: str) -> List[User]:
        return get_user_by_phone(phone)

    @staticmethod
    def get_by_role(role: str) -> List[User]:
        return get_users_by_role(role)

    @staticmethod
    def create(data: UserCreate) -> User:
        return create_user(data)

    @staticmethod
    def update(user_id: int, data: UserUpdate) -> Optional[User]:
        return update_user(user_id, data)

    @staticmethod
    def delete(user_id: int) -> bool:
        return delete_user(user_id)

    @staticmethod
    def get_all_emails() -> List[str]:
        return get_all_user_emails()


class BotUserController:
    """Operacoes relacionadas aos usuarios do bot (mapeamento chat_id)."""

    @staticmethod
    def register_or_update(chat_id: int, user_id: Optional[int] = None, email: Optional[str] = None) -> None:
        return register_or_update_bot_user(chat_id=chat_id, user_id=user_id, email=email)

    @staticmethod
    def get_all_chat_ids(only_active: bool = True) -> list[int]:
        return get_all_bot_chat_ids(only_active=only_active)

    @staticmethod
    def deactivate(chat_id: int) -> None:
        return deactivate_bot_user(chat_id=chat_id)


class PlanController:
    @staticmethod
    def get_all_plans() -> List[Plan]:
        return get_plans()

    @staticmethod
    def get_plan_by_id(plan_id: int) -> Optional[Plan]:
        return get_plan_by_id(plan_id)

    @staticmethod
    def get_plans_by_user_id(user_id: int) -> List[Plan]:
        return get_plans_by_user_id(user_id)

    @staticmethod
    def assign_plan(user_id: int, req: AssignPlanRequest) -> bool:
        return assign_plan_to_user(user_id, req.plan_id)

    @staticmethod
    def remove_plan(user_id: int, plan_id: int) -> bool:
        return remove_plan_from_user(user_id, plan_id)


class PaymentController:
    @staticmethod
    def get_history_by_user_id(user_id: int) -> List[Payment]:
        return get_payments_by_user_id(user_id)

    @staticmethod
    def update_payment_method(user_id: int, req: PaymentMethodUpdate) -> Optional[User]:
        return update_payment_method(user_id, req.payment_method)

    @staticmethod
    def get_dashboard_overview() -> DashboardOverview:
        return get_dashboard_overview()

    @staticmethod
    def confirm_and_link_payment(user_id: int, payment_id: int, plan_id: int) -> Optional[Payment]:
        return confirm_payment_and_link_plan(user_id=user_id, payment_id=payment_id, plan_id=plan_id)

    @staticmethod
    def create_pending(user_id: int, plan_id: int, amount: float, method: str) -> Optional[Payment]:
        return create_pending_payment(user_id=user_id, plan_id=plan_id, amount=amount, method=method)


class TokenController:
    @staticmethod
    def get_tokens(user_id: int, plan_id: int) -> Optional[UserPlanTokens]:
        return get_user_plan_tokens(user_id, plan_id)

    @staticmethod
    def consume_tokens(user_id: int, plan_id: int, req: TokenConsumeRequest) -> Optional[UserPlanTokens]:
        return consume_tokens(user_id, plan_id, req.amount)


class TestController:
    """Controller para fluxo de teste de login + consulta em API de terceiro.

    Regra:
    - Admin (role == "admin"): nao consome tokens (acesso ilimitado).
    - Usuario comum: consome sempre 1 token do plano informado.
    """

    @staticmethod
    def third_party_query(email: str, plan_id: int) -> Optional[dict]:
        user = get_user_by_email(email)
        if not user:
            return None

        is_admin = user.role == "admin"

        if is_admin:
            tokens = get_user_plan_tokens(user.id, plan_id)
        else:
            tokens = consume_tokens(user.id, plan_id, 1)
            if not tokens:
                # Sem assinatura ativa ou sem saldo de tokens
                return None

        # Aqui seria feita a chamada real para a API de terceiro.
        # Para teste, vamos apenas simular um payload de retorno.
        external_data = {
            "provider": "third_party_mock",
            "status": "OK",
            "detail": "Consulta em API de terceiro simulada com sucesso.",
        }

        return {
            "user_email": user.email,
            "plan_id": plan_id,
            "is_admin": is_admin,
            "remaining_tokens": tokens.remaining_tokens if tokens else None,
            "external_data": external_data,
        }
