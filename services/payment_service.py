"""
Stripe PayNow payment service.

Uses the same PaymentIntent creation pattern as the tested
stripe_payment reference project (confirm=True + payment_method_data).
Stripe hosts the QR code image and handles bank notification via webhook.
"""
import logging

import stripe
from fastapi import HTTPException

from config.settings import settings

logger = logging.getLogger(__name__)

stripe.api_key = settings.stripe_secret_key

# Stripe status → internal status mapping
_STATUS_MAP = {
    "succeeded":               "succeeded",
    "requires_action":         "pending",   # QR shown, awaiting scan
    "processing":              "pending",
    "requires_payment_method": "expired",
    "canceled":                "expired",
}


def _extract_qr_info(payment_intent) -> dict:
    """Pull QR code fields from a PaymentIntent's next_action."""
    na = payment_intent.get("next_action")
    if na and na.get("type") == "paynow_display_qr_code":
        qr_obj = na.get("paynow_display_qr_code", {})
        return {
            "image_url_png": qr_obj.get("image_url_png"),
            "image_url_svg": qr_obj.get("image_url_svg"),
            "data":          qr_obj.get("data"),
            "expires_at":    qr_obj.get("expires_at"),
        }
    return {}


def _assert_stripe_configured():
    """Raise a clear 503 if the Stripe key is missing or is still the placeholder."""
    key = settings.stripe_secret_key
    if not key or not key.startswith("sk_"):
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured. Contact support.",
        )


class PaymentService:
    """Stripe PayNow payment processing service."""

    @staticmethod
    def create_payment_intent(amount: float, description: str, order_id: int) -> dict:
        """
        Create and immediately confirm a Stripe PaymentIntent for PayNow.
        Returns the Stripe-hosted QR image URL and raw PayNow data string.

        An idempotency_key scoped to the order prevents duplicate intents
        if the client retries the same order (double-click / network hiccup).
        """
        _assert_stripe_configured()

        amount_cents = int(round(amount * 100))

        pi = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="sgd",
            payment_method_types=["paynow"],
            confirm=True,
            payment_method_data={"type": "paynow"},
            return_url=f"{settings.app_url}/payment-complete",
            metadata={
                "order_id":    str(order_id),
                "description": description,
            },
            # Prevents duplicate PaymentIntents when a client retries the same order.
            # Stripe returns the existing PI instead of creating a new charge.
            idempotency_key=f"create-pi-order-{order_id}",
        )

        qr = _extract_qr_info(pi)
        logger.info(
            "Stripe PaymentIntent created: %s  status=%s  amount=SGD%.2f  order_id=%s",
            pi["id"], pi["status"], amount, order_id,
        )

        return {
            "payment_intent_id": pi["id"],
            "client_secret":     pi["client_secret"],
            "qr_url":            qr.get("image_url_png"),
            "qr_data":           qr.get("data"),
            "status":            _STATUS_MAP.get(pi["status"], "pending"),
            "amount":            amount,
            "currency":          "SGD",
            "expires_at":        qr.get("expires_at"),
        }

    @staticmethod
    def get_payment_status(payment_intent_id: str) -> dict:
        """
        Retrieve live payment status directly from Stripe.
        Also returns metadata_order_id so callers can verify the PI
        belongs to the expected order (prevents payment intent re-use attacks).
        """
        _assert_stripe_configured()
        pi = stripe.PaymentIntent.retrieve(payment_intent_id)
        qr = _extract_qr_info(pi)

        return {
            "payment_intent_id":  pi["id"],
            "status":             _STATUS_MAP.get(pi["status"], "pending"),
            "amount":             pi["amount"] / 100,
            "currency":           "SGD",
            "qr_url":             qr.get("image_url_png"),
            "expires_at":         qr.get("expires_at"),
            # Callers verify this matches the order_id in their request
            "metadata_order_id":  pi.get("metadata", {}).get("order_id"),
        }
