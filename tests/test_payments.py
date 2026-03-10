"""
Payment service and endpoint tests — Stripe PayNow integration.

Run with:  pytest tests/test_payments.py -v
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from main import app


# ---------------------------------------------------------------------------
# Helpers: fake Stripe objects
# ---------------------------------------------------------------------------

def _make_pi(
    pi_id="pi_test123",
    status="requires_action",
    amount_cents=1050,
    has_qr=True,
    order_id=1,             # metadata.order_id — must match the order_id in the request
):
    """Return a dict that mimics a Stripe PaymentIntent object."""
    qr_block = None
    if has_qr:
        qr_block = {
            "type": "paynow_display_qr_code",
            "paynow_display_qr_code": {
                "image_url_png": "https://qr.stripe.com/test.png",
                "image_url_svg": "https://qr.stripe.com/test.svg",
                "data": "00020101021226...",
                "expires_at": 9999999999,
            },
        }
    return {
        "id": pi_id,
        "client_secret": f"{pi_id}_secret_xyz",
        "status": status,
        "amount": amount_cents,
        "currency": "sgd",
        "next_action": qr_block,
        # Ownership check: confirm endpoint validates this matches order_id in the URL
        "metadata": {"order_id": str(order_id)},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """TestClient with DB dependency overridden."""
    from database.connection import get_db

    def _fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _fake_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# PaymentService unit tests
# ---------------------------------------------------------------------------

class TestPaymentService:
    def test_create_payment_intent_returns_required_fields(self):
        from services.payment_service import PaymentService
        fake_pi = _make_pi()
        with patch("stripe.PaymentIntent.create", return_value=fake_pi):
            result = PaymentService.create_payment_intent(10.50, "Test Order", 1)
        assert result["payment_intent_id"] == "pi_test123"
        assert result["status"] == "pending"
        assert result["amount"] == 10.50
        assert result["currency"] == "SGD"
        assert result["qr_url"] == "https://qr.stripe.com/test.png"
        assert result["qr_data"] == "00020101021226..."
        assert result["expires_at"] == 9999999999

    def test_create_payment_intent_no_qr(self):
        from services.payment_service import PaymentService
        fake_pi = _make_pi(has_qr=False)
        with patch("stripe.PaymentIntent.create", return_value=fake_pi):
            result = PaymentService.create_payment_intent(10.50, "No QR", 2)
        assert result["qr_url"] is None
        assert result["qr_data"] is None

    def test_create_payment_intent_amount_converted_to_cents(self):
        from services.payment_service import PaymentService
        fake_pi = _make_pi(amount_cents=2550)
        with patch("stripe.PaymentIntent.create", return_value=fake_pi) as mock_create:
            PaymentService.create_payment_intent(25.50, "Round", 3)
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["amount"] == 2550
        assert call_kwargs["currency"] == "sgd"

    def test_create_payment_intent_metadata_has_order_id(self):
        from services.payment_service import PaymentService
        fake_pi = _make_pi()
        with patch("stripe.PaymentIntent.create", return_value=fake_pi) as mock_create:
            PaymentService.create_payment_intent(10.00, "Meta test", 42)
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["metadata"]["order_id"] == "42"

    def test_get_payment_status_pending(self):
        from services.payment_service import PaymentService
        fake_pi = _make_pi(status="requires_action", amount_cents=2000)
        with patch("stripe.PaymentIntent.retrieve", return_value=fake_pi):
            result = PaymentService.get_payment_status("pi_test123")
        assert result["status"] == "pending"
        assert result["amount"] == 20.00
        assert result["payment_intent_id"] == "pi_test123"

    def test_get_payment_status_succeeded(self):
        from services.payment_service import PaymentService
        fake_pi = _make_pi(status="succeeded", has_qr=False)
        with patch("stripe.PaymentIntent.retrieve", return_value=fake_pi):
            result = PaymentService.get_payment_status("pi_test123")
        assert result["status"] == "succeeded"

    def test_get_payment_status_expired(self):
        from services.payment_service import PaymentService
        fake_pi = _make_pi(status="requires_payment_method", has_qr=False)
        with patch("stripe.PaymentIntent.retrieve", return_value=fake_pi):
            result = PaymentService.get_payment_status("pi_test123")
        assert result["status"] == "expired"

    def test_get_payment_status_cancelled_maps_to_expired(self):
        from services.payment_service import PaymentService
        fake_pi = _make_pi(status="canceled", has_qr=False)
        with patch("stripe.PaymentIntent.retrieve", return_value=fake_pi):
            result = PaymentService.get_payment_status("pi_test123")
        assert result["status"] == "expired"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestPaymentEndpoints:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_create_payment_success(self, client):
        fake_pi = _make_pi(amount_cents=1050)
        with patch("stripe.PaymentIntent.create", return_value=fake_pi):
            response = client.post(
                "/api/v1/payments/create-payment",
                json={"amount": 10.50, "description": "Garden Roots Order", "order_id": 1},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["payment_intent_id"] == "pi_test123"
        assert data["status"] == "pending"
        assert data["amount"] == 10.50
        assert data["currency"] == "SGD"
        assert data["qr_url"] == "https://qr.stripe.com/test.png"

    def test_create_payment_missing_order_id_rejected(self, client):
        response = client.post(
            "/api/v1/payments/create-payment",
            json={"amount": 10.50, "description": "No order_id"},
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_create_payment_zero_amount_rejected(self, client):
        response = client.post(
            "/api/v1/payments/create-payment",
            json={"amount": 0, "description": "Bad", "order_id": 1},
        )
        assert response.status_code == 400

    def test_create_payment_negative_amount_rejected(self, client):
        response = client.post(
            "/api/v1/payments/create-payment",
            json={"amount": -5.00, "description": "Bad", "order_id": 1},
        )
        assert response.status_code == 400

    def test_get_payment_status_pending(self, client):
        fake_pi = _make_pi(status="requires_action", amount_cents=1500)
        with patch("stripe.PaymentIntent.retrieve", return_value=fake_pi):
            response = client.get("/api/v1/payments/status/pi_test123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["payment_intent_id"] == "pi_test123"
        assert data["amount"] == 15.00
        assert data["currency"] == "SGD"

    def test_get_payment_status_succeeded(self, client):
        fake_pi = _make_pi(status="succeeded", amount_cents=1500, has_qr=False)
        with patch("stripe.PaymentIntent.retrieve", return_value=fake_pi):
            response = client.get("/api/v1/payments/status/pi_test123")
        assert response.status_code == 200
        assert response.json()["status"] == "succeeded"

    def test_confirm_payment_success(self, client):
        fake_pi = _make_pi(status="succeeded", has_qr=False)
        mock_order = MagicMock()
        mock_order.order_ref = "GR-ABC123"
        mock_order.order_status = "confirmed"
        mock_order.payment_status = "succeeded"

        with patch("stripe.PaymentIntent.retrieve", return_value=fake_pi), \
             patch("api.v1.endpoints.payments.order_service.confirm_payment", return_value=mock_order):
            response = client.put(
                "/api/v1/payments/1/payment-confirm",
                params={"payment_intent_id": "pi_test123"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Payment successful" in data["message"]
        assert data["order_ref"] == "GR-ABC123"
        assert data["order_status"] == "confirmed"
        assert data["payment_status"] == "succeeded"

    def test_confirm_payment_wrong_order_rejected(self, client):
        """PI that belongs to order 99 must not confirm order 1."""
        fake_pi = _make_pi(status="succeeded", has_qr=False, order_id=99)
        with patch("stripe.PaymentIntent.retrieve", return_value=fake_pi):
            response = client.put(
                "/api/v1/payments/1/payment-confirm",
                params={"payment_intent_id": "pi_test123"},
            )
        assert response.status_code == 400
        assert "does not match" in response.json()["error"]

    def test_confirm_payment_not_yet_paid_rejected(self, client):
        fake_pi = _make_pi(status="requires_action")
        with patch("stripe.PaymentIntent.retrieve", return_value=fake_pi):
            response = client.put(
                "/api/v1/payments/1/payment-confirm",
                params={"payment_intent_id": "pi_test123"},
            )
        assert response.status_code == 400

    def test_confirm_payment_expired_rejected(self, client):
        fake_pi = _make_pi(status="requires_payment_method", has_qr=False)
        with patch("stripe.PaymentIntent.retrieve", return_value=fake_pi):
            response = client.put(
                "/api/v1/payments/1/payment-confirm",
                params={"payment_intent_id": "pi_test123"},
            )
        assert response.status_code == 400

    def test_confirm_payment_already_confirmed_idempotent(self, client):
        """If webhook already confirmed (409), endpoint returns success anyway."""
        import fastapi
        fake_pi = _make_pi(status="succeeded", has_qr=False)
        mock_order = MagicMock()
        mock_order.order_ref = "GR-XYZ"
        mock_order.order_status = "confirmed"
        mock_order.payment_status = "succeeded"

        with patch("stripe.PaymentIntent.retrieve", return_value=fake_pi), \
             patch("api.v1.endpoints.payments.order_service.confirm_payment",
                   side_effect=fastapi.HTTPException(status_code=409, detail="already confirmed")), \
             patch("api.v1.endpoints.payments.order_service.get_order", return_value=mock_order):
            response = client.put(
                "/api/v1/payments/1/payment-confirm",
                params={"payment_intent_id": "pi_test123"},
            )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_webhook_payment_succeeded(self, client):
        """Valid webhook with payment_intent.succeeded confirms the order."""
        mock_order = MagicMock()
        event = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test123",
                    "metadata": {"order_id": "5"},
                }
            },
        }
        with patch("stripe.Webhook.construct_event", return_value=event), \
             patch("api.v1.endpoints.payments.order_service.confirm_payment", return_value=mock_order) as mock_confirm:
            response = client.post(
                "/api/v1/payments/webhook",
                content=b'{"type":"payment_intent.succeeded"}',
                headers={"stripe-signature": "t=1,v1=abc"},
            )
        assert response.status_code == 200
        assert response.json()["status"] == "received"
        mock_confirm.assert_called_once()

    def test_webhook_invalid_signature_rejected(self, client):
        import stripe as stripe_lib
        with patch("stripe.Webhook.construct_event",
                   side_effect=stripe_lib.SignatureVerificationError("bad sig", "sig_header")):
            response = client.post(
                "/api/v1/payments/webhook",
                content=b"{}",
                headers={"stripe-signature": "bad"},
            )
        assert response.status_code == 400

    def test_webhook_invalid_payload_rejected(self, client):
        with patch("stripe.Webhook.construct_event", side_effect=ValueError("bad json")):
            response = client.post(
                "/api/v1/payments/webhook",
                content=b"not json",
                headers={"stripe-signature": "t=1,v1=abc"},
            )
        assert response.status_code == 400

    def test_webhook_unhandled_event_returns_received(self, client):
        event = {"type": "customer.created", "data": {"object": {}}}
        with patch("stripe.Webhook.construct_event", return_value=event):
            response = client.post(
                "/api/v1/payments/webhook",
                content=b'{"type":"customer.created"}',
                headers={"stripe-signature": "t=1,v1=abc"},
            )
        assert response.status_code == 200
        assert response.json()["status"] == "received"
