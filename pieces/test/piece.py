import io
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient
from PIL import Image

from pieces.models import Piece, TypePiece, Section

User = get_user_model()

LIST_URL = '/api/v1/pieces/'


def detail_url(slug):
    return f'/api/v1/pieces/{slug}/'


def fake_image(name='test.jpg'):
    """Genera una imagen JPEG real en memoria usando Pillow."""
    img = Image.new('RGB', (10, 10), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/jpeg')


def piece_payload(type_piece, section, title='Mi Pieza', **kwargs):
    """Payload base con todos los campos requeridos de Piece."""
    data = {
        'title': title,
        'description': 'Descripción de prueba',
        'quantity': 5,
        'price_mx': '100.00',
        'price_usa': '200.00',
        'width': '10.00',
        'height': '20.00',
        'length': '5.00',
        'weight': '1.50',
        'type_id': type_piece.pk,
        'section_id': section.pk,
        'thumbnail_path': fake_image(),
    }
    data.update(kwargs)
    return data


class PieceBaseTestCase(TestCase):
    """Configuración compartida para todos los tests de Piece."""

    def setUp(self):
        self.client = APIClient()

        self.admin_user = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='admin123'
        )
        self.regular_user = User.objects.create_user(
            username='user', email='user@test.com', password='user123'
        )

        self.type_piece = TypePiece.objects.create(type='Escultura', key='escultura')
        self.section = Section.objects.create(section='Tecnologia', key='tecnologia')

        self.piece = Piece(
            title='Hello World',
            slug='hello-world',
            description='Descripción de prueba',
            quantity=3,
            price_mx=100,
            price_usa=200,
            width=10,
            height=20,
            length=5,
            weight=1.5,
            type=self.type_piece,
            section=self.section,
            thumbnail_path=fake_image(),
        )
        # usamos save sin full_clean para evitar validación de imagen en setUp
        Piece.save(self.piece)

    def as_admin(self):
        self.client.force_authenticate(user=self.admin_user)

    def as_user(self):
        self.client.force_authenticate(user=self.regular_user)

    def as_anonymous(self):
        self.client.force_authenticate(user=None)


# ── Lectura pública ───────────────────────────────────────────────────────────

# class PieceReadAccessTest(PieceBaseTestCase):

#     def test_list_pieces_unauthenticated(self):
#         response = self.client.get(LIST_URL)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#     def test_retrieve_piece_by_slug(self):
#         response = self.client.get(detail_url(self.piece.slug))
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['slug'], self.piece.slug)

#     def test_retrieve_nonexistent_piece_returns_404(self):
#         response = self.client.get(detail_url('no-existe'))
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

#     def test_list_returns_all_pieces(self):
#         Piece.objects.create(
#             title='Segunda Pieza',
#             slug='segunda-pieza',
#             description='Otra descripción',
#             quantity=1,
#             price_mx=50,
#             price_usa=150,
#             width=5,
#             height=10,
#             length=3,
#             weight=1.0,
#             type=self.type_piece,
#             section=self.section,
#             thumbnail_path=fake_image(),
#         )
#         response = self.client.get(LIST_URL)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         # ajusta si no usas paginación (cambia 'results' por response.data directamente)
#         self.assertEqual(len(response.data['results']), 2)


# ── Creación ──────────────────────────────────────────────────────────────────

class PieceCreateTest(PieceBaseTestCase):

    def test_admin_can_create_piece(self):
        self.as_admin()
        payload = piece_payload(self.type_piece, self.section, title='Nueva Pieza')
        response = self.client.post(LIST_URL, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['slug'], 'nueva-pieza')

    def test_slug_is_generated_from_title(self):
        self.as_admin()
        payload = piece_payload(self.type_piece, self.section, title='Hola Mundo Bonito')
        response = self.client.post(LIST_URL, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['slug'], 'hola-mundo-bonito')

    def test_slug_handles_spaces_and_uppercase(self):
        self.as_admin()
        payload = piece_payload(self.type_piece, self.section, title='Mi Gran Obra')
        response = self.client.post(LIST_URL, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn(' ', response.data['slug'])
        self.assertEqual(response.data['slug'], response.data['slug'].lower())

    def test_regular_user_cannot_create_piece(self):
        self.as_user()
        payload = piece_payload(self.type_piece, self.section)
        response = self.client.post(LIST_URL, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_create_piece(self):
        self.as_anonymous()
        payload = piece_payload(self.type_piece, self.section)
        response = self.client.post(LIST_URL, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_piece_is_saved_in_db(self):
        self.as_admin()
        payload = piece_payload(self.type_piece, self.section, title='Pieza en DB')
        response = self.client.post(LIST_URL, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Piece.objects.filter(slug='pieza-en-db').exists())


# ── Actualización ─────────────────────────────────────────────────────────────

class PieceUpdateTest(PieceBaseTestCase):

    def test_admin_can_partial_update_title(self):
        self.as_admin()
        response = self.client.patch(
            detail_url(self.piece.slug),
            {'title': 'Titulo Actualizado'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['slug'], 'titulo-actualizado')
        self.assertEqual(response.data['title'], 'Titulo Actualizado')

    def test_slug_updates_when_title_changes(self):
        self.as_admin()
        response = self.client.patch(
            detail_url(self.piece.slug),
            {'title': 'Nuevo Titulo Slug'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['slug'], 'nuevo-titulo-slug')

    def test_admin_can_full_update_piece(self):
        self.as_admin()
        payload = piece_payload(self.type_piece, self.section, title='Pieza Completa')
        response = self.client.put(detail_url(self.piece.slug), payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['slug'], 'pieza-completa')

    def test_regular_user_cannot_update_piece(self):
        self.as_user()
        response = self.client.patch(
            detail_url(self.piece.slug),
            {'title': 'Hack'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_update_piece(self):
        self.as_anonymous()
        response = self.client.patch(
            detail_url(self.piece.slug),
            {'title': 'Hack'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ── Eliminación ───────────────────────────────────────────────────────────────

class PieceDeleteTest(PieceBaseTestCase):

    def test_admin_can_delete_piece(self):
        self.as_admin()
        response = self.client.delete(detail_url(self.piece.slug))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Piece.objects.filter(slug=self.piece.slug).exists())

    def test_regular_user_cannot_delete_piece(self):
        self.as_user()
        response = self.client.delete(detail_url(self.piece.slug))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_delete_piece(self):
        self.as_anonymous()
        response = self.client.delete(detail_url(self.piece.slug))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_piece_removed_from_db(self):
        self.as_admin()
        slug = self.piece.slug
        self.client.delete(detail_url(slug))
        self.assertFalse(Piece.objects.filter(slug=slug).exists())


# ── Filtros ───────────────────────────────────────────────────────────────────

class PieceFilterTest(PieceBaseTestCase):

    def setUp(self):
        super().setUp()
        # sección extra para filtrar piezas que NO pertenecen a self.section
        self.other_section = Section.objects.create(section='Otro', key='otro')
        self.other_type = TypePiece.objects.create(type='Pintura', key='pintura')

    def test_filter_by_section_returns_matching_pieces(self):
        response = self.client.get(LIST_URL, {'section': self.section.key})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for result in response.data['results']:
            self.assertEqual(result['section'], self.section.key)

    def test_filter_by_type_returns_matching_pieces(self):
        response = self.client.get(LIST_URL, {'type': self.type_piece.key})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for result in response.data['results']:
            self.assertEqual(result['type'], self.type_piece.key)

    def test_filter_by_section_returns_empty_when_no_pieces_in_section(self):
        # other_section existe pero no tiene piezas asignadas
        response = self.client.get(LIST_URL, {'section': self.other_section.key})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_filter_by_type_returns_empty_when_no_pieces_of_type(self):
        # other_type existe pero no tiene piezas asignadas
        response = self.client.get(LIST_URL, {'type': self.other_type.key})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)