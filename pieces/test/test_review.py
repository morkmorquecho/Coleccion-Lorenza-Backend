# tests/test_reviews.py
import io
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from PIL import Image
from unittest.mock import patch
from pieces.models import Review, Piece, TypePiece, Section

User = get_user_model()

REVIEWS_URL = '/api/v1/reviews/'

def review_detail_url(pk):
    return f'/api/v1/reviews/{pk}/'

def fake_image(name='review.jpg'):
    img = Image.new('RGB', (10, 10), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/jpeg')

def review_payload(piece, **kwargs):
    data = {
        'piece': piece.pk,
        'rating': 4,
        'comment': 'Muy buena pieza',
        'photo': fake_image(),
    }
    data.update(kwargs)
    return data


class ReviewSetup(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_superuser(
            username='admin', password='admin123', email='admin@test.com'
        )
        self.user = User.objects.create_user(
            username='buyer', password='pass123', email='buyer@test.com'
        )
        self.other_user = User.objects.create_user(
            username='other', password='pass123', email='other@test.com'
        )

        self.type = TypePiece.objects.create(type='Escultura', key='escultura')
        self.section = Section.objects.create(section='Tecnologia', key='tecnologia')
        
        self.piece = Piece.objects.create(
            title='Obra Test',
            description='desc',
            quantity=5,
            price_base='100.00',
            width='10.00',
            height='20.00',
            length='5.00',
            weight='1.50',
            type=self.type,
            section=self.section,
            thumbnail_path = fake_image(),
        )

    def _make_review(self, user=None, piece=None, rating=5):
        """Crea una review saltando clean() para tests que no necesitan validar compra."""
        review = Review(
            user=user or self.user,
            piece=piece or self.piece,
            rating=rating,
            comment='Comentario de prueba',
            photo=fake_image(),
        )
        Review.objects.bulk_create([review])  # evita full_clean
        return Review.objects.filter(user=review.user, piece=review.piece).latest('id')


# ─────────────────────────────────────────────
# LIST - público
# ─────────────────────────────────────────────
class ReviewListTests(ReviewSetup):

    def test_list_unauthenticated(self):
        res = self.client.get(REVIEWS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_authenticated(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(REVIEWS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


# ─────────────────────────────────────────────
# RETRIEVE - público
# ─────────────────────────────────────────────
class ReviewRetrieveTests(ReviewSetup):

    def test_retrieve_unauthenticated(self):
        review = self._make_review()
        res = self.client.get(review_detail_url(review.pk))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['rating'], review.rating)


# ─────────────────────────────────────────────
# CREATE - solo autenticados
# ─────────────────────────────────────────────
class ReviewCreateTests(ReviewSetup):

    def test_create_unauthenticated_fails(self):
        payload = review_payload(self.piece)
        res = self.client.post(REVIEWS_URL, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('pieces.models.Review.clean')  # saltamos validación de compra
    def test_create_authenticated_success(self, mock_clean):
        mock_clean.return_value = None
        self.client.force_authenticate(self.user)
        payload = review_payload(self.piece)
        res = self.client.post(REVIEWS_URL, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['user'], str(self.user))

    @patch('pieces.models.Review.clean')
    def test_create_assigns_authenticated_user(self, mock_clean):
        """No debe permitir asignar otro usuario desde el body."""
        mock_clean.return_value = None
        self.client.force_authenticate(self.user)
        payload = review_payload(self.piece, user=self.other_user.pk)
        res = self.client.post(REVIEWS_URL, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['user'], str(self.user)) 

    def test_create_fails_if_not_purchased(self):
        self.client.force_authenticate(self.user)
        payload = review_payload(self.piece)
        res = self.client.post(REVIEWS_URL, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('pieces.models.Review.clean')
    def test_create_invalid_rating_fails(self, mock_clean):
        mock_clean.return_value = None
        self.client.force_authenticate(self.user)
        payload = review_payload(self.piece, rating=10)
        res = self.client.post(REVIEWS_URL, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────
# UPDATE/PATCH/DELETE - solo admin
# ─────────────────────────────────────────────
class ReviewAdminTests(ReviewSetup):

    def test_update_by_non_admin_fails(self):
        review = self._make_review()
        self.client.force_authenticate(self.user)
        res = self.client.patch(review_detail_url(review.pk), {'rating': 1})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch('pieces.models.Review.clean')
    def test_update_by_admin_success(self, mock_clean):
        mock_clean.return_value = None
        review = self._make_review()
        self.client.force_authenticate(self.admin)
        res = self.client.patch(review_detail_url(review.pk), {'rating': 2})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['rating'], 2)

    def test_delete_by_non_admin_fails(self):
        review = self._make_review()
        self.client.force_authenticate(self.user)
        res = self.client.delete(review_detail_url(review.pk))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch('pieces.models.Review.clean')
    def test_delete_by_admin_success(self, mock_clean):
        mock_clean.return_value = None
        review = self._make_review()
        self.client.force_authenticate(self.admin)
        res = self.client.delete(review_detail_url(review.pk))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

# ─────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────
class ReviewFilterTests(ReviewSetup):

    def setUp(self):
        super().setUp()
        self.piece2 = Piece.objects.create(
            title='Obra 2', description='desc', quantity=3,
            price_base='50.00', width='5.00', height='5.00',
            length='5.00', weight='1.00',
            type=self.type, section=self.section,
            thumbnail_path=fake_image(),
        )
        self.r1 = self._make_review(user=self.user, piece=self.piece, rating=5)
        self.r2 = self._make_review(user=self.other_user, piece=self.piece2, rating=2)

    def test_filter_by_user(self):
        res = self.client.get(REVIEWS_URL, {'user': self.user.pk})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(all(r['user'] == str(self.user) for r in res.data['results']))

    def test_filter_by_piece(self):
        res = self.client.get(REVIEWS_URL, {'piece': self.piece.pk})
        ids = [r['id'] for r in res.data['results']]
        self.assertIn(self.r1.pk, ids)
        self.assertNotIn(self.r2.pk, ids)

    def test_filter_by_exact_rating(self):
        res = self.client.get(REVIEWS_URL, {'rating': 5})
        self.assertTrue(all(r['rating'] == 5 for r in res.data['results']))

    def test_filter_by_rating_range(self):
        res = self.client.get(REVIEWS_URL, {'rating_min': 3, 'rating_max': 5})
        self.assertTrue(all(3 <= r['rating'] <= 5 for r in res.data['results']))