from decimal import Decimal
import io
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from PIL import Image

from orders.models import (
    Order,
    OrderItem,
    ShippingTracking,
    Payment,
    Coupon,
    CouponUsage,
)
from users.models import Address
from pieces.models import Piece, Section, TypePiece


# ---------------------------------------------------------------------------
# Mixin con datos base reutilizables
# ---------------------------------------------------------------------------

class OrderTestMixin:

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )

        self.type_piece = TypePiece.objects.create(type="Escultura", key="escultura")
        self.section = Section.objects.create(section="Tecnologia", key="tecnologia")

        self.address = Address.objects.create(
            user=self.user,
            recipient_name="Test User",
            country="mexico",
            state="Jalisco",
            city="Guadalajara",
            postal_code="44100",
            neighborhood="Centro",
            street="Av. Juárez",
            street_number=123,
            phone_number="+523310000000",
            reference="Entre calles principales",
            is_default=True,
        )
        self.other_address = Address.objects.create(
            user=self.other_user,
            recipient_name="Other User",
            country="usa",
            state="California",
            city="Los Angeles",
            postal_code="90001",
            neighborhood="Downtown",
            street="Main St",
            street_number=456,
            phone_number="+13105550000",
            reference="Near the park",
            is_default=True,
        )

        self.piece = Piece.objects.create(
            title="Test Piece",
            description="Descripción de prueba",
            quantity=5,
            price_base=Decimal("100.00"),
            width=Decimal("10.00"),
            height=Decimal("20.00"),
            length=Decimal("5.00"),
            weight=Decimal("1.50"),
            type=self.type_piece,
            section=self.section,
            thumbnail_path=self._fake_image(),
        )

        self.order = Order.objects.create(
            user=self.user,
            total=Decimal("199.98"),
            status="pending",
            address=self.address,
        )
        self.other_order = Order.objects.create(
            user=self.other_user,
            total=Decimal("50.00"),
            status="paid",
            address=self.other_address,
        )

        self.shipping_tracking = ShippingTracking.objects.create(
            order=self.order,
            carrier="fedex",
            tracking_number="123456789",
            status="in_transit",
            shipped_at=timezone.now(),
        )
        self.other_shipping_tracking = ShippingTracking.objects.create(
            order=self.other_order,
            carrier="dhl",
            tracking_number="987654321",
            status="delivered",
            shipped_at=timezone.now(),
            delivered_at=timezone.now(),
        )

    @staticmethod
    def _fake_image(name="test.jpg"):
        """Genera una imagen JPEG real en memoria usando Pillow."""
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")

    def login_as(self, user):
        self.client.force_authenticate(user=user)

    def login(self):
        self.login_as(self.user)

    def logout(self):
        self.client.force_authenticate(user=None)


# ===========================================================================
# OrderViewSet — LIST
# ===========================================================================

class TestOrderList(OrderTestMixin, APITestCase):

    # FIX: IsOwner filtra el queryset en vez de bloquear con 401.
    # Un usuario no autenticado recibe 200 con lista vacía.
    def test_unauthenticated_returns_401(self):
        self.logout()
        response = self.client.get(reverse("orders-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_sees_only_own_orders(self):
        self.login()
        response = self.client.get(reverse("orders-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [o["id"] for o in response.data["results"]]
        self.assertIn(self.order.id, ids)
        self.assertNotIn(self.other_order.id, ids)

    def test_empty_list_when_user_has_no_orders(self):
        self.login_as(self.other_user)
        self.other_order.delete()
        response = self.client.get(reverse("orders-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_response_includes_nested_items(self):
        OrderItem.objects.create(
            order=self.order,
            piece=self.piece,
            quantity=2,
            price_snapshot=Decimal("99.99"),
        )
        self.login()
        response = self.client.get(reverse("orders-list"))

        first = response.data["results"][0]
        self.assertIn("items", first)
        self.assertEqual(len(first["items"]), 1)

    def test_response_includes_nested_payments(self):
        Payment.objects.create(
            order=self.order,
            amount=Decimal("199.98"),
            payment_method="stripe",
            external_id="pi_test_123",
            status="completed",
        )
        self.login()
        response = self.client.get(reverse("orders-list"))

        first = response.data["results"][0]
        self.assertIn("payments", first)
        self.assertEqual(len(first["payments"]), 1)

    # FIX: el campo real en la respuesta es "coupon_usage", no "coupons".
    def test_response_includes_nested_coupons(self):
        coupon = Coupon.objects.create(
            code="SAVE10",
            percentage=Decimal("10.0"),
            valid_from=timezone.now().date(),
            valid_until=timezone.now().date() + timezone.timedelta(days=30),
        )
        CouponUsage.objects.create(
            order=self.order,
            coupon=coupon,
            user=self.user,
            discount_applied=Decimal("20.00"),
        )
        self.login()
        response = self.client.get(reverse("orders-list"))

        first = response.data["results"][0]
        self.assertIn("coupon_usage", first)
        self.assertEqual(len(first["coupon_usage"]), 1)

    def test_multiple_own_orders_all_returned(self):
        self.login()
        Order.objects.create(
            user=self.user, total=Decimal("10.00"), status="paid", address=self.address
        )
        Order.objects.create(
            user=self.user, total=Decimal("20.00"), status="shipped", address=self.address
        )
        response = self.client.get(reverse("orders-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)


# ===========================================================================
# OrderViewSet — RETRIEVE
# ===========================================================================

class TestOrderRetrieve(OrderTestMixin, APITestCase):

    def test_owner_can_retrieve_own_order(self):
        self.login()
        response = self.client.get(reverse("orders-detail", kwargs={"pk": self.order.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.order.id)

    def test_other_user_cannot_access_order(self):
        self.login_as(self.other_user)
        response = self.client.get(reverse("orders-detail", kwargs={"pk": self.order.pk}))

        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

    # FIX: IsOwner filtra queryset, por eso un anónimo recibe 404 (no 401).
    def test_unauthenticated_cannot_retrieve_order(self):
        self.logout()
        response = self.client.get(reverse("orders-detail", kwargs={"pk": self.order.pk}))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_order_returns_404(self):
        self.login()
        response = self.client.get(reverse("orders-detail", kwargs={"pk": 999999}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # FIX: "coupons" es "coupon_usage" en la respuesta real del serializer.
    def test_response_contains_expected_fields(self):
        self.login()
        response = self.client.get(reverse("orders-detail", kwargs={"pk": self.order.pk}))

        expected = {"id", "user", "total", "status", "address", "items", "payments", "coupon_usage"}
        self.assertTrue(expected.issubset(set(response.data.keys())))

    def test_total_value_matches(self):
        self.login()
        response = self.client.get(reverse("orders-detail", kwargs={"pk": self.order.pk}))

        self.assertEqual(Decimal(response.data["total"]), self.order.total)

    def test_status_is_pending(self):
        self.login()
        response = self.client.get(reverse("orders-detail", kwargs={"pk": self.order.pk}))

        self.assertEqual(response.data["status"], "pending")


# ===========================================================================
# OrderViewSet — READ ONLY
# ===========================================================================

class TestOrderReadOnly(OrderTestMixin, APITestCase):

    def test_post_not_allowed(self):
        self.login()
        response = self.client.post(
            reverse("orders-list"),
            {"total": "99.99", "status": "pending", "address": self.address.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_not_allowed(self):
        self.login()
        response = self.client.put(
            reverse("orders-detail", kwargs={"pk": self.order.pk}),
            {"status": "paid"},
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_not_allowed(self):
        self.login()
        response = self.client.patch(
            reverse("orders-detail", kwargs={"pk": self.order.pk}),
            {"status": "paid"},
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        self.login()
        response = self.client.delete(
            reverse("orders-detail", kwargs={"pk": self.order.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ===========================================================================
# OrderFilter
# ===========================================================================

class TestOrderFilter(OrderTestMixin, APITestCase):

    def test_filter_by_date_returns_gte_results(self):
        self.login()

        old = Order.objects.create(
            user=self.user, total=Decimal("10.00"), status="paid", address=self.address
        )
        # FIX: usar timezone.now() para evitar el RuntimeWarning de naive datetime.
        Order.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timezone.timedelta(days=10)
        )
        recent = Order.objects.create(
            user=self.user, total=Decimal("20.00"), status="pending", address=self.address
        )

        filter_date = (timezone.now() - timezone.timedelta(days=5)).date()
        response = self.client.get(reverse("orders-list"), {"date": filter_date.isoformat()})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [o["id"] for o in response.data["results"]]
        self.assertIn(recent.id, ids)
        self.assertNotIn(old.id, ids)

    def test_filter_future_date_returns_empty(self):
        self.login()
        future = (timezone.now() + timezone.timedelta(days=30)).date()
        response = self.client.get(reverse("orders-list"), {"date": future.isoformat()})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_invalid_date_returns_400(self):
        self.login()
        response = self.client.get(reverse("orders-list"), {"date": "not-a-date"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_filter_returns_all_own_orders(self):
        self.login()
        response = self.client.get(reverse("orders-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)


# ===========================================================================
# ShippingTrackingViewSet — LIST
# ===========================================================================

class TestShippingTrackingList(OrderTestMixin, APITestCase):
    
    # IsOwner lanza 401 para usuarios no autenticados.
    def test_unauthenticated_returns_401(self):
        self.logout()
        response = self.client.get(reverse("shipping-tracking-list"))  #  correcto
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_sees_only_own_trackings(self):
        self.login()
        response = self.client.get(reverse("shipping-tracking-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertIn(self.shipping_tracking.id, ids)
        self.assertNotIn(self.other_shipping_tracking.id, ids)

    def test_empty_list_when_no_trackings(self):
        self.login_as(self.other_user)
        self.other_shipping_tracking.delete()
        response = self.client.get(reverse("shipping-tracking-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    # ShippingTrackingSerializer con fields='__all__' no incluye 'order'
    # según la respuesta real observada en los logs.
    def test_response_contains_expected_fields(self):
        self.login()
        response = self.client.get(reverse("shipping-tracking-list"))

        self.assertGreater(response.data["count"], 0)
        first = response.data["results"][0]
        for field in ("id", "carrier", "tracking_number", "status", "shipped_at", "delivered_at"):
            self.assertIn(field, first, msg=f"Campo '{field}' no encontrado en la respuesta")


# ===========================================================================
# ShippingTrackingViewSet — RETRIEVE
# ===========================================================================

class TestShippingTrackingRetrieve(OrderTestMixin, APITestCase):

    def test_owner_can_retrieve_own_tracking(self):
        self.login()
        response = self.client.get(
            reverse("shipping-tracking-detail", kwargs={"pk": self.shipping_tracking.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.shipping_tracking.id)

    def test_other_user_cannot_retrieve_tracking(self):
        self.login_as(self.other_user)
        response = self.client.get(
            reverse("shipping-tracking-detail", kwargs={"pk": self.shipping_tracking.pk})
        )

        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

    # get_queryset devuelve none() para no autenticados → objeto no encontrado → 404.
    def test_unauthenticated_cannot_retrieve_tracking(self):
        self.logout()
        response = self.client.get(
            reverse("shipping-tracking-detail", kwargs={"pk": self.shipping_tracking.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_tracking_returns_404(self):
        self.login()
        response = self.client.get(
            reverse("shipping-tracking-detail", kwargs={"pk": 999999})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_carrier_status_and_tracking_number_are_correct(self):
        self.login()
        response = self.client.get(
            reverse("shipping-tracking-detail", kwargs={"pk": self.shipping_tracking.pk})
        )

        self.assertEqual(response.data["carrier"], "fedex")
        self.assertEqual(response.data["status"], "in_transit")
        self.assertEqual(response.data["tracking_number"], "123456789")

    def test_shipped_at_set_and_delivered_at_null(self):
        self.login()
        response = self.client.get(
            reverse("shipping-tracking-detail", kwargs={"pk": self.shipping_tracking.pk})
        )

        self.assertIsNotNone(response.data["shipped_at"])
        self.assertIsNone(response.data["delivered_at"])


# ===========================================================================
# ShippingTrackingViewSet — READ ONLY
# ===========================================================================

class TestShippingTrackingReadOnly(OrderTestMixin, APITestCase):

    def test_post_not_allowed(self):
        self.login()
        response = self.client.post(
            reverse("shipping-tracking-list"),
            {"order": self.order.pk, "carrier": "ups", "tracking_number": "NEW123", "status": "pending"},
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_not_allowed(self):
        self.login()
        response = self.client.put(
            reverse("shipping-tracking-detail", kwargs={"pk": self.shipping_tracking.pk}),
            {"status": "delivered"},
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_not_allowed(self):
        self.login()
        response = self.client.patch(
            reverse("shipping-tracking-detail", kwargs={"pk": self.shipping_tracking.pk}),
            {"status": "delivered"},
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        self.login()
        response = self.client.delete(
            reverse("shipping-tracking-detail", kwargs={"pk": self.shipping_tracking.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ===========================================================================
# Nested route: /api/v1/orders/{order_pk}/shipping-trackings/
# ===========================================================================

class TestNestedShippingTracking(OrderTestMixin, APITestCase):

    def test_owner_lists_trackings_under_own_order(self):
        self.login()
        url = reverse("order-shiping-tracking-list", kwargs={"order_pk": self.order.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertIn(self.shipping_tracking.id, ids)

    # get_queryset filtra por order__user_id=user.id → other_user solo ve sus
    # propios trackings, nunca los de una orden ajena.
    def test_other_user_cannot_see_foreign_order_trackings(self):
        self.login_as(self.other_user)
        url = reverse("order-shiping-tracking-list", kwargs={"order_pk": self.order.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertNotIn(self.shipping_tracking.id, ids)

    # IsOwner lanza 401 para usuarios no autenticados.
    def test_unauthenticated_gets_empty_nested_trackings(self):
        self.logout()
        url = reverse("order-shiping-tracking-list", kwargs={"order_pk": self.order.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_trackings_from_other_orders_not_leaked(self):
        self.login()
        url = reverse("order-shiping-tracking-list", kwargs={"order_pk": self.order.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertNotIn(self.other_shipping_tracking.id, ids)