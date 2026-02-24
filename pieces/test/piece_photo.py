import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from pieces.models import Piece, PiecePhoto, TypePiece, Section  # ajusta los imports reales
from users.models import User  # ajusta al path real de tu modelo de usuario


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def make_image_file(name="test.jpg", size=(100, 100), fmt="JPEG"):
    """Genera un archivo de imagen en memoria listo para subir."""
    buf = io.BytesIO()
    Image.new("RGB", size, color=(255, 0, 0)).save(buf, format=fmt)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


def create_type_piece():
    return TypePiece.objects.create(key="Tipo Test", type = "si")


def create_section():
    return Section.objects.create(key="Sección Test", section = "si")


def piece_payload(type_piece, section, title="Mi Pieza", **kwargs):
    """Payload base con todos los campos requeridos de Piece."""
    data = {
        "title": title,
        "description": "Descripción de prueba",
        "quantity": 5,
        "price_mx": "100.00",
        "price_usa": "200.00",
        "width": "10.00",
        "height": "20.00",
        "length": "5.00",
        "weight": "1.50",
        "type_id": type_piece.pk,
        "section_id": section.pk,
        "thumbnail_path": make_image_file(),
    }
    data.update(kwargs)
    return data


def create_piece(type_piece=None, section=None, slug="test-piece", title="Test Piece"):
    """Crea una Piece con todos sus campos requeridos."""
    type_piece = type_piece or create_type_piece()
    section = section or create_section()
    payload = piece_payload(type_piece, section, title=title, slug=slug)
    return Piece.objects.create(**payload)


def create_photo(piece, position=1):
    return PiecePhoto.objects.create(
        piece=piece,
        image_path=make_image_file(f"photo_{position}.jpg"),
        position=position,
    )


def get_results(resp):
    """
    Extrae la lista de items de una respuesta, sea paginada o no.
    Si está paginada devuelve resp.data['results'], si no, resp.data directamente.
    """
    if isinstance(resp.data, dict) and "results" in resp.data:
        return resp.data["results"]
    return resp.data


def photos_url(piece_slug, suffix=""):
    """
    /api/v1/pieces/{piece_slug}/photos/
    /api/v1/pieces/{piece_slug}/photos/{suffix}/
    """
    base = f"/api/v1/pieces/{piece_slug}/photos/"
    return base if not suffix else f"{base}{suffix}/"


# ──────────────────────────────────────────────
# Mixins de autenticación
# ──────────────────────────────────────────────

class AdminClientMixin:
    """Autentifica como admin antes de cada test."""

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(
            username="admin", password="admin123", email="admin@test.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)


class AnonClientMixin:
    """Cliente sin autenticación."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()


# ══════════════════════════════════════════════
# 1. LIST / RETRIEVE (GET)
# ══════════════════════════════════════════════

class PiecePhotoListTests(AnonClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.type_piece = create_type_piece()
        self.section = create_section()
        self.piece = create_piece(self.type_piece, self.section)
        self.photo1 = create_photo(self.piece, position=1)
        self.photo2 = create_photo(self.piece, position=2)

    def test_list_returns_only_piece_photos(self):
        other_piece = create_piece(self.type_piece, self.section, slug="other-piece", title="Otra Pieza")
        create_photo(other_piece, position=1)

        resp = self.client.get(photos_url(self.piece.slug))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = get_results(resp)
        ids = [p["id"] for p in results]
        self.assertIn(self.photo1.id, ids)
        self.assertIn(self.photo2.id, ids)
        # La foto de la otra pieza NO debe aparecer
        self.assertEqual(len(ids), 2)

    def test_list_excludes_soft_deleted_photos(self):
        """Fotos con deleted_at != None no deben listarse."""
        # PiecePhoto.delete() es siempre hard delete, así que seteamos
        # deleted_at directamente para simular un soft delete en la query.
        from django.utils import timezone
        PiecePhoto.objects.filter(id=self.photo1.id).update(deleted_at=timezone.now())

        resp = self.client.get(photos_url(self.piece.slug))
        results = get_results(resp)
        ids = [p["id"] for p in results]
        self.assertNotIn(self.photo1.id, ids)

    def test_retrieve_returns_correct_photo(self):
        resp = self.client.get(photos_url(self.piece.slug) + f"{self.photo1.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["id"], self.photo1.id)

    def test_list_empty_for_nonexistent_piece(self):
        """El viewset filtra por slug; si no existe la pieza devuelve lista vacía."""
        resp = self.client.get(photos_url("nonexistent-slug"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(get_results(resp)), 0)


# ══════════════════════════════════════════════
# 2. CREATE (POST single)
# ══════════════════════════════════════════════

class PiecePhotoCreateTests(AdminClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.type_piece = create_type_piece()
        self.section = create_section()
        self.piece = create_piece(self.type_piece, self.section)

    def test_create_photo_success(self):
        data = {"image_path": make_image_file(), "position": 1}
        resp = self.client.post(photos_url(self.piece.slug), data, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PiecePhoto.objects.filter(piece=self.piece).count(), 1)

    def test_create_photo_exceeding_limit_raises_400(self):
        """No se puede crear la foto 11 cuando ya hay 10."""
        for i in range(1, 11):
            create_photo(self.piece, position=i)

        data = {"image_path": make_image_file(), "position": 11}
        resp = self.client.post(photos_url(self.piece.slug), data, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_photo_anon_forbidden(self):
        self.client.force_authenticate(user=None)
        data = {"image_path": make_image_file(), "position": 1}
        resp = self.client.post(photos_url(self.piece.slug), data, format="multipart")
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_create_photo_piece_not_found_raises_404(self):
        data = {"image_path": make_image_file(), "position": 1}
        resp = self.client.post(photos_url("ghost-slug"), data, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ══════════════════════════════════════════════
# 3. BULK CREATE
# ══════════════════════════════════════════════

class PiecePhotoBulkCreateTests(AdminClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.type_piece = create_type_piece()
        self.section = create_section()
        self.piece = create_piece(self.type_piece, self.section)
        self.url = photos_url(self.piece.slug, "bulk-create")

    def test_bulk_create_single_image(self):
        data = {"images": [make_image_file()]}
        resp = self.client.post(self.url, data, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(PiecePhoto.objects.filter(piece=self.piece).count(), 1)

    def test_bulk_create_multiple_images(self):
        images = [make_image_file(f"img{i}.jpg") for i in range(3)]
        resp = self.client.post(self.url, {"images": images}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp.data), 3)

    def test_bulk_create_positions_are_sequential(self):
        """Las posiciones deben continuar desde la última existente."""
        create_photo(self.piece, position=1)
        create_photo(self.piece, position=2)

        images = [make_image_file(f"new{i}.jpg") for i in range(2)]
        resp = self.client.post(self.url, {"images": images}, format="multipart")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        positions = sorted([p["position"] for p in resp.data])
        self.assertEqual(positions, [3, 4])

    def test_bulk_create_exceeds_limit_raises_400(self):
        """Si ya hay 8 fotos, subir 3 más debe fallar."""
        for i in range(1, 9):
            create_photo(self.piece, position=i)

        images = [make_image_file(f"over{i}.jpg") for i in range(3)]
        resp = self.client.post(self.url, {"images": images}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_create_exactly_fills_limit(self):
        """Subir exactamente las fotos que faltan hasta 10 debe funcionar."""
        for i in range(1, 8):
            create_photo(self.piece, position=i)  # 7 existentes

        images = [make_image_file(f"fill{i}.jpg") for i in range(3)]  # 7+3=10
        resp = self.client.post(self.url, {"images": images}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_bulk_create_empty_list_raises_400(self):
        resp = self.client.post(self.url, {"images": []}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_create_no_images_field_raises_400(self):
        resp = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_create_anon_forbidden(self):
        self.client.force_authenticate(user=None)
        data = {"images": [make_image_file()]}
        resp = self.client.post(self.url, data, format="multipart")
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_bulk_create_piece_not_found_raises_404(self):
        url = photos_url("ghost-piece", "bulk-create")
        resp = self.client.post(url, {"images": [make_image_file()]}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_create_is_atomic(self):
        """Si algo falla a mitad del proceso no debe quedar ninguna foto guardada."""
        # Creamos 9 fotos; una imagen inválida en el batch debería revertir todo.
        for i in range(1, 10):
            create_photo(self.piece, position=i)

        # Solo podemos subir 1 más; intentar subir 2 debe fallar sin crear ninguna.
        images = [make_image_file(f"x{i}.jpg") for i in range(2)]
        initial_count = PiecePhoto.objects.filter(piece=self.piece).count()
        resp = self.client.post(self.url, {"images": images}, format="multipart")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PiecePhoto.objects.filter(piece=self.piece).count(), initial_count)


# ══════════════════════════════════════════════
# 4. REORDER
# ══════════════════════════════════════════════

class PiecePhotoReorderTests(AdminClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.type_piece = create_type_piece()
        self.section = create_section()
        self.piece = create_piece(self.type_piece, self.section)
        self.photo1 = create_photo(self.piece, position=1)
        self.photo2 = create_photo(self.piece, position=2)
        self.photo3 = create_photo(self.piece, position=3)
        self.url = photos_url(self.piece.slug, "reorder")

    def _reorder_payload(self, mapping):
        """mapping: {photo: new_position}"""
        return {"photos": [{"id": p.id, "position": pos} for p, pos in mapping.items()]}

    def test_reorder_swaps_positions(self):
        payload = self._reorder_payload({
            self.photo1: 3,
            self.photo2: 2,
            self.photo3: 1,
        })
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.photo1.refresh_from_db()
        self.photo3.refresh_from_db()
        self.assertEqual(self.photo1.position, 3)
        self.assertEqual(self.photo3.position, 1)

    def test_reorder_response_is_ordered_by_position(self):
        payload = self._reorder_payload({
            self.photo1: 2,
            self.photo2: 1,
            self.photo3: 3,
        })
        resp = self.client.patch(self.url, payload, format="json")
        positions = [p["position"] for p in resp.data]
        self.assertEqual(positions, sorted(positions))

    def test_reorder_with_duplicate_positions_raises_400(self):
        payload = {"photos": [
            {"id": self.photo1.id, "position": 1},
            {"id": self.photo2.id, "position": 1},  # duplicado
        ]}
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_with_foreign_ids_raises_400(self):
        """IDs que no pertenecen a la pieza deben rechazarse."""
        other_piece = create_piece(self.type_piece, self.section, slug="other", title="Otra Pieza")
        other_photo = create_photo(other_piece, position=1)

        payload = {"photos": [{"id": other_photo.id, "position": 1}]}
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_with_invalid_position_value_raises_400(self):
        """position=0 viola min_value=1."""
        payload = {"photos": [{"id": self.photo1.id, "position": 0}]}
        resp = self.client.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_with_empty_list_raises_400(self):
        resp = self.client.patch(self.url, {"photos": []}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_anon_forbidden(self):
        self.client.force_authenticate(user=None)
        payload = self._reorder_payload({self.photo1: 2, self.photo2: 1, self.photo3: 3})
        resp = self.client.patch(self.url, payload, format="json")
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_reorder_piece_not_found_raises_404(self):
        url = photos_url("ghost-piece", "reorder")
        payload = {"photos": [{"id": self.photo1.id, "position": 1}]}
        resp = self.client.patch(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ══════════════════════════════════════════════
# 5. BULK DELETE
# ══════════════════════════════════════════════

class PiecePhotoBulkDeleteTests(AdminClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.type_piece = create_type_piece()
        self.section = create_section()
        self.piece = create_piece(self.type_piece, self.section)
        self.photo1 = create_photo(self.piece, position=1)
        self.photo2 = create_photo(self.piece, position=2)
        self.photo3 = create_photo(self.piece, position=3)
        self.url = photos_url(self.piece.slug, "bulk-delete")

    def test_bulk_delete_removes_photos(self):
        payload = {"ids": [self.photo1.id, self.photo2.id]}
        resp = self.client.delete(self.url, payload, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(PiecePhoto.objects.filter(id__in=[self.photo1.id, self.photo2.id]).exists())

    def test_bulk_delete_response_includes_count(self):
        payload = {"ids": [self.photo1.id, self.photo2.id]}
        resp = self.client.delete(self.url, payload, format="json")
        self.assertIn("2", resp.data["detail"])

    def test_bulk_delete_does_not_affect_other_photos(self):
        payload = {"ids": [self.photo1.id]}
        self.client.delete(self.url, payload, format="json")

        self.assertTrue(PiecePhoto.objects.filter(id=self.photo2.id).exists())
        self.assertTrue(PiecePhoto.objects.filter(id=self.photo3.id).exists())

    def test_bulk_delete_cannot_delete_foreign_photos(self):
        """Intentar borrar fotos de otra pieza no debe tocarlas."""
        other_piece = create_piece(self.type_piece, self.section, slug="other2", title="Otra Pieza 2")
        other_photo = create_photo(other_piece, position=1)

        payload = {"ids": [other_photo.id]}
        resp = self.client.delete(self.url, payload, format="json")

        # Devuelve 404 porque no se encontró ninguna foto en ESTA pieza
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(PiecePhoto.objects.filter(id=other_photo.id).exists())

    def test_bulk_delete_nonexistent_ids_returns_404(self):
        payload = {"ids": [99999, 88888]}
        resp = self.client.delete(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_delete_empty_ids_raises_400(self):
        resp = self.client.delete(self.url, {"ids": []}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_delete_anon_forbidden(self):
        self.client.force_authenticate(user=None)
        payload = {"ids": [self.photo1.id]}
        resp = self.client.delete(self.url, payload, format="json")
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_bulk_delete_piece_not_found_raises_404(self):
        url = photos_url("ghost-piece", "bulk-delete")
        resp = self.client.delete(url, {"ids": [self.photo1.id]}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_delete_is_hard_delete(self):
        """Las fotos eliminadas no deben existir ni como soft-delete."""
        payload = {"ids": [self.photo1.id]}
        self.client.delete(self.url, payload, format="json")

        # Verificamos a nivel de DB (incluyendo deleted_at) que no existe
        self.assertFalse(
            PiecePhoto.all_objects.filter(id=self.photo1.id).exists()
        )