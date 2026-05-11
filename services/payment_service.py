"""
HitPay payment service — PayNow via HitPay hosted checkout.

Flow:
  1. create_payment_request() → returns HitPay checkout URL
  2. Frontend redirects customer to that URL
  3. Customer pays on HitPay's page
  4. HitPay POSTs webhook to /api/v1/payments/hitpay-webhook
  5. Webhook verifies HMAC, then confirms order in DB
  6. HitPay redirects customer back to frontend with ?reference=...&status=...
"""
import hashlib
import hmac as hmac_lib
import logging

import httpx
from fastapi import HTTPException

from config.settings import settings

logger = logging.getLogger(__name__)

_SANDBOX_BASE = "https://api.sandbox.hit-pay.com/v1"
_PROD_BASE    = "https://api.hit-pay.com/v1"

_TIMEOUT   = 30   # seconds per attempt
_MAX_TRIES = 2    # retry once on timeout

# HitPay status → internal status
_STATUS_MAP = {
    "pending":   "pending",
    "completed": "succeeded",
    "failed":    "failed",
    "expired":   "failed",
}


def _api_base() -> str:
    return _SANDBOX_BASE if settings.hitpay_is_sandbox else _PROD_BASE


def _headers() -> dict:
    return {"X-BUSINESS-API-KEY": settings.hitpay_api_key}


def _assert_configured():
    if not settings.hitpay_api_key:
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured. Contact support.",
        )


async def _post(url: str, **kwargs) -> httpx.Response:
    """POST with one automatic retry on timeout."""
    for attempt in range(_MAX_TRIES):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                return await client.post(url, **kwargs)
        except httpx.TimeoutException:
            if attempt < _MAX_TRIES - 1:
                logger.warning("HitPay POST timed out (attempt %d), retrying…", attempt + 1)
            else:
                logger.error("HitPay POST timed out after %d attempts: %s", _MAX_TRIES, url)
                raise HTTPException(
                    status_code=504,
                    detail="Payment gateway timed out. Please try again.",
                )


async def _get(url: str, **kwargs) -> httpx.Response:
    """GET with one automatic retry on timeout."""
    for attempt in range(_MAX_TRIES):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                return await client.get(url, **kwargs)
        except httpx.TimeoutException:
            if attempt < _MAX_TRIES - 1:
                logger.warning("HitPay GET timed out (attempt %d), retrying…", attempt + 1)
            else:
                logger.error("HitPay GET timed out after %d attempts: %s", _MAX_TRIES, url)
                raise HTTPException(
                    status_code=504,
                    detail="Payment gateway timed out. Please try again.",
                )


class PaymentService:
    """HitPay PayNow payment processing service."""

    @staticmethod
    async def create_payment_request(
        amount: float,
        order_id: int,
        customer_name: str = "",
        customer_email: str = "",
        customer_phone: str = "",
    ) -> dict:
        """
        Create a HitPay payment request for PayNow.
        Returns the HitPay hosted checkout URL to redirect the customer to.
        reference_number encodes the order_id so it can be recovered from webhook/redirect.
        """
        _assert_configured()

        payload = {
            "amount":           f"{amount:.2f}",
            "currency":         "SGD",
            "reference_number": f"GR-ORDER-{order_id}",
            "redirect_url":     f"{settings.frontend_url}/",
        }
        # Webhook requires a public URL — skip in sandbox (localhost not allowed).
        # In production the webhook is the primary confirmation trigger.
        if not settings.hitpay_is_sandbox:
            payload["webhook"] = f"{settings.app_url}/api/v1/payments/hitpay-webhook"
            payload["payment_methods"] = ["paynow_online"]
        if customer_name:
            payload["name"] = customer_name
        if customer_email:
            payload["email"] = customer_email
        if customer_phone:
            payload["phone"] = customer_phone

        resp = await _post(
            f"{_api_base()}/payment-requests",
            json=payload,
            headers=_headers(),
        )

        if not resp.is_success:
            logger.error("HitPay create error: %s %s", resp.status_code, resp.text)
            raise HTTPException(status_code=502, detail="Payment gateway error. Please try again.")

        data = resp.json()
        logger.info(
            "HitPay payment request created: id=%s  amount=SGD%.2f  order_id=%s",
            data["id"], amount, order_id,
        )

        return {
            "payment_intent_id": data["id"],
            "payment_url":       data["url"],
            "status":            "pending",
            "amount":            amount,
            "currency":          "SGD",
        }

    @staticmethod
    async def create_payment_link(
        amount: float = None,
        order_id: int = None,
        customer_name: str = "",
        customer_email: str = "",
        customer_phone: str = "",
        allow_any_amount: bool = False,
    ) -> dict:
        """
        Create a HitPay payment link that shows ALL available payment methods.
        Returns a shareable payment link URL.
        """
        _assert_configured()

        payload = {
            "currency": "SGD",
            "reference_number": f"GR-ORDER-{order_id}" if order_id else "GR-LINK",
            "redirect_url": f"{settings.frontend_url}/",
        }

        if amount and not allow_any_amount:
            payload["amount"] = f"{amount:.2f}"

        if not settings.hitpay_is_sandbox:
            payload["webhook"] = f"{settings.app_url}/api/v1/payments/hitpay-webhook"

        if customer_name:
            payload["name"] = customer_name
        if customer_email:
            payload["email"] = customer_email
        if customer_phone:
            payload["phone"] = customer_phone

        resp = await _post(
            f"{_api_base()}/payment-requests",
            json=payload,
            headers=_headers(),
        )

        if not resp.is_success:
            logger.error("HitPay payment link create error: %s %s", resp.status_code, resp.text)
            raise HTTPException(status_code=502, detail="Payment gateway error. Please try again.")

        data = resp.json()
        logger.info(
            "HitPay payment link created: id=%s  amount=%s  order_id=%s",
            data["id"], f"SGD{amount}" if amount else "any", order_id,
        )

        return {
            "payment_link_id": data["id"],
            "payment_url": data["url"],
            "status": "pending",
            "amount": amount,
            "currency": "SGD",
            "allow_any_amount": allow_any_amount,
        }

    @staticmethod
    async def get_payment_status(payment_request_id: str) -> dict:
        """Retrieve current status of a HitPay payment request."""
        _assert_configured()

        resp = await _get(
            f"{_api_base()}/payment-requests/{payment_request_id}",
            headers=_headers(),
        )

        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Payment not found.")
        if not resp.is_success:
            logger.error("HitPay status error: %s %s", resp.status_code, resp.text)
            raise HTTPException(status_code=502, detail="Payment gateway error.")

        data = resp.json()

        # HitPay sandbox quirk: the payment *request* status can stay "pending"
        # even after the customer pays — but the nested payments[] array has the
        # real per-transaction status. Check it as the authoritative source.
        top_status = data.get("status", "pending")
        payments   = data.get("payments") or []
        if any(p.get("status") == "succeeded" for p in payments):
            resolved_status = "succeeded"
        else:
            resolved_status = _STATUS_MAP.get(top_status, "pending")

        return {
            "payment_intent_id":  data["id"],
            "status":             resolved_status,
            "amount":             float(data.get("amount", 0)),
            "currency":           "SGD",
            "reference_number":   data.get("reference_number", ""),
        }

    @staticmethod
    def verify_webhook(payload: dict, received_hmac: str) -> bool:
        """
        Verify HitPay webhook HMAC-SHA256 signature.
        Steps: sort all payload fields (excl. hmac) alphabetically,
        join as key=value&..., sign with hitpay_salt.
        """
        if not settings.hitpay_salt:
            logger.warning("HITPAY_SALT not set — skipping webhook HMAC verification")
            return True  # allow in dev when salt not configured

        sorted_string = "&".join(
            f"{k}={v}"
            for k, v in sorted(payload.items())
            if k != "hmac"
        )
        expected = hmac_lib.new(
            settings.hitpay_salt.encode("utf-8"),
            sorted_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        match = hmac_lib.compare_digest(expected, received_hmac)
        if not match:
            logger.warning(
                "HitPay HMAC mismatch — salt_last4=%s expected_last8=%s received_last8=%s",
                settings.hitpay_salt[-4:] if len(settings.hitpay_salt) >= 4 else "???",
                expected[-8:],
                received_hmac[-8:],
            )
        return match
