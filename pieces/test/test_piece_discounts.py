import io
from datetime import date, timedelta

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from pieces.models import Piece, PieceDiscount, Discount, TypePiece, Section
from users.models import User  # ajusta al path real


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def make_image_file(name="test.jpg"):
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=(0, 255, 0)).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


def create_type_piece():
    return TypePiece.objects.create(key="Tipo Test", type = "si")


def create_section():
    return Section.objects.create(key="Sección Test", section = "si")


def create_piece(type_piece=None, section=None, slug="test-piece", title="Test Piece"):
    type_piece = type_piece or create_type_piece()
    section = section or create_section()
    return Piece.objects.create(
        title=title,
        description="Descripción de prueba",
        quantity=5,
        price_base="100.00",
        width="10.00",
        height="20.00",
        length="5.00",
        weight="1.50",
        type_id=type_piece.pk,
        section_id=section.pk,
        thumbnail_path=make_image_file(),
        slug=slug,
    )


def create_discount(percentage="10.0", days_ahead_start=1, days_ahead_end=10):
    """
    Crea un Discount con fechas futuras válidas.
    Usamos .objects.create() saltando clean() para no depender
    de la lógica de fechas en los helpers de test.
    """
    today = timezone.now().date()
    return Discount.objects.create(
        percentage=percentage,
        start_date=today + timedelta(days=days_ahead_start),
        end_date=today + timedelta(days=days_ahead_end),
    )


def create_piece_discount(piece, discount=None):
    discount = discount or create_discount()
    return PieceDiscount.objects.create(piece=piece, discount=discount)


def get_results(resp):
    """Soporta respuestas paginadas y no paginadas."""
    if isinstance(resp.data, dict) and "results" in resp.data:
        return resp.data["results"]
    return resp.data


def discounts_url(piece_slug, detail_id=None):
    """
    /api/v1/pieces/{slug}/discounts/
    /api/v1/pieces/{slug}/discounts/{id}/
    """
    base = f"/api/v1/pieces/{piece_slug}/discounts/"
    return base if detail_id is None else f"{base}{detail_id}/"


# ──────────────────────────────────────────────
# Mixins
# ──────────────────────────────────────────────

class AdminClientMixin:
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(
            username="admin", password="admin123", email="admin@test.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)


class AnonClientMixin:
    def setUp(self):
        super().setUp()
        self.client = APIClient()


# ══════════════════════════════════════════════
# 1. LIST
# ══════════════════════════════════════════════

class PieceDiscountListTests(AnonClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.type_piece = create_type_piece()
        self.section = create_section()
        self.piece = create_piece(self.type_piece, self.section)
        self.discount = create_discount()
        self.piece_discount = create_piece_discount(self.piece, self.discount)

    def test_list_returns_200(self):
        resp = self.client.get(discounts_url(self.piece.slug))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_returns_discount_of_piece(self):
        resp = self.client.get(discounts_url(self.piece.slug))
        results = get_results(resp)
        ids = [d["id"] for d in results]
        self.assertIn(self.piece_discount.id, ids)

    def test_list_returns_only_piece_discounts(self):
        """El descuento de otra pieza no debe aparecer en la lista."""
        other_piece = create_piece(self.type_piece, self.section, slug="other", title="Otra Pieza")
        other_discount = create_discount(percentage="20.0", days_ahead_start=2, days_ahead_end=15)
        create_piece_discount(other_piece, other_discount)

        resp = self.client.get(discounts_url(self.piece.slug))
        results = get_results(resp)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.piece_discount.id)

    def test_list_excludes_soft_deleted_discounts(self):
        """PieceDiscounts con deleted_at != None no deben aparecer."""
        PieceDiscount.objects.filter(id=self.piece_discount.id).update(
            deleted_at=timezone.now()
        )
        resp = self.client.get(discounts_url(self.piece.slug))
        results = get_results(resp)
        ids = [d["id"] for d in results]
        self.assertNotIn(self.piece_discount.id, ids)

    def test_list_empty_when_no_discounts(self):
        """Si la pieza no tiene descuentos activos devuelve lista vacía."""
        PieceDiscount.objects.filter(piece=self.piece).update(deleted_at=timezone.now())
        resp = self.client.get(discounts_url(self.piece.slug))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(get_results(resp)), 0)

    def test_list_empty_for_nonexistent_piece(self):
        """Slug inexistente devuelve lista vacía (el viewset filtra, no lanza 404)."""
        resp = self.client.get(discounts_url("ghost-slug"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(get_results(resp)), 0)

    def test_list_accessible_by_anon(self):
        """El endpoint es de solo lectura y público."""
        resp = self.client.get(discounts_url(self.piece.slug))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ══════════════════════════════════════════════
# 2. RETRIEVE
# ══════════════════════════════════════════════

class PieceDiscountRetrieveTests(AnonClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.type_piece = create_type_piece()
        self.section = create_section()
        self.piece = create_piece(self.type_piece, self.section)
        self.discount = create_discount(percentage="15.0")
        self.piece_discount = create_piece_discount(self.piece, self.discount)

    def test_retrieve_returns_200(self):
        resp = self.client.get(discounts_url(self.piece.slug, self.piece_discount.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_retrieve_returns_correct_id(self):
        resp = self.client.get(discounts_url(self.piece.slug, self.piece_discount.id))
        self.assertEqual(resp.data["id"], self.piece_discount.id)

    def test_retrieve_returns_percentage_from_related_discount(self):
        """El serializer expone discount.percentage como 'percentage'."""
        resp = self.client.get(discounts_url(self.piece.slug, self.piece_discount.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("percentage", resp.data)
        self.assertEqual(float(resp.data["percentage"]), float(self.discount.percentage))

    def test_retrieve_returns_piece_id(self):
        resp = self.client.get(discounts_url(self.piece.slug, self.piece_discount.id))
        self.assertIn("piece", resp.data)
        self.assertEqual(resp.data["piece"], self.piece.id)

    def test_retrieve_nonexistent_id_returns_404(self):
        resp = self.client.get(discounts_url(self.piece.slug, 99999))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_accessible_by_anon(self):
        resp = self.client.get(discounts_url(self.piece.slug, self.piece_discount.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ══════════════════════════════════════════════
# 3. WRITE METHODS FORBIDDEN (ReadOnly)
# ══════════════════════════════════════════════

class PieceDiscountWriteForbiddenTests(AdminClientMixin, APITestCase):
    """
    PieceDiscountViewSet extiende ReadOnlyModelViewSet:
    POST, PUT, PATCH y DELETE no deben estar disponibles.
    """

    def setUp(self):
        super().setUp()
        self.type_piece = create_type_piece()
        self.section = create_section()
        self.piece = create_piece(self.type_piece, self.section)
        self.discount = create_discount()
        self.piece_discount = create_piece_discount(self.piece, self.discount)
        self.url = discounts_url(self.piece.slug)
        self.detail_url = discounts_url(self.piece.slug, self.piece_discount.id)

    def test_post_not_allowed(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_not_allowed(self):
        resp = self.client.put(self.detail_url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_not_allowed(self):
        resp = self.client.patch(self.detail_url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        resp = self.client.delete(self.detail_url)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)