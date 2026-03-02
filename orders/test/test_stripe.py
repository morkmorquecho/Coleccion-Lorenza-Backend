# orders/tests/test_views.py
import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework import status

from orders.models import (
    Coupon, CouponUsage, Order, OrderItem, Payment, ShippingTracking
)


# ===========================================================================
# Base fixtures
# ===========================================================================

class OrderTestBase(TestCase):
    """Common fixtures shared across all test classes."""

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser", password="pass", email="test@example.com"
        )
        self.other_user = User.objects.create_user(
            username="other", password="pass", email="other@example.com"
        )

        self.address = self._create_address(self.user)
        self.other_address = self._create_address(self.other_user)
        self.piece = self._create_piece(title="Obra 1", price=Decimal("500.00"), quantity=10)

        today = timezone.now().date()
        self.coupon = Coupon.objects.create(
            code="DESCUENTO20",
            percentage=Decimal("20.0"),
            valid_from=today,
            valid_until=today + timezone.timedelta(days=30),
        )
        self.expired_coupon = Coupon.objects.create(
            code="VENCIDO",
            percentage=Decimal("10.0"),
            valid_from=today - timezone.timedelta(days=60),
            valid_until=today - timezone.timedelta(days=1),
        )

    def _create_address(self, user):
        from users.models import Address
        return Address.objects.create(
            user=user,
            recipient_name="Juan Pérez",
            country="mexico",
            state="CDMX",
            city="Ciudad de México",
            postal_code="06600",
            neighborhood="Roma Norte",
            street="Calle 1",
            street_number=123,
            phone_number="+5215512345678",
            reference="Casa color blanco",
            apartment_number="2B",
            is_default=True,
        )
    
    def _create_piece(self, title, price, quantity):
        from pieces.models import Piece, TypePiece, Section
        from django.core.files.uploadedfile import SimpleUploadedFile
        type_piece, _ = TypePiece.objects.get_or_create(
            type="Pintura",
            key="painting"
        )
        
        section, _ = Section.objects.get_or_create(
            section="Colección Principal",
            key="main-collection"
        )
        
        type_piece = TypePiece.objects.first()
        section = Section.objects.first()

        thumbnail = SimpleUploadedFile(
            name="test.jpg",
            content=b"fake-image-content",
            content_type="image/jpeg"
        )
        return Piece.objects.create(
            title=title,
            slug=title.lower().replace(" ", "-"),
            description="Descripción de prueba",
            quantity=quantity,
            price_base=Decimal(price),
            width=Decimal("10.0"),
            height=Decimal("5.0"),
            length=Decimal("20.0"),
            weight=Decimal("2.5"),
            customizable=False,
            featured=False,
            type=type_piece,
            section=section,
            thumbnail_path=thumbnail,
        )
    
    def _authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def _checkout_payload(self, piece=None, quantity=1, coupon_code=None):
        piece = piece or self.piece
        payload = {
            "address": self.address.id,
            "payment_method": "card",
            "items": [{"piece": piece.id, "quantity": quantity}],
        }
        if coupon_code:
            payload["coupon_code"] = coupon_code
        return payload


# ===========================================================================
# CheckoutView  — POST /api/v1/orders/checkout/
# ===========================================================================

class CheckoutViewTest(OrderTestBase):
    URL = "/api/v1/orders/checkout/"

    # ---- authentication ----

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(self.URL, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- happy path ----

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_successful_checkout_returns_201_with_expected_keys(self, mock_pi):
        mock_pi.return_value = {"id": "pi_abc123", "client_secret": "secret_xyz"}
        self._authenticate()

        resp = self.client.post(self.URL, self._checkout_payload(), format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("order_id", resp.data)
        self.assertIn("client_secret", resp.data)
        self.assertIn("publishable_key", resp.data)
        self.assertEqual(resp.data["client_secret"], "secret_xyz")

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_successful_checkout_creates_order_with_pending_status(self, mock_pi):
        mock_pi.return_value = {"id": "pi_abc123", "client_secret": "s"}
        self._authenticate()

        resp = self.client.post(self.URL, self._checkout_payload(), format="json")

        order = Order.objects.get(id=resp.data["order_id"])
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.address, self.address)

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_successful_checkout_creates_payment_with_stripe_id(self, mock_pi):
        mock_pi.return_value = {"id": "pi_abc123", "client_secret": "s"}
        self._authenticate()

        resp = self.client.post(self.URL, self._checkout_payload(), format="json")

        payment = Order.objects.get(id=resp.data["order_id"]).payment_set.first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.external_id, "pi_abc123")
        self.assertEqual(payment.status, "pending")

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_stock_is_decremented_after_checkout(self, mock_pi):
        mock_pi.return_value = {"id": "pi_xyz", "client_secret": "s"}
        self._authenticate()
        initial_qty = self.piece.quantity

        self.client.post(self.URL, self._checkout_payload(quantity=3), format="json")

        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantity, initial_qty - 3)

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_order_total_is_calculated_correctly(self, mock_pi):
        mock_pi.return_value = {"id": "pi_t", "client_secret": "s"}
        self._authenticate()

        resp = self.client.post(self.URL, self._checkout_payload(quantity=2), format="json")

        order = Order.objects.get(id=resp.data["order_id"])
        expected = self.piece.get_final_price("mx") * 2
        self.assertEqual(order.total, expected)

    # ---- coupon ----

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_checkout_with_valid_coupon_applies_discount(self, mock_pi):
        mock_pi.return_value = {"id": "pi_coup", "client_secret": "s"}
        self._authenticate()

        resp = self.client.post(
            self.URL, self._checkout_payload(coupon_code="DESCUENTO20"), format="json"
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(id=resp.data["order_id"])
        subtotal = self.piece.get_final_price("mx")
        expected_discount = (subtotal * Decimal("20.0") / Decimal("100")).quantize(Decimal("0.01"))
        self.assertEqual(order.total, subtotal - expected_discount)

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_checkout_with_valid_coupon_creates_coupon_usage(self, mock_pi):
        mock_pi.return_value = {"id": "pi_cu", "client_secret": "s"}
        self._authenticate()

        resp = self.client.post(
            self.URL, self._checkout_payload(coupon_code="DESCUENTO20"), format="json"
        )

        order = Order.objects.get(id=resp.data["order_id"])
        usage = CouponUsage.objects.get(order=order)
        self.assertEqual(usage.coupon, self.coupon)
        self.assertEqual(usage.user, self.user)

    def test_checkout_with_expired_coupon_returns_400(self):
        self._authenticate()
        resp = self.client.post(
            self.URL, self._checkout_payload(coupon_code="VENCIDO"), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_with_nonexistent_coupon_returns_400(self):
        self._authenticate()
        resp = self.client.post(
            self.URL, self._checkout_payload(coupon_code="FAKE99"), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_coupon_cannot_be_reused_by_same_user(self, mock_pi):
        mock_pi.return_value = {"id": "pi_ru", "client_secret": "s"}
        self._authenticate()

        self.client.post(
            self.URL, self._checkout_payload(coupon_code="DESCUENTO20"), format="json"
        )
        # Reset stock so the second request doesn't fail on stock
        self.piece.quantity = 10
        self.piece.save()

        resp = self.client.post(
            self.URL, self._checkout_payload(coupon_code="DESCUENTO20"), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_same_coupon_can_be_used_by_different_users(self, mock_pi):
        mock_pi.return_value = {"id": "pi_u1", "client_secret": "s"}
        self._authenticate(self.user)
        r1 = self.client.post(
            self.URL, self._checkout_payload(coupon_code="DESCUENTO20"), format="json"
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)

        # Reset stock and use a different address for other_user
        self.piece.quantity = 10
        self.piece.save()
        mock_pi.return_value = {"id": "pi_u2", "client_secret": "s2"}
        self._authenticate(self.other_user)
        payload = {
            "address": self.other_address.id,
            "payment_method": "card",
            "items": [{"piece": self.piece.id, "quantity": 1}],
            "coupon_code": "DESCUENTO20",
        }
        r2 = self.client.post(self.URL, payload, format="json")
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)

    # ---- validation ----

    def test_insufficient_stock_returns_400(self):
        self._authenticate()
        resp = self.client.post(
            self.URL,
            self._checkout_payload(quantity=self.piece.quantity + 1),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_items_list_returns_400(self):
        self._authenticate()
        payload = {"address": self.address.id, "payment_method": "card", "items": []}
        resp = self.client.post(self.URL, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_address_belonging_to_other_user_returns_400(self):
        self._authenticate()
        payload = {
            "address": self.other_address.id,
            "payment_method": "card",
            "items": [{"piece": self.piece.id, "quantity": 1}],
        }
        resp = self.client.post(self.URL, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_payment_method_returns_400(self):
        self._authenticate()
        payload = self._checkout_payload()
        payload["payment_method"] = "bitcoin"
        resp = self.client.post(self.URL, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- stripe error handling ----

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_stripe_error_returns_502(self, mock_pi):
        import stripe as stripe_lib
        mock_pi.side_effect = stripe_lib.error.StripeError("Network error")
        self._authenticate()

        resp = self.client.post(self.URL, self._checkout_payload(), format="json")

        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_stripe_error_rolls_back_order_creation(self, mock_pi):
        import stripe as stripe_lib
        mock_pi.side_effect = stripe_lib.error.StripeError("Network error")
        self._authenticate()

        self.client.post(self.URL, self._checkout_payload(), format="json")

        self.assertFalse(Order.objects.filter(user=self.user).exists())

    @patch("orders.views.stripe.PaymentIntent.create")
    def test_stripe_error_rolls_back_stock_decrement(self, mock_pi):
        import stripe as stripe_lib
        mock_pi.side_effect = stripe_lib.error.StripeError("fail")
        self._authenticate()
        initial_qty = self.piece.quantity

        self.client.post(self.URL, self._checkout_payload(quantity=2), format="json")

        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantity, initial_qty)


# ===========================================================================
# StripeWebhookView  — POST /api/v1/orders/webhook/
# ===========================================================================

class StripeWebhookViewTest(OrderTestBase):
    URL = "/api/v1/orders/webhook/"

    def setUp(self):
        super().setUp()
        self.order = Order.objects.create(
            user=self.user, address=self.address,
            total=Decimal("500.00"), status="pending",
        )
        self.payment = Payment.objects.create(
            order=self.order, amount=Decimal("500.00"),
            payment_method="card", external_id="pi_webhook_test", status="pending",
        )
        OrderItem.objects.create(
            order=self.order, piece=self.piece,
            quantity=2, price_snapshot=Decimal("500.00"),
        )
        # Simulate stock already decremented by checkout
        self.piece.quantity -= 2
        self.piece.save()

    def _post_webhook(self, event_type, payment_intent_id="pi_webhook_test"):
        with patch("orders.views.stripe.Webhook.construct_event") as mock_event:
            mock_event.return_value = {
                "type": event_type,
                "data": {"object": {"id": payment_intent_id}},
            }
            return self.client.post(
                self.URL,
                data=json.dumps({"dummy": True}),
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
            )

    # ---- signature / auth ----

    def test_invalid_payload_returns_400(self):
        with patch("orders.views.stripe.Webhook.construct_event", side_effect=ValueError):
            resp = self.client.post(
                self.URL, data="bad", content_type="application/json",
                HTTP_STRIPE_SIGNATURE="bad",
            )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_signature_returns_400(self):
        import stripe as stripe_lib
        with patch(
            "orders.views.stripe.Webhook.construct_event",
            side_effect=stripe_lib.error.SignatureVerificationError("bad", "hdr"),
        ):
            resp = self.client.post(
                self.URL, data="bad", content_type="application/json",
                HTTP_STRIPE_SIGNATURE="bad",
            )
        self.assertEqual(resp.status_code, 400)

    def test_no_auth_required_valid_event_returns_200(self):
        """Webhook endpoint must be publicly reachable without user auth."""
        resp = self._post_webhook("payment_intent.succeeded")
        self.assertEqual(resp.status_code, 200)

    # ---- payment_intent.succeeded ----

    def test_succeeded_marks_order_as_paid(self):
        self._post_webhook("payment_intent.succeeded")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "paid")

    def test_succeeded_marks_payment_as_completed(self):
        self._post_webhook("payment_intent.succeeded")
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "completed")

    def test_succeeded_creates_shipping_tracking(self):
        self._post_webhook("payment_intent.succeeded")
        self.assertTrue(ShippingTracking.objects.filter(order=self.order).exists())

    def test_succeeded_idempotent_on_duplicate_event(self):
        self._post_webhook("payment_intent.succeeded")
        resp = self._post_webhook("payment_intent.succeeded")   # duplicate

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ShippingTracking.objects.filter(order=self.order).count(), 1)

    def test_succeeded_unknown_payment_intent_silently_ignored(self):
        resp = self._post_webhook("payment_intent.succeeded", "pi_unknown")
        self.assertEqual(resp.status_code, 200)

    # ---- payment_intent.payment_failed ----

    def test_payment_failed_cancels_order(self):
        self._post_webhook("payment_intent.payment_failed")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "cancelled")

    def test_payment_failed_marks_payment_as_failed(self):
        self._post_webhook("payment_intent.payment_failed")
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "failed")

    def test_payment_failed_restores_stock(self):
        stock_before = self.piece.quantity
        self._post_webhook("payment_intent.payment_failed")
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantity, stock_before + 2)

    # ---- payment_intent.canceled ----

    def test_canceled_cancels_order(self):
        self._post_webhook("payment_intent.canceled")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "cancelled")

    def test_canceled_restores_stock(self):
        stock_before = self.piece.quantity
        self._post_webhook("payment_intent.canceled")
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantity, stock_before + 2)

    def test_canceled_idempotent_if_already_failed(self):
        """Second canceled event must NOT restore stock a second time."""
        self.payment.status = "failed"
        self.payment.save()
        stock_before = self.piece.quantity

        resp = self._post_webhook("payment_intent.canceled")

        self.assertEqual(resp.status_code, 200)
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantity, stock_before)     # unchanged

    # ---- unhandled event ----

    def test_unhandled_event_type_returns_200(self):
        resp = self._post_webhook("customer.created")
        self.assertEqual(resp.status_code, 200)


# ===========================================================================
# CancelOrderView  — POST /api/v1/orders/<pk>/cancel/
# ===========================================================================

class CancelOrderViewTest(OrderTestBase):

    def _cancel_url(self, pk):
        return f"/api/v1/orders/{pk}/cancel/"

    def _make_order(self, user=None, order_status="pending",
                    payment_status="pending", payment_external_id="pi_cancel_test"):
        user = user or self.user
        order = Order.objects.create(
            user=user, address=self.address,
            total=Decimal("500.00"), status=order_status,
        )
        payment = Payment.objects.create(
            order=order, amount=Decimal("500.00"), payment_method="card",
            external_id=payment_external_id, status=payment_status,
        )
        OrderItem.objects.create(
            order=order, piece=self.piece, quantity=2,
            price_snapshot=Decimal("500.00"),
        )
        self.piece.quantity -= 2
        self.piece.save()
        return order, payment

    # ---- auth / ownership ----

    def test_unauthenticated_returns_401(self):
        order, _ = self._make_order()
        resp = self.client.post(self._cancel_url(order.pk))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_other_users_order_returns_404(self):
        order, _ = self._make_order(user=self.other_user)
        self._authenticate()
        resp = self.client.post(self._cancel_url(order.pk))
        self.assertEqual(resp.status_code, 404)

    def test_nonexistent_order_returns_404(self):
        self._authenticate()
        resp = self.client.post(self._cancel_url(99999))
        self.assertEqual(resp.status_code, 404)

    # ---- status guards ----

    def test_cannot_cancel_shipped_order(self):
        order, _ = self._make_order(order_status="shipped")
        self._authenticate()
        resp = self.client.post(self._cancel_url(order.pk))
        self.assertEqual(resp.status_code, 400)

    def test_cannot_cancel_already_cancelled_order(self):
        order, _ = self._make_order(order_status="cancelled")
        self._authenticate()
        resp = self.client.post(self._cancel_url(order.pk))
        self.assertEqual(resp.status_code, 400)

    # ---- pending order cancellation ----

    @patch("orders.views.stripe.PaymentIntent.cancel")
    def test_cancel_pending_order_returns_200(self, _mock):
        order, _ = self._make_order()
        self._authenticate()
        resp = self.client.post(self._cancel_url(order.pk))
        self.assertEqual(resp.status_code, 200)

    @patch("orders.views.stripe.PaymentIntent.cancel")
    def test_cancel_pending_calls_stripe_cancel_with_correct_id(self, mock_cancel):
        order, _ = self._make_order(payment_external_id="pi_live_123")
        self._authenticate()

        self.client.post(self._cancel_url(order.pk))

        mock_cancel.assert_called_once_with("pi_live_123")

    @patch("orders.views.stripe.PaymentIntent.cancel")
    def test_cancel_pending_updates_order_and_payment_status(self, _mock):
        order, payment = self._make_order()
        self._authenticate()

        self.client.post(self._cancel_url(order.pk))

        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(payment.status, "failed")

    @patch("orders.views.stripe.PaymentIntent.cancel")
    def test_cancel_pending_restores_stock(self, _mock):
        order, _ = self._make_order()
        stock_before = self.piece.quantity
        self._authenticate()

        self.client.post(self._cancel_url(order.pk))

        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantity, stock_before + 2)

    @patch("orders.views.stripe.PaymentIntent.cancel")
    def test_cancel_pending_stripe_already_cancelled_still_returns_200(self, mock_cancel):
        import stripe as stripe_lib
        mock_cancel.side_effect = stripe_lib.error.InvalidRequestError("already cancelled", "param")
        order, _ = self._make_order()
        self._authenticate()

        resp = self.client.post(self._cancel_url(order.pk))
        self.assertEqual(resp.status_code, 200)

    @patch("orders.views.stripe.PaymentIntent.cancel")
    def test_cancel_pending_placeholder_external_id_skips_stripe(self, mock_cancel):
        """When external_id is still 'pending', Stripe must NOT be called."""
        order, _ = self._make_order(payment_external_id="pending")
        self._authenticate()

        self.client.post(self._cancel_url(order.pk))

        mock_cancel.assert_not_called()

    # ---- paid order cancellation (refund) ----

    @patch("orders.views.stripe.Refund.create")
    def test_cancel_paid_order_returns_200(self, _mock):
        order, _ = self._make_order(order_status="paid", payment_status="completed")
        self._authenticate()
        resp = self.client.post(self._cancel_url(order.pk))
        self.assertEqual(resp.status_code, 200)

    @patch("orders.views.stripe.Refund.create")
    def test_cancel_paid_order_calls_stripe_refund_correctly(self, mock_refund):
        order, _ = self._make_order(
            order_status="paid", payment_status="completed",
            payment_external_id="pi_paid_99",
        )
        self._authenticate()

        self.client.post(self._cancel_url(order.pk))

        mock_refund.assert_called_once_with(
            payment_intent="pi_paid_99", reason="requested_by_customer"
        )

    @patch("orders.views.stripe.Refund.create")
    def test_cancel_paid_order_restores_stock(self, _mock):
        order, _ = self._make_order(order_status="paid", payment_status="completed")
        stock_before = self.piece.quantity
        self._authenticate()

        self.client.post(self._cancel_url(order.pk))

        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantity, stock_before + 2)

    @patch("orders.views.stripe.Refund.create")
    def test_cancel_paid_order_deletes_pending_shipping_tracking(self, _mock):
        order, _ = self._make_order(order_status="paid", payment_status="completed")
        tracking = ShippingTracking.objects.create(order=order)  # default status='pending'
        self._authenticate()

        self.client.post(self._cancel_url(order.pk))

        self.assertFalse(ShippingTracking.objects.filter(pk=tracking.pk).exists())

    @patch("orders.views.stripe.Refund.create")
    def test_cancel_paid_order_does_not_delete_in_transit_tracking(self, _mock):
        order, _ = self._make_order(order_status="paid", payment_status="completed")
        tracking = ShippingTracking.objects.create(order=order, status="in_transit")
        self._authenticate()

        self.client.post(self._cancel_url(order.pk))

        self.assertTrue(ShippingTracking.objects.filter(pk=tracking.pk).exists())

    @patch("orders.views.stripe.Refund.create")
    def test_cancel_paid_order_stripe_error_returns_502(self, mock_refund):
        import stripe as stripe_lib
        mock_refund.side_effect = stripe_lib.error.StripeError("Refund failed")
        order, _ = self._make_order(order_status="paid", payment_status="completed")
        self._authenticate()

        resp = self.client.post(self._cancel_url(order.pk))

        self.assertEqual(resp.status_code, 502)

    @patch("orders.views.stripe.Refund.create")
    def test_cancel_paid_order_stripe_error_does_not_change_order_status(self, mock_refund):
        import stripe as stripe_lib
        mock_refund.side_effect = stripe_lib.error.StripeError("Refund failed")
        order, _ = self._make_order(order_status="paid", payment_status="completed")
        self._authenticate()

        self.client.post(self._cancel_url(order.pk))

        order.refresh_from_db()
        self.assertEqual(order.status, "paid")  # must remain unchanged on refund failure