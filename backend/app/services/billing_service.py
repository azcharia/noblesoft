"""Billing service for Midtrans transaction and webhook handling."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import hmac
import json
import logging
import time

import httpx
from supabase import Client

from app.config import settings
from app.core.database import get_supabase_admin_client
from app.core.dependencies import CurrentUser
from app.models.billing import (
    BillingAddOnCatalogItem,
    BillingAddOnSelection,
    BillingCatalogResponse,
    BillingPlanCatalogItem,
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

    def get_billing_catalog(self) -> BillingCatalogResponse:
        """Return centralized plan/add-on catalog for checkout UI."""
        plans = [
            BillingPlanCatalogItem(
                tier="basic",
                monthly_price=self._as_money(settings.BILLING_PRICE_BASIC_MONTHLY),
                annual_price=self._annual_price(settings.BILLING_PRICE_BASIC_MONTHLY),
                annual_discount_percent=settings.BILLING_ANNUAL_DISCOUNT_PERCENT,
                max_users=settings.MAX_USERS_BASIC,
            ),
            BillingPlanCatalogItem(
                tier="pro",
                monthly_price=self._as_money(settings.BILLING_PRICE_PRO_MONTHLY),
                annual_price=self._annual_price(settings.BILLING_PRICE_PRO_MONTHLY),
                annual_discount_percent=settings.BILLING_ANNUAL_DISCOUNT_PERCENT,
                max_users=settings.MAX_USERS_PRO,
            ),
            BillingPlanCatalogItem(
                tier="enterprise",
                monthly_price=self._as_money(settings.BILLING_PRICE_ENTERPRISE_MONTHLY),
                annual_price=self._annual_price(settings.BILLING_PRICE_ENTERPRISE_MONTHLY),
                annual_discount_percent=settings.BILLING_ANNUAL_DISCOUNT_PERCENT,
                max_users=settings.MAX_USERS_ENTERPRISE,
            ),
        ]

        add_ons = [
            BillingAddOnCatalogItem(
                code="ai_agent_pack",
                name="AI Agent Pack",
                description="Additional specialist AI agents for advanced workflows.",
                monthly_price=self._as_money(settings.BILLING_ADDON_AI_AGENT_MONTHLY),
                annual_price=self._annual_price(settings.BILLING_ADDON_AI_AGENT_MONTHLY),
            ),
            BillingAddOnCatalogItem(
                code="automation_pack",
                name="Automation Pack",
                description="Workflow automation pack for repetitive business operations.",
                monthly_price=self._as_money(settings.BILLING_ADDON_AUTOMATION_PACK_MONTHLY),
                annual_price=self._annual_price(settings.BILLING_ADDON_AUTOMATION_PACK_MONTHLY),
            ),
        ]

        return BillingCatalogResponse(
            currency=settings.BILLING_CURRENCY,
            annual_discount_percent=settings.BILLING_ANNUAL_DISCOUNT_PERCENT,
            plans=plans,
            add_ons=add_ons,
        )

    async def get_billing_status(self, current_user: CurrentUser) -> BillingStatusResponse:
        response = self._fetch_tenant_billing_status(current_user.tenant_id)

        if not response.data:
            raise ValueError("Tenant not found")

        tenant = response.data
        add_ons = self._normalize_active_add_ons(tenant.get("active_add_ons"))
        return BillingStatusResponse(
            tenant_id=tenant["id"],
            company_name=tenant["company_name"],
            subscription_tier=tenant["subscription_tier"],
            is_active=tenant.get("is_active", True),
            max_users=tenant.get("max_users", 5),
            payment_gateway_customer_id=tenant.get("payment_gateway_customer_id"),
            billing_period=self._normalize_billing_period(tenant.get("billing_period")),
            add_ons=add_ons,
            billing_start_date=tenant.get("billing_start_date"),
            billing_end_date=tenant.get("billing_end_date"),
        )

    async def create_midtrans_transaction(
        self,
        payload: BillingTransactionRequest,
        current_user: CurrentUser,
    ) -> BillingTransactionResponse:
        self._ensure_midtrans_configured()

        line_items = self._build_line_items(
            target_tier=payload.target_tier,
            billing_period=payload.billing_period,
            add_ons=payload.add_ons,
        )
        amount = sum((item.subtotal for item in line_items), Decimal("0.00"))
        if amount <= 0:
            raise ValueError("Calculated amount must be greater than zero")

        if payload.amount is not None:
            provided_amount = round(Decimal(payload.amount), 2)
            if provided_amount != amount:
                raise ValueError(
                    f"Provided amount does not match pricing catalog. Expected {amount}"
                )

        order_id = payload.order_id or self._build_order_id(
            tenant_id=current_user.tenant_id,
            target_tier=payload.target_tier,
            billing_period=payload.billing_period,
        )
        request_body = {
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": int(amount),
            },
            "item_details": [
                {
                    "id": item.id,
                    "price": int(item.price),
                    "quantity": item.quantity,
                    "name": item.name,
                }
                for item in line_items
            ],
            "customer_details": {
                "first_name": payload.customer_name or (current_user.full_name or current_user.email),
                "email": payload.customer_email or current_user.email,
                "phone": payload.customer_phone,
            },
            "custom_field1": current_user.tenant_id,
            "custom_field2": payload.target_tier,
            "custom_field3": self._encode_checkout_metadata(
                billing_period=payload.billing_period,
                add_ons=payload.add_ons,
                notes=payload.notes,
            ),
        }

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
            billing_period=payload.billing_period,
            line_items=line_items,
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
        billing_period = "monthly"
        add_ons: list[BillingAddOnSelection] = []

        if not tenant_id or not target_tier:
            parsed_tenant_id, parsed_tier, parsed_period = self._parse_order_id(payload.order_id)
            tenant_id = tenant_id or parsed_tenant_id
            target_tier = target_tier or parsed_tier
            billing_period = parsed_period or billing_period

        if payload.custom_field3:
            metadata = self._parse_checkout_metadata(payload.custom_field3)
            billing_period = self._normalize_billing_period(metadata.get("period"))
            add_ons = self._parse_add_ons_token(metadata.get("addons"))

        existing_event = self._find_billing_event(payload.order_id)
        if existing_event:
            return MidtransWebhookResponse(
                accepted=True,
                message="Payment webhook already processed",
                tenant_id=existing_event.get("tenant_id") or tenant_id,
                updated_tier=existing_event.get("updated_tier") or target_tier,
            )

        if not tenant_id or target_tier not in {"basic", "pro", "enterprise"}:
            return MidtransWebhookResponse(
                accepted=True,
                message="Payment settled but tenant metadata is missing",
            )

        tenant_lookup = self._fetch_tenant_for_webhook(tenant_id)

        if not tenant_lookup.data:
            return MidtransWebhookResponse(
                accepted=False,
                message="Tenant not found for webhook payload",
                tenant_id=tenant_id,
                updated_tier=target_tier,
            )

        existing_period = self._normalize_billing_period(tenant_lookup.data.get("billing_period"))
        existing_add_ons = self._normalize_active_add_ons(tenant_lookup.data.get("active_add_ons"))
        if (
            tenant_lookup.data.get("subscription_tier") == target_tier
            and existing_period == billing_period
            and self._serialize_add_ons(existing_add_ons) == self._serialize_add_ons(add_ons)
        ):
            self._record_billing_event(
                order_id=payload.order_id,
                tenant_id=tenant_id,
                updated_tier=target_tier,
                transaction_status=transaction_status,
                billing_period=billing_period,
                add_ons=add_ons,
                payload=payload,
            )
            return MidtransWebhookResponse(
                accepted=True,
                message="Subscription already up-to-date",
                tenant_id=tenant_id,
                updated_tier=target_tier,
            )

        start_at = datetime.now(timezone.utc)
        end_at = self._calculate_billing_end(start_at, billing_period)

        response = self.db.table("tenants").update(
            {
                "subscription_tier": target_tier,
                "is_active": True,
                "billing_period": billing_period,
                "active_add_ons": self._serialize_add_ons(add_ons),
                "billing_start_date": start_at.isoformat(),
                "billing_end_date": end_at.isoformat(),
                "last_billing_event_id": payload.order_id,
            }
        ).eq("id", tenant_id).execute()

        if not response.data:
            return MidtransWebhookResponse(
                accepted=False,
                message="Tenant not found for webhook payload",
                tenant_id=tenant_id,
                updated_tier=target_tier,
            )

        self._record_billing_event(
            order_id=payload.order_id,
            tenant_id=tenant_id,
            updated_tier=target_tier,
            transaction_status=transaction_status,
            billing_period=billing_period,
            add_ons=add_ons,
            payload=payload,
        )

        return MidtransWebhookResponse(
            accepted=True,
            message=f"Subscription updated from Midtrans webhook ({billing_period})",
            tenant_id=tenant_id,
            updated_tier=target_tier,
        )

    def _fetch_tenant_billing_status(self, tenant_id: str):
        try:
            return self.db.table("tenants").select(
                (
                    "id, company_name, subscription_tier, is_active, max_users, "
                    "payment_gateway_customer_id, billing_period, active_add_ons, "
                    "billing_start_date, billing_end_date"
                )
            ).eq("id", tenant_id).single().execute()
        except Exception:
            # Backward compatibility for environments that have not applied billing schema updates yet.
            return self.db.table("tenants").select(
                "id, company_name, subscription_tier, is_active, max_users, payment_gateway_customer_id"
            ).eq("id", tenant_id).single().execute()

    def _fetch_tenant_for_webhook(self, tenant_id: str):
        try:
            return self.db.table("tenants").select(
                "id, subscription_tier, billing_period, active_add_ons"
            ).eq("id", tenant_id).single().execute()
        except Exception:
            return self.db.table("tenants").select(
                "id, subscription_tier"
            ).eq("id", tenant_id).single().execute()

    def _find_billing_event(self, order_id: str) -> dict | None:
        try:
            event_response = self.db.table("billing_events").select(
                "order_id, tenant_id, updated_tier"
            ).eq("order_id", order_id).single().execute()
            return event_response.data
        except Exception:
            return None

    def _record_billing_event(
        self,
        order_id: str,
        tenant_id: str,
        updated_tier: str,
        transaction_status: str,
        billing_period: str,
        add_ons: list[BillingAddOnSelection],
        payload: MidtransWebhookRequest,
    ) -> None:
        try:
            self.db.table("billing_events").insert(
                {
                    "tenant_id": tenant_id,
                    "order_id": order_id,
                    "transaction_status": transaction_status,
                    "updated_tier": updated_tier,
                    "billing_period": billing_period,
                    "add_ons": self._serialize_add_ons(add_ons),
                    "payload": payload.model_dump(),
                }
            ).execute()
        except Exception:
            # We keep webhook processing resilient even when billing_events table is not present.
            logger.debug("Unable to persist billing event for order_id=%s", order_id)

    def _normalize_billing_period(self, value: str | None) -> str:
        return "annual" if value == "annual" else "monthly"

    def _parse_add_ons_token(self, token: str | None) -> list[BillingAddOnSelection]:
        if not token or token == "none":
            return []

        add_ons: list[BillingAddOnSelection] = []
        for entry in token.split(","):
            item = entry.strip()
            if not item:
                continue

            if ":" not in item:
                continue

            code, raw_quantity = item.split(":", 1)
            try:
                add_ons.append(
                    BillingAddOnSelection(code=code.strip(), quantity=max(1, int(raw_quantity.strip())))
                )
            except Exception:
                logger.debug("Ignoring invalid add-on token: %s", item)
        return add_ons

    def _normalize_active_add_ons(self, raw_add_ons: object) -> list[BillingAddOnSelection]:
        candidate = raw_add_ons
        if isinstance(candidate, str):
            try:
                candidate = json.loads(candidate)
            except Exception:
                return []

        if not isinstance(candidate, list):
            return []

        add_ons: list[BillingAddOnSelection] = []
        for item in candidate:
            if not isinstance(item, dict):
                continue
            try:
                add_ons.append(
                    BillingAddOnSelection(
                        code=item.get("code"),
                        quantity=item.get("quantity", 1),
                    )
                )
            except Exception:
                logger.debug("Ignoring invalid persisted add-on entry: %s", item)
        return add_ons

    def _serialize_add_ons(self, add_ons: list[BillingAddOnSelection]) -> list[dict[str, int | str]]:
        return sorted(
            [
                {
                    "code": item.code,
                    "quantity": item.quantity,
                }
                for item in add_ons
            ],
            key=lambda item: (item["code"], item["quantity"]),
        )

    def _calculate_billing_end(self, start_at: datetime, billing_period: str) -> datetime:
        return start_at + (timedelta(days=365) if billing_period == "annual" else timedelta(days=30))

    def _ensure_midtrans_configured(self) -> None:
        if not settings.MIDTRANS_SERVER_KEY:
            raise ValueError("Midtrans server key is not configured")

    def _build_midtrans_basic_auth(self) -> str:
        token = f"{settings.MIDTRANS_SERVER_KEY}:".encode("utf-8")
        return base64.b64encode(token).decode("utf-8")

    def _build_order_id(self, tenant_id: str, target_tier: str, billing_period: str) -> str:
        return f"NSFT_{tenant_id}_{target_tier}_{billing_period}_{int(time.time())}"

    def _verify_signature(self, payload: MidtransWebhookRequest) -> None:
        raw = f"{payload.order_id}{payload.status_code}{payload.gross_amount}{settings.MIDTRANS_SERVER_KEY}"
        expected = hashlib.sha512(raw.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(expected, payload.signature_key):
            raise ValueError("Invalid Midtrans webhook signature")

    def _parse_order_id(self, order_id: str) -> tuple[str | None, str | None, str | None]:
        parts = order_id.split("_")
        if len(parts) >= 5 and parts[0] == "NSFT":
            return parts[1], parts[2], parts[3]
        if len(parts) >= 4 and parts[0] == "NSFT":
            return parts[1], parts[2], "monthly"
        return None, None, None

    def _as_money(self, amount: int | Decimal) -> Decimal:
        return round(Decimal(amount), 2)

    def _annual_price(self, monthly_price: int) -> Decimal:
        multiplier = Decimal(100 - settings.BILLING_ANNUAL_DISCOUNT_PERCENT) / Decimal(100)
        return self._as_money(Decimal(monthly_price) * Decimal(12) * multiplier)

    def _price_for_period(self, monthly_price: int, billing_period: str) -> Decimal:
        if billing_period == "annual":
            return self._annual_price(monthly_price)
        return self._as_money(monthly_price)

    def _build_line_items(
        self,
        target_tier: str,
        billing_period: str,
        add_ons: list[BillingAddOnSelection],
    ) -> list[BillingTransactionResponse.BillingTransactionLineItem]:
        plan_monthly_prices = {
            "basic": settings.BILLING_PRICE_BASIC_MONTHLY,
            "pro": settings.BILLING_PRICE_PRO_MONTHLY,
            "enterprise": settings.BILLING_PRICE_ENTERPRISE_MONTHLY,
        }
        add_on_monthly_prices = {
            "ai_agent_pack": settings.BILLING_ADDON_AI_AGENT_MONTHLY,
            "automation_pack": settings.BILLING_ADDON_AUTOMATION_PACK_MONTHLY,
        }
        add_on_names = {
            "ai_agent_pack": "AI Agent Pack",
            "automation_pack": "Automation Pack",
        }

        if target_tier not in plan_monthly_prices:
            raise ValueError("Unsupported target tier")

        plan_price = self._price_for_period(plan_monthly_prices[target_tier], billing_period)
        line_items: list[BillingTransactionResponse.BillingTransactionLineItem] = [
            BillingTransactionResponse.BillingTransactionLineItem(
                id=f"plan-{target_tier}-{billing_period}",
                name=f"NobleSoft {target_tier.title()} Plan ({billing_period.title()})",
                price=plan_price,
                quantity=1,
                subtotal=plan_price,
            )
        ]

        for add_on in add_ons:
            if add_on.code not in add_on_monthly_prices:
                raise ValueError(f"Unsupported add-on code: {add_on.code}")
            add_on_price = self._price_for_period(add_on_monthly_prices[add_on.code], billing_period)
            line_items.append(
                BillingTransactionResponse.BillingTransactionLineItem(
                    id=f"addon-{add_on.code}-{billing_period}",
                    name=f"{add_on_names[add_on.code]} ({billing_period.title()})",
                    price=add_on_price,
                    quantity=add_on.quantity,
                    subtotal=self._as_money(add_on_price * add_on.quantity),
                )
            )

        return line_items

    def _encode_checkout_metadata(
        self,
        billing_period: str,
        add_ons: list[BillingAddOnSelection],
        notes: str | None,
    ) -> str:
        add_on_token = ",".join(f"{item.code}:{item.quantity}" for item in add_ons) or "none"
        note_token = (notes or "").replace(";", " ").strip()
        if note_token:
            return f"period={billing_period};addons={add_on_token};note={note_token}"
        return f"period={billing_period};addons={add_on_token}"

    def _parse_checkout_metadata(self, metadata: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for chunk in metadata.split(";"):
            if "=" not in chunk:
                continue
            key, value = chunk.split("=", 1)
            result[key.strip().lower()] = value.strip()
        return result