import os
from typing import Any, Dict, Optional

import requests

from ..models.domain_core import (
	get_user_by_id,
	get_plan_by_id,
	create_pending_payment,
)


class MercadoPagoPixError(Exception):
	pass


class MercadoPagoPixService:
	"""Integração básica com Mercado Pago para pagamentos PIX.

	Fluxo principal:
	- Criar pagamento pendente interno vinculado a um plano (tokens).
	- Criar pagamento PIX no Mercado Pago e retornar o código "copia e cola".
	- Webhook do Mercado Pago consulta o pagamento e, se aprovado,
	  confirma o pagamento interno e libera os tokens (feito fora deste serviço).
	"""

	def __init__(self) -> None:
		self.access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "").strip()
		self.base_url = os.getenv("MERCADOPAGO_BASE_URL", "https://api.mercadopago.com").rstrip("/")
		self.notification_url = os.getenv("MERCADOPAGO_NOTIFICATION_URL", "").strip()

		if not self.access_token:
			raise MercadoPagoPixError(
				"MERCADOPAGO_ACCESS_TOKEN nao configurado nas variaveis de ambiente"
			)

	def _headers(self) -> Dict[str, str]:
		return {
			"Authorization": f"Bearer {self.access_token}",
			"Content-Type": "application/json",
		}

	def create_pix_payment_for_plan(self, user_id: int, plan_id: int) -> Dict[str, Any]:
		"""Cria um pagamento PIX no Mercado Pago para um plano de tokens.

		Retorna um dicionario com informacoes do pagamento interno e do PIX,
		incluindo o codigo copia e cola.
		"""

		user = get_user_by_id(user_id)
		plan = get_plan_by_id(plan_id)
		if not user or not plan:
			raise MercadoPagoPixError("Usuario ou plano invalido")

		# Cria pagamento pendente interno
		payment = create_pending_payment(
			user_id=user.id,
			plan_id=plan.id,
			amount=float(plan.price),
			method="pix",
		)
		if not payment:
			raise MercadoPagoPixError("Falha ao criar pagamento pendente interno")

		payload: Dict[str, Any] = {
			"transaction_amount": float(plan.price),
			"description": f"Compra de {plan.total_tokens} tokens - plano {plan.name}",
			"payment_method_id": "pix",
			"payer": {
				"email": user.email,
				"first_name": user.name,
			},
			"metadata": {
				"internal_payment_id": payment.id,
				"user_id": user.id,
				"plan_id": plan.id,
			},
		}

		if self.notification_url:
			payload["notification_url"] = self.notification_url

		try:
			resp = requests.post(
				f"{self.base_url}/v1/payments",
				json=payload,
				headers=self._headers(),
				timeout=20,
			)
		except Exception as exc:  # noqa: BLE001
			raise MercadoPagoPixError(f"Erro ao chamar Mercado Pago: {exc}") from exc

		if not resp.ok:
			try:
				data = resp.json()
			except ValueError:
				data = {"error": resp.text}
			raise MercadoPagoPixError(
				f"Erro do Mercado Pago (status {resp.status_code}): {data}"
			)

		try:
			data = resp.json()
		except ValueError as exc:  # noqa: BLE001
			raise MercadoPagoPixError("Resposta invalida do Mercado Pago (nao eh JSON)") from exc

		transaction_data: Optional[Dict[str, Any]] = None
		poi = data.get("point_of_interaction")
		if isinstance(poi, dict):
			transaction_data = poi.get("transaction_data")

		if not isinstance(transaction_data, dict):
			raise MercadoPagoPixError(
				"Resposta do Mercado Pago nao contem dados de PIX (transaction_data)"
			)

		pix_copia_cola = transaction_data.get("qr_code")
		qr_code_base64 = transaction_data.get("qr_code_base64")

		if not pix_copia_cola:
			raise MercadoPagoPixError(
				"Resposta do Mercado Pago nao contem o codigo PIX (qr_code)"
			)

		return {
			"internal_payment_id": payment.id,
			"user_id": user.id,
			"plan_id": plan.id,
			"amount": float(plan.price),
			"total_tokens": plan.total_tokens,
			"mercadopago_payment_id": data.get("id"),
			"mercadopago_status": data.get("status"),
			"pix_copia_cola": pix_copia_cola,
			"qr_code_base64": qr_code_base64,
		}

	def get_payment(self, mercadopago_payment_id: str | int) -> Dict[str, Any]:
		"""Busca detalhes de um pagamento no Mercado Pago pelo ID."""

		try:
			resp = requests.get(
				f"{self.base_url}/v1/payments/{mercadopago_payment_id}",
				headers=self._headers(),
				timeout=20,
			)
		except Exception as exc:  # noqa: BLE001
			raise MercadoPagoPixError(f"Erro ao consultar pagamento Mercado Pago: {exc}") from exc

		if not resp.ok:
			try:
				data = resp.json()
			except ValueError:
				data = {"error": resp.text}
			raise MercadoPagoPixError(
				f"Erro do Mercado Pago ao consultar pagamento (status {resp.status_code}): {data}"
			)

		try:
			return resp.json()
		except ValueError as exc:  # noqa: BLE001
			raise MercadoPagoPixError("Resposta invalida do Mercado Pago ao consultar pagamento") from exc
