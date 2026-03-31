from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from users.models import Address

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def make_user(username="testuser", email="test@example.com", password="Pass1234!"):
    return User.objects.create_user(username=username, email=email, password=password)

# ---------------------------------------------------------------------------
# EmailUpdateAPIView
# ---------------------------------------------------------------------------

class EmailUpdateAPIViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/users/me/email/request-change"
        self.password = "Pass1234!"

    # --- autenticación ---

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {"email": "nuevo@example.com"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- email ya en uso ---

    def test_email_already_registered_returns_200_without_sending_email(self):
        make_user(username="other", email="ocupado@example.com")
        with patch("core.services.email_service.UpdateUserEmail.send_email") as mock_send:  
            response = self.client.post(self.url, {"email": "ocupado@example.com", "password": self.password})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        mock_send.assert_not_called()

    # --- email nuevo ---

    @patch("users.views.UsersRegisterService.get_confirmation_url", return_value="http://confirm.url/token")
    @patch("core.services.email_service.UpdateUserEmail.send_email")  
    def test_new_email_sends_confirmation_and_returns_200(self, mock_send, mock_url):
        response = self.client.post(self.url, {"email": "nuevo@example.com", "password": self.password})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        mock_send.assert_called_once_with(
            to_email="nuevo@example.com",
            confirm_url="http://confirm.url/token",
            nombre=self.user.username,
        )

    # --- validación del serializer ---

    def test_invalid_email_format_returns_400(self):
        response = self.client.post(self.url, {"email": "no-es-un-email", "password": self.password})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_email_field_returns_400(self):
        response = self.client.post(self.url, {"password": self.password })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# AddressViewSet
# ---------------------------------------------------------------------------

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from .models import Address

User = get_user_model()


# ──────────────────────────────────────────────
# Mixin con helpers compartidos
# ──────────────────────────────────────────────

class AddressTestMixin:
    """Datos y helpers reutilizables entre TestCases."""

    ADDRESS_DATA = {
        "recipient_name": "Juan Pérez",
        "country": "mexico",
        "state": "Jalisco",
        "city": "Guadalajara",
        "postal_code": "44100",
        "neighborhood": "Centro",
        "street": "Av. Juárez",
        "street_number": 123,
        "phone_number": "+523312345678",
        "reference": "Cerca del parque",
        "apartment_number": "4B",
        "is_default": False,
    }

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="pass1234"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@test.com", password="pass1234"
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_address(self, user=None, **kwargs):
        data = {**self.ADDRESS_DATA, **kwargs}
        return Address.objects.create(user=user or self.user, **data)

    def list_url(self):
        return reverse("user:address-list")

    def detail_url(self, pk):
        return reverse("user:address-detail", args=[pk])

    def set_default_url(self, pk):
        return reverse("user:address-set-default", args=[pk])


# ──────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────

class TestAddressAuthentication(AddressTestMixin, APITestCase):

    def test_unauthenticated_list_returns_401(self):
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_create_returns_401(self):
        response = self.client.post(self.list_url(), self.ADDRESS_DATA, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_detail_returns_401(self):
        address = self.create_address()
        response = self.client.get(self.detail_url(address.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ──────────────────────────────────────────────
# List
# ──────────────────────────────────────────────

class TestAddressList(AddressTestMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.authenticate()

    def test_returns_only_own_addresses(self):
        own = self.create_address()
        other = self.create_address(user=self.other_user)

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [a["id"] for a in response.data["results"]]
        self.assertIn(own.id, ids)
        self.assertNotIn(other.id, ids)

    def test_empty_list_when_no_addresses(self):
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_default_address_appears_first(self):
        non_default = self.create_address(is_default=False)
        default = self.create_address(is_default=True)

        response = self.client.get(self.list_url())

        results = response.data["results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(results[0]["id"], default.id)
        self.assertEqual(results[1]["id"], non_default.id)

    def test_returns_multiple_own_addresses(self):
        self.create_address()
        self.create_address()

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

# ──────────────────────────────────────────────
# Create
# ──────────────────────────────────────────────

class TestAddressCreate(AddressTestMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.authenticate()

    def test_create_address_successfully(self):
        response = self.client.post(self.list_url(), self.ADDRESS_DATA, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["city"], self.ADDRESS_DATA["city"])

    def test_created_address_belongs_to_authenticated_user(self):
        self.client.post(self.list_url(), self.ADDRESS_DATA, format="json")
        self.assertEqual(Address.objects.filter(user=self.user).count(), 1)

    def test_create_default_address_when_none_exists(self):
        data = {**self.ADDRESS_DATA, "is_default": True}
        response = self.client.post(self.list_url(), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_default"])

    def test_cannot_create_second_default_address(self):
        self.create_address(is_default=True)
        data = {**self.ADDRESS_DATA, "is_default": True}

        response = self.client.post(self.list_url(), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_default", response.data)

    def test_create_missing_required_field_returns_400(self):
        data = {**self.ADDRESS_DATA}
        del data["street"]

        response = self.client.post(self.list_url(), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_country_returns_400(self):
        data = {**self.ADDRESS_DATA, "country": "argentina"}

        response = self.client.post(self.list_url(), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_user_default_does_not_block_own_default(self):
        """El default de otro usuario no interfiere con el tuyo."""
        self.create_address(user=self.other_user, is_default=True)
        data = {**self.ADDRESS_DATA, "is_default": True}

        response = self.client.post(self.list_url(), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_default"])


# ──────────────────────────────────────────────
# Retrieve
# ──────────────────────────────────────────────

class TestAddressRetrieve(AddressTestMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.authenticate()

    def test_owner_can_retrieve_own_address(self):
        address = self.create_address()
        response = self.client.get(self.detail_url(address.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], address.id)

    def test_response_contains_expected_fields(self):
        address = self.create_address()
        response = self.client.get(self.detail_url(address.pk))
        expected_fields = {
            "id", "recipient_name", "country", "state", "city",
            "postal_code", "neighborhood", "street", "street_number",
            "phone_number", "reference", "apartment_number",
            "is_default", "created_at", "updated_at",
        }
        self.assertTrue(expected_fields.issubset(set(response.data.keys())))

    def test_cannot_retrieve_other_user_address(self):
        other = self.create_address(user=self.other_user)
        response = self.client.get(self.detail_url(other.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_nonexistent_address_returns_404(self):
        response = self.client.get(self.detail_url(9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ──────────────────────────────────────────────
# Update
# ──────────────────────────────────────────────

class TestAddressUpdate(AddressTestMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.authenticate()
        self.address = self.create_address()

    def test_partial_update_own_address(self):
        response = self.client.patch(
            self.detail_url(self.address.pk), {"city": "Monterrey"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["city"], "Monterrey")

    def test_full_update_own_address(self):
        data = {**self.ADDRESS_DATA, "city": "Tijuana"}
        response = self.client.put(self.detail_url(self.address.pk), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["city"], "Tijuana")

    def test_cannot_update_other_user_address(self):
        other = self.create_address(user=self.other_user)
        response = self.client.patch(
            self.detail_url(other.pk), {"city": "CDMX"}, format="json"
        )
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

    def test_setting_is_default_when_another_exists_returns_400(self):
        self.create_address(is_default=True)
        response = self.client.patch(
            self.detail_url(self.address.pk), {"is_default": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_default", response.data)

    def test_update_own_default_address_does_not_conflict(self):
        """Actualizar otros campos de la dirección default no debe disparar el error."""
        self.address.is_default = True
        self.address.save()

        response = self.client.patch(
            self.detail_url(self.address.pk),
            {"city": "Puebla", "is_default": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["city"], "Puebla")

    def test_patch_does_not_alter_unrelated_fields(self):
        response = self.client.patch(
            self.detail_url(self.address.pk), {"city": "Mérida"}, format="json"
        )
        self.assertEqual(response.data["street"], self.ADDRESS_DATA["street"])


# ──────────────────────────────────────────────
# Delete
# ──────────────────────────────────────────────

class TestAddressDelete(AddressTestMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.authenticate()

    def test_owner_can_delete_own_address(self):
        address = self.create_address()
        response = self.client.delete(self.detail_url(address.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Address.objects.filter(pk=address.pk).exists())

    def test_cannot_delete_other_user_address(self):
        other = self.create_address(user=self.other_user)
        response = self.client.delete(self.detail_url(other.pk))
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )
        self.assertTrue(Address.all_objects.filter(pk=other.pk).exists())

    def test_delete_nonexistent_address_returns_404(self):
        response = self.client.delete(self.detail_url(9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ──────────────────────────────────────────────
# set-default action
# ──────────────────────────────────────────────

class TestSetDefaultAction(AddressTestMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.authenticate()
        self.address = self.create_address()

    def test_set_default_marks_address_as_default(self):
        response = self.client.patch(self.set_default_url(self.address.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.address.refresh_from_db()
        self.assertTrue(self.address.is_default)

    def test_set_default_response_contains_is_default_true(self):
        response = self.client.patch(self.set_default_url(self.address.pk))
        self.assertTrue(response.data["is_default"])

    def test_set_default_unsets_previous_default(self):
        old_default = self.create_address(is_default=True)

        self.client.patch(self.set_default_url(self.address.pk))

        old_default.refresh_from_db()
        self.address.refresh_from_db()
        self.assertFalse(old_default.is_default)
        self.assertTrue(self.address.is_default)

    def test_only_one_default_after_set_default(self):
        self.create_address(is_default=True)
        self.create_address(is_default=True)

        self.client.patch(self.set_default_url(self.address.pk))

        defaults = Address.objects.filter(user=self.user, is_default=True)
        self.assertEqual(defaults.count(), 1)
        self.assertEqual(defaults.first().pk, self.address.pk)

    def test_cannot_set_default_on_other_user_address(self):
        other = self.create_address(user=self.other_user)
        response = self.client.patch(self.set_default_url(other.pk))
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

    def test_set_default_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.patch(self.set_default_url(self.address.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_set_default_does_not_affect_other_users_addresses(self):
        other_default = self.create_address(user=self.other_user, is_default=True)

        self.client.patch(self.set_default_url(self.address.pk))

        other_default.refresh_from_db()
        self.assertTrue(other_default.is_default)

    def test_set_default_on_nonexistent_address_returns_404(self):
        response = self.client.patch(self.set_default_url(9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# tests/test_wishlist.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from pieces.models import Piece
from users.models import WishList
import io
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient
from PIL import Image

from pieces.models import Piece, TypePiece, Section

User = get_user_model()

def fake_image(name='test.jpg'):
        """Genera una imagen JPEG real en memoria usando Pillow."""
        img = Image.new('RGB', (10, 10), color=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return SimpleUploadedFile(name, buf.read(), content_type='image/jpeg')
class WishListViewSetTest(APITestCase):

    


    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='testpass123'
        )
        self.type_piece = TypePiece.objects.create(type='Escultura', key='escultura')
        self.section = Section.objects.create(section='Tecnologia', key='tecnologia')
        
        self.piece = Piece.objects.create(
                title='Nueva Pieza',
                description='Descripción de prueba',
                quantity=5,
                price_base='100.00',
                width='10.00',
                height='20.00',
                length='5.00',
                weight='1.50',
                type=self.type_piece,
                section=self.section,
                thumbnail_path=fake_image(),
            )
        self.piece2 = Piece.objects.create(
                title='Nueva Pieza 2',
                description='Descripción de prueba 2',
                quantity=3,
                price_base='200.00',
                width='10.00',
                height='20.00',
                length='5.00',
                weight='1.50',
                type=self.type_piece,
                section=self.section,
                thumbnail_path=fake_image('test2.jpg'),
            )

        self.list_url = reverse('user:wishlist-list')

    def detail_url(self, pk):
        return reverse('user:wishlist-detail', args=[pk])

    # ── AUTH ──────────────────────────────────────────────────────────────────

    def test_unauthenticated_cannot_access(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── CREATE ────────────────────────────────────────────────────────────────

    def test_create_wishlist_item(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, {'piece_id': self.piece.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(WishList.objects.filter(user=self.user, piece=self.piece).exists())

    def test_create_reactivates_inactive_item(self):
        """Si el item existe pero está inactivo, lo reactiva en lugar de crear uno nuevo"""
        self.client.force_authenticate(user=self.user)
        wishlist_item = WishList.objects.create(
            user=self.user,
            piece=self.piece,
            is_active=False
        )

        response = self.client.post(self.list_url, {'piece_id': self.piece.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        wishlist_item.refresh_from_db()
        self.assertTrue(wishlist_item.is_active)
        self.assertEqual(WishList.objects.filter(user=self.user, piece=self.piece).count(), 1)

    def test_create_with_invalid_piece(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.list_url, {'piece_id': 99999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── LIST ──────────────────────────────────────────────────────────────────

    def test_list_returns_only_active_items(self):
        self.client.force_authenticate(user=self.user)
        WishList.objects.create(user=self.user, piece=self.piece, is_active=True)
        WishList.objects.create(user=self.user, piece=self.piece2, is_active=False)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)  # soporta con y sin paginación
        self.assertEqual(len(results), 1)

    def test_list_returns_only_own_items(self):
        self.client.force_authenticate(user=self.user)
        WishList.objects.create(user=self.user, piece=self.piece, is_active=True)
        WishList.objects.create(user=self.other_user, piece=self.piece2, is_active=True)

        response = self.client.get(self.list_url)

        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)

    def test_list_response_includes_piece_detail(self):
        self.client.force_authenticate(user=self.user)
        WishList.objects.create(user=self.user, piece=self.piece, is_active=True)

        response = self.client.get(self.list_url)

        results = response.data.get('results', response.data)
        self.assertIn('piece', results[0])
        self.assertEqual(results[0]['piece']['title'], self.piece.title)

    # ── DELETE ────────────────────────────────────────────────────────────────

    def test_delete_deactivates_item(self):
        """DELETE no borra el registro, solo desactiva is_active"""
        self.client.force_authenticate(user=self.user)
        item = WishList.objects.create(user=self.user, piece=self.piece, is_active=True)

        response = self.client.delete(self.detail_url(item.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        item.refresh_from_db()
        self.assertFalse(item.is_active)
        self.assertTrue(WishList.objects.filter(id=item.id).exists())  # sigue en BD

    def test_delete_other_users_item_returns_404(self):
        """Un usuario no puede desactivar el favorito de otro"""
        self.client.force_authenticate(user=self.user)
        item = WishList.objects.create(user=self.other_user, piece=self.piece, is_active=True)

        response = self.client.delete(self.detail_url(item.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── MÉTODOS NO PERMITIDOS ─────────────────────────────────────────────────

    def test_put_not_allowed(self):
        self.client.force_authenticate(user=self.user)
        item = WishList.objects.create(user=self.user, piece=self.piece, is_active=True)
        response = self.client.put(self.detail_url(item.id), {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_not_allowed(self):
        self.client.force_authenticate(user=self.user)
        item = WishList.objects.create(user=self.user, piece=self.piece, is_active=True)
        response = self.client.patch(self.detail_url(item.id), {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)