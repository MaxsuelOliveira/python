import os
import time
from datetime import datetime
from collections import deque
from threading import Lock
from typing import Any, Deque, Dict, Optional

import requests

from ..models.domain_core import (
    get_user_by_email,
    get_user_plan_tokens,
    consume_tokens,
    consume_daily_free_tokens,
    get_today_daily_free_tokens,
    save_external_user_payload,
    log_external_request,
)


class RateLimitExceeded(Exception):
    pass


class ThirdPartyAPIService:
    """Serviço para controlar chamadas à API de terceiros.

    - Usa HOST e SESSION_SECRET do .env/.env.production.
    - Aplica rate-limit de 30 req/min por processo.
    - Salva JSON de usuário no banco principal.
    - Registra logs de cada puxada em um SQLite separado.
    """

    _lock: Lock = Lock()
    _request_times: Deque[float] = deque()

    RATE_LIMIT: int = 30
    WINDOW_SECONDS: int = 60

    def __init__(self) -> None:
        self.base_url = os.getenv("HOST", "").rstrip("/")
        self.session_secret = os.getenv("SESSION_SECRET", "")

    @classmethod
    def _check_rate_limit(cls) -> None:
        now = time.time()
        with cls._lock:
            # Remove requests fora da janela de 60s
            while cls._request_times and now - cls._request_times[0] > cls.WINDOW_SECONDS:
                cls._request_times.popleft()

            if len(cls._request_times) >= cls.RATE_LIMIT:
                raise RateLimitExceeded("Rate limit de 30 requisicoes por minuto excedido")

            cls._request_times.append(now)

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.session_secret:
            # Usa o SESSION_SECRET em um header dedicado
            headers["X-Session-Secret"] = self.session_secret
        return headers

    def perform_query(
        self,
        system_user_email: str,
        plan_id: Optional[int],
        external_user_payload: Dict[str, Any],
        endpoint: str = "",
    ) -> Dict[str, Any]:
        """Fluxo completo de consulta em API de terceiro com controle de tokens.

        - Localiza o usuário do sistema pelo email (login).
        - Admin (role == "admin") nao consome tokens; demais consomem 1 token.
        - Salva o JSON do usuário externo no banco principal.
        - Chama a API de terceiro usando HOST + endpoint.
        - Registra o log da puxada em banco de logs separado.
        """

        user = get_user_by_email(system_user_email)
        if not user:
            return {"success": False, "error": "Usuario nao encontrado"}

        is_admin = user.role == "admin"

        # Controle de tokens (planos pagos + fallback para tokens gratis diarios)
        tokens = None
        using_daily_free = False
        daily_free = None

        if is_admin:
            if plan_id is not None:
                tokens = get_user_plan_tokens(user.id, plan_id)
        else:
            if plan_id is not None:
                tokens = consume_tokens(user.id, plan_id, 1)

            # Se nao houver assinatura/tokens suficientes, tenta usar tokens gratis diarios
            if tokens is None:
                daily_free = consume_daily_free_tokens(user.id, 1)
                if daily_free is None:
                    return {
                        "success": False,
                        "error": (
                            "Sem tokens disponiveis. Assine um plano ou aguarde o proximo dia "
                            "para renovar seus 3 tokens gratuitos."
                        ),
                    }
                using_daily_free = True

        # Informacoes de plano/assinatura para retorno
        plan_active: Optional[bool]
        plan_expires_at: Optional[str]
        seconds_to_renew: Optional[int]
        total_tokens: Optional[int]
        remaining_tokens: Optional[int]

        plan_active = None
        plan_expires_at = None
        seconds_to_renew = None
        total_tokens = None
        remaining_tokens = None

        if tokens is not None:
            total_tokens = tokens.total_tokens
            remaining_tokens = tokens.remaining_tokens
            plan_expires_at = tokens.end_date

            if tokens.end_date:
                try:
                    end_dt = datetime.fromisoformat(tokens.end_date)
                    now_dt = datetime.utcnow()
                    delta = end_dt - now_dt
                    seconds = int(delta.total_seconds())
                    if seconds < 0:
                        seconds = 0
                    seconds_to_renew = seconds
                    plan_active = bool(tokens.active and seconds_to_renew > 0)
                except Exception:  # noqa: BLE001
                    plan_active = bool(tokens.active)
                    seconds_to_renew = None
            else:
                plan_active = bool(tokens.active)
        elif is_admin:
            # Admin: considera acesso ilimitado, sem expiracao
            plan_active = True
            plan_expires_at = None
            seconds_to_renew = None
            total_tokens = None
            remaining_tokens = None
        elif using_daily_free and daily_free is not None:
            # Tokens gratuitos diarios: 3 por dia, renovados a cada dia
            total_tokens = daily_free.total_tokens
            remaining_tokens = daily_free.total_tokens - daily_free.used_tokens

            # Considera como "ativo" ate o final do dia UTC
            now_dt = datetime.utcnow()
            end_of_day = datetime.combine(now_dt.date(), datetime.max.time())
            delta = end_of_day - now_dt
            seconds = int(delta.total_seconds())
            if seconds < 0:
                seconds = 0
            seconds_to_renew = seconds
            plan_active = seconds_to_renew > 0
            plan_expires_at = end_of_day.isoformat()

        # Salva JSON de usuario externo no banco principal
        external_user_id = save_external_user_payload(
            system_user_id=user.id,
            system_user_email=user.email,
            plan_id=plan_id if plan_id is not None else None,
            payload=external_user_payload,
        )

        # Prepara chamada HTTP
        if not self.base_url:
            # Se nao houver HOST configurado, apenas simula a chamada
            request_url = ""
            status_code = 0
            external_response: Dict[str, Any] = {
                "provider": "third_party_mock",
                "status": "OK",
                "detail": "HOST nao configurado; resposta simulada.",
            }
            success = True
            error_message: Optional[str] = None
        else:
            self._check_rate_limit()

            path = endpoint.lstrip("/")
            request_url = f"{self.base_url}/{path}" if path else self.base_url

            headers = self._build_headers()

            try:
                resp = requests.post(request_url, json=external_user_payload, headers=headers, timeout=15)
                status_code = resp.status_code
                success = resp.ok
                try:
                    external_response = resp.json()
                except ValueError:
                    external_response = {"text": resp.text}
                error_message = None if success else f"HTTP {status_code}"
            except Exception as exc:  # noqa: BLE001
                status_code = 0
                success = False
                external_response = {}
                error_message = str(exc)

        # Sempre registra o log no banco separado
        log_external_request(
            system_user_id=user.id,
            system_user_email=user.email,
            plan_id=plan_id if plan_id is not None else None,
            external_user_id=external_user_id,
            request_url=request_url,
            status_code=status_code,
            success=success,
            error_message=error_message,
        )

        return {
            "success": success,
            "user_email": user.email,
            "plan_id": plan_id,
            "is_admin": is_admin,
            "total_tokens": total_tokens,
            "remaining_tokens": remaining_tokens,
            "plan_active": plan_active,
            "plan_expires_at": plan_expires_at,
            "seconds_to_renew": seconds_to_renew,
            "using_daily_free_tokens": using_daily_free,
            "external_user_id": external_user_id,
            "request_url": request_url,
            "status_code": status_code,
            "error": error_message,
            "external_response": external_response,
        }
