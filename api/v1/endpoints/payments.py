import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from config.settings import settings
from database.connection import get_db
from services.payment_service import PaymentService
from services import order_service
from schemas.common import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentStatusResponse,
    PaymentConfirmResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create-payment", response_model=PaymentCreateResponse)
def create_payment(request: PaymentCreateRequest):
    """Create a Stripe PayNow PaymentIntent. Returns Stripe-hosted QR image URL."""
    try:
        if request.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")

        intent = PaymentService.create_payment_intent(
            request.amount, request.description, request.order_id
        )
        return PaymentCreateResponse(
            payment_intent_id=intent["payment_intent_id"],
            client_secret=intent.get("client_secret"),
            qr_url=intent.get("qr_url"),
            qr_data=intent.get("qr_data"),
            status=intent["status"],
            amount=intent["amount"],
            currency=intent.get("currency", "SGD"),
            expires_at=intent.get("expires_at"),
        )
    except HTTPException:
        raise
    except stripe.StripeError as e:
        logger.error("Stripe error creating payment: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating payment: %s", e)
        raise HTTPException(status_code=500, detail="Error creating payment")


@router.get("/status/{payment_intent_id}", response_model=PaymentStatusResponse)
def get_payment_status(payment_intent_id: str):
    """Poll Stripe for the current status of a PayNow payment."""
    try:
        status_info = PaymentService.get_payment_status(payment_intent_id)
        return PaymentStatusResponse(
            status=status_info["status"],
            payment_intent_id=payment_intent_id,
            amount=status_info.get("amount"),
            currency=status_info.get("currency", "SGD"),
        )
    except HTTPException:
        raise
    except stripe.StripeError as e:
        logger.error("Stripe error getting status: %s", e)
        raise HTTPException(status_code=404, detail="Payment not found")
    except Exception as e:
        logger.error("Error getting payment status: %s", e)
        raise HTTPException(status_code=500, detail="Error retrieving payment status")


@router.put("/{order_id}/payment-confirm", response_model=PaymentConfirmResponse)
def confirm_payment(order_id: int, payment_intent_id: str, db: Session = Depends(get_db)):
    """
    Confirm a PayNow payment and finalise the order.
    Called by the frontend when polling detects 'succeeded'.
    The Stripe webhook is the primary trigger; this is the fallback/final step.
    """
    try:
        # ── Step 1: Verify with Stripe that payment actually succeeded ──────
        status_info = PaymentService.get_payment_status(payment_intent_id)

        # ── Step 2: Verify the PI was created for THIS order ─────────────────
        # Prevents a user from passing a succeeded PI from a different order
        # to fraudulently confirm an order they haven't paid for.
        metadata_order_id = status_info.get("metadata_order_id")
        if metadata_order_id is None or metadata_order_id != str(order_id):
            logger.warning(
                "PI ownership mismatch: pi=%s claimed order_id=%d but metadata says %s",
                payment_intent_id, order_id, metadata_order_id,
            )
            raise HTTPException(
                status_code=400,
                detail="Payment intent does not match this order.",
            )

        # ── Step 3: Guard on payment state ───────────────────────────────────
        if status_info["status"] == "pending":
            raise HTTPException(
                status_code=400,
                detail="Payment not completed yet. Please complete the PayNow transfer first.",
            )
        if status_info["status"] == "expired":
            raise HTTPException(
                status_code=400,
                detail="Payment has expired. Please create a new payment.",
            )
        if status_info["status"] != "succeeded":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm payment with status '{status_info['status']}'",
            )

        # ── Step 4: Confirm in DB (SELECT FOR UPDATE serialises concurrent calls) ──
        try:
            order = order_service.confirm_payment(db, order_id, payment_intent_id)
        except HTTPException as e:
            if e.status_code == 409:
                # Already confirmed by webhook — fetch and return success
                order = order_service.get_order(db, order_id)
                return PaymentConfirmResponse(
                    success=True,
                    message="Payment successful! Your order has been confirmed.",
                    order_ref=order.order_ref,
                    order_status=order.order_status,
                    payment_status=order.payment_status,
                )
            raise

        return PaymentConfirmResponse(
            success=True,
            message="Payment successful! Your order has been confirmed.",
            order_ref=order.order_ref,
            order_status=order.order_status,
            payment_status=order.payment_status,
        )

    except HTTPException:
        raise
    except stripe.StripeError as e:
        logger.error("Stripe error confirming payment: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error confirming payment for order %d: %s", order_id, e)
        raise HTTPException(status_code=500, detail="Error confirming payment")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe sends signed events here when payment state changes.
    Run: stripe listen --forward-to localhost:8000/api/v1/payments/webhook
    """
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError as e:
        logger.warning("Webhook invalid payload: %s", e)
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError as e:
        logger.warning("Webhook signature mismatch: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")

    etype = event["type"]
    obj   = event["data"]["object"]
    pi_id = obj.get("id", "?")

    if etype == "payment_intent.succeeded":
        order_id_str = obj.get("metadata", {}).get("order_id")
        logger.info("Webhook: payment_intent.succeeded  pi=%s  order_id=%s", pi_id, order_id_str)
        if not order_id_str:
            logger.warning("Webhook: payment_intent.succeeded has no order_id in metadata  pi=%s", pi_id)
        else:
            try:
                order_service.confirm_payment(db, int(order_id_str), pi_id)
                logger.info("Order %s confirmed via webhook", order_id_str)
            except HTTPException as e:
                if e.status_code == 409:
                    logger.info("Order %s already confirmed (idempotent)", order_id_str)
                else:
                    logger.error("Failed to confirm order %s via webhook: %s", order_id_str, e.detail)
            except Exception as e:
                logger.error("Failed to confirm order %s via webhook: %s", order_id_str, e)

    elif etype == "payment_intent.payment_failed":
        logger.warning("Webhook: payment_intent.payment_failed  pi=%s  reason=%s",
                       pi_id, obj.get("last_payment_error", {}).get("message"))

    elif etype == "payment_intent.canceled":
        logger.info("Webhook: payment_intent.canceled  pi=%s", pi_id)

    else:
        logger.debug("Webhook: unhandled event type %s", etype)

    return {"status": "received"}
