"""Billing service for Midtrans transaction and webhook handling."""
from __future__ import annotations

import base64
from decimal import Decimal
import hashlib
import hmac
import logging
import time

import httpx
from supabase import Client

from app.config import settings
from app.core.database import get_supabase_admin_client
from app.core.dependencies import CurrentUser
from app.models.billing import (
    BillingStatusResponse,
    BillingTransactionRequest,
    BillingTransactionResponse,
    MidtransWebhookRequest,
    MidtransWebhookResponse,
)

logger = logging.getLogger(__name__)


class BillingService:
    """Service class for Midtrans-backed billing operations."""

    def __init__(self, db: Client | None = None):
        self.db = db or get_supabase_admin_client()

    async def get_billing_status(self, current_user: CurrentUser) -> BillingStatusResponse:
        response = self.db.table("tenants").select(
            "id, company_name, subscription_tier, is_active, max_users, payment_gateway_customer_id"
        ).eq("id", current_user.tenant_id).single().execute()

        if not response.data:
            raise ValueError("Tenant not found")

        tenant = response.data
        return BillingStatusResponse(
            tenant_id=tenant["id"],
            company_name=tenant["company_name"],
            subscription_tier=tenant["subscription_tier"],
            is_active=tenant.get("is_active", True),
            max_users=tenant.get("max_users", 5),
            payment_gateway_customer_id=tenant.get("payment_gateway_customer_id"),
        )

    async def create_midtrans_transaction(
        self,
        payload: BillingTransactionRequest,
        current_user: CurrentUser,
    ) -> BillingTransactionResponse:
        self._ensure_midtrans_configured()

        order_id = payload.order_id or self._build_order_id(
            tenant_id=current_user.tenant_id,
            target_tier=payload.target_tier,
        )
        amount = round(Decimal(payload.amount), 2)

        item_name = f"NobleSoft {payload.target_tier.title()} Plan"
        request_body = {
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": int(amount),
            },
            "item_details": [
                {
                    "id": f"plan-{payload.target_tier}",
                    "price": int(amount),
                    "quantity": 1,
                    "name": item_name,
                }
            ],
            "customer_details": {
                "first_name": payload.customer_name or (current_user.full_name or current_user.email),
                "email": payload.customer_email or current_user.email,
                "phone": payload.customer_phone,
            },
            "custom_field1": current_user.tenant_id,
            "custom_field2": payload.target_tier,
        }

        if payload.notes:
            request_body["custom_field3"] = payload.notes

        url = f"{settings.midtrans_api_base_url}/snap/v1/transactions"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {self._build_midtrans_basic_auth()}"
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=request_body)

        if response.status_code >= 400:
            raise Exception(f"Midtrans transaction error: {response.text}")

        body = response.json()
        token = body.get("token")
        redirect_url = body.get("redirect_url")
        if not token or not redirect_url:
            raise Exception("Midtrans response missing token or redirect_url")

        return BillingTransactionResponse(
            order_id=order_id,
            token=token,
            redirect_url=redirect_url,
            target_tier=payload.target_tier,
            amount=amount,
        )

    async def process_midtrans_webhook(
        self,
        payload: MidtransWebhookRequest,
    ) -> MidtransWebhookResponse:
        self._ensure_midtrans_configured()
        self._verify_signature(payload)

        transaction_status = payload.transaction_status.lower()
        fraud_status = (payload.fraud_status or "").lower()

        if transaction_status == "pending":
            return MidtransWebhookResponse(
                accepted=True,
                message="Payment is pending",
            )

        if transaction_status in {"deny", "cancel", "expire"}:
            return MidtransWebhookResponse(
                accepted=True,
                message=f"Payment status is {transaction_status}",
            )

        if transaction_status in {"capture", "settlement"} and fraud_status not in {"", "accept"}:
            return MidtransWebhookResponse(
                accepted=True,
                message="Payment captured but flagged by fraud check",
            )

        if transaction_status not in {"capture", "settlement"}:
            return MidtransWebhookResponse(
                accepted=True,
                message=f"Unhandled transaction status: {transaction_status}",
            )

        tenant_id = payload.custom_field1
        target_tier = payload.custom_field2

        if not tenant_id or not target_tier:
            parsed_tenant_id, parsed_tier = self._parse_order_id(payload.order_id)
            tenant_id = tenant_id or parsed_tenant_id
            target_tier = target_tier or parsed_tier

        if not tenant_id or target_tier not in {"basic", "pro", "enterprise"}:
            return MidtransWebhookResponse(
                accepted=True,
                message="Payment settled but tenant metadata is missing",
            )

        response = self.db.table("tenants").update(
            {
                "subscription_tier": target_tier,
                "is_active": True,
            }
        ).eq("id", tenant_id).execute()

        if not response.data:
            return MidtransWebhookResponse(
                accepted=False,
                message="Tenant not found for webhook payload",
                tenant_id=tenant_id,
                updated_tier=target_tier,
            )

        return MidtransWebhookResponse(
            accepted=True,
            message="Subscription updated from Midtrans webhook",
            tenant_id=tenant_id,
            updated_tier=target_tier,
        )

    def _ensure_midtrans_configured(self) -> None:
        if not settings.MIDTRANS_SERVER_KEY:
            raise ValueError("Midtrans server key is not configured")

    def _build_midtrans_basic_auth(self) -> str:
        token = f"{settings.MIDTRANS_SERVER_KEY}:".encode("utf-8")
        return base64.b64encode(token).decode("utf-8")

    def _build_order_id(self, tenant_id: str, target_tier: str) -> str:
        return f"NSFT_{tenant_id}_{target_tier}_{int(time.time())}"

    def _verify_signature(self, payload: MidtransWebhookRequest) -> None:
        raw = f"{payload.order_id}{payload.status_code}{payload.gross_amount}{settings.MIDTRANS_SERVER_KEY}"
        expected = hashlib.sha512(raw.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(expected, payload.signature_key):
            raise ValueError("Invalid Midtrans webhook signature")

    def _parse_order_id(self, order_id: str) -> tuple[str | None, str | None]:
        parts = order_id.split("_")
        if len(parts) >= 4 and parts[0] == "NSFT":
            return parts[1], parts[2]
        return None, None