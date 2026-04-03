import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

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
    """
    Create a HitPay PayNow payment request.
    Returns the HitPay hosted checkout URL — frontend redirects the customer there.
    """
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    try:
        result = PaymentService.create_payment_request(
            amount=request.amount,
            order_id=request.order_id,
            customer_name=request.customer_name or "",
            customer_email=request.customer_email or "",
            customer_phone=request.customer_phone or "",
        )
        return PaymentCreateResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating HitPay payment: %s", e)
        raise HTTPException(status_code=500, detail="Error creating payment")


@router.get("/status/{payment_request_id}", response_model=PaymentStatusResponse)
def get_payment_status(payment_request_id: str):
    """Poll HitPay for the current status of a payment request."""
    try:
        info = PaymentService.get_payment_status(payment_request_id)
        return PaymentStatusResponse(
            status=info["status"],
            payment_intent_id=payment_request_id,
            amount=info.get("amount"),
            currency=info.get("currency", "SGD"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting HitPay payment status: %s", e)
        raise HTTPException(status_code=500, detail="Error retrieving payment status")


@router.put("/{order_id}/payment-confirm", response_model=PaymentConfirmResponse)
def confirm_payment(
    order_id: int,
    payment_intent_id: str,
    db: Session = Depends(get_db),
):
    """
    Fallback confirm endpoint — called by frontend after returning from HitPay.
    The webhook is the primary trigger; this handles the case where the webhook
    fires after the customer is already back on the site.
    """
    try:
        # Verify with HitPay that the payment succeeded
        info = PaymentService.get_payment_status(payment_intent_id)

        # Verify ownership: reference_number must match this order_id
        expected_ref = f"GR-ORDER-{order_id}"
        if info.get("reference_number") != expected_ref:
            logger.warning(
                "HitPay ownership mismatch: pi=%s claimed order_id=%d but reference=%s",
                payment_intent_id, order_id, info.get("reference_number"),
            )
            raise HTTPException(
                status_code=400,
                detail="Payment does not match this order.",
            )

        if info["status"] == "pending":
            raise HTTPException(
                status_code=400,
                detail="Payment not completed yet.",
            )
        if info["status"] == "failed":
            raise HTTPException(
                status_code=400,
                detail="Payment failed or expired. Please create a new payment.",
            )
        if info["status"] != "succeeded":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm payment with status '{info['status']}'",
            )

        try:
            order = order_service.confirm_payment(db, order_id, payment_intent_id)
        except HTTPException as e:
            if e.status_code == 409:
                # Already confirmed by webhook — idempotent success
                order = order_service.get_order(db, order_id)
                return PaymentConfirmResponse(
                    success=True,
                    message="Payment successful! Your order has been confirmed.",
                    order_ref=order.order_ref,
                    order_status=order.order_status,
                    payment_status=order.payment_status,
                    total_price=float(order.total_price) if order.total_price else None,
                )
            raise

        return PaymentConfirmResponse(
            success=True,
            message="Payment successful! Your order has been confirmed.",
            order_ref=order.order_ref,
            order_status=order.order_status,
            payment_status=order.payment_status,
            total_price=float(order.total_price) if order.total_price else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error confirming payment for order %d: %s", order_id, e)
        raise HTTPException(status_code=500, detail="Error confirming payment")


@router.post("/hitpay-webhook")
async def hitpay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    HitPay sends a signed POST (form-encoded) here when payment status changes.
    Configure this URL in HitPay Dashboard → Payment Gateway → Webhook.
    """
    form_data = await request.form()
    payload = dict(form_data)

    received_hmac = payload.pop("hmac", "")

    # Verify HMAC signature
    if not PaymentService.verify_webhook(payload, received_hmac):
        logger.warning("HitPay webhook: invalid HMAC signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    status    = payload.get("status", "")
    reference = payload.get("reference_number", "")
    pi_id     = payload.get("payment_request_id", "")

    logger.info(
        "HitPay webhook: status=%s  reference=%s  payment_request_id=%s",
        status, reference, pi_id,
    )

    if status == "completed" and reference.startswith("GR-ORDER-"):
        try:
            order_id = int(reference.replace("GR-ORDER-", ""))
        except ValueError:
            logger.warning("HitPay webhook: cannot parse order_id from reference=%s", reference)
            return {"status": "ok"}

        try:
            order_service.confirm_payment(db, order_id, pi_id)
            logger.info("Order %d confirmed via HitPay webhook", order_id)
        except HTTPException as e:
            if e.status_code == 409:
                logger.info("Order %d already confirmed (idempotent)", order_id)
            else:
                logger.error("Failed to confirm order %d via webhook: %s", order_id, e.detail)
        except Exception as e:
            logger.error("Failed to confirm order %d via webhook: %s", order_id, e)

    elif status == "failed":
        logger.warning("HitPay webhook: payment failed  reference=%s", reference)

    # Always return 200 — HitPay retries on non-2xx
    return {"status": "ok"}
