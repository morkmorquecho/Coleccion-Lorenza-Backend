import io
from PIL import Image

from django.test import TestCase
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from blog.models import Blog
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


def make_blog(**kwargs):
    defaults = {
        "title": "Test Blog",
        "slug": "test-blog",
        "content": "Some content",
        "status": "published",
        "published_at": timezone.now(),
    }
    defaults.update(kwargs)
    return Blog.objects.create(**defaults)

def make_image(name="test.jpg"):
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=(0, 255, 0)).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")

class BlogListTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("blog:blogs-list")
        self.admin = User.objects.create_superuser("admin", password="pass")
        self.user = User.objects.create_user("user", password="pass")

    def test_list_published_blogs_unauthenticated(self):
        make_blog(slug="blog-1")
        make_blog(slug="blog-2", status="draft")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_returns_all_blogs_as_admin(self):
        make_blog(slug="blog-1")
        make_blog(slug="blog-2", status="draft")
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_empty(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)


class BlogRetrieveTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.blog = make_blog()
        self.url = reverse("blog:blogs-detail", args=[self.blog.pk])

    def test_retrieve_blog_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], self.blog.slug)

    def test_retrieve_returns_correct_fields(self):
        response = self.client.get(self.url)
        for field in ("title", "slug", "content", "status", "published_at"):
            self.assertIn(field, response.data)

    def test_retrieve_not_found(self):
        url = reverse("blog:blogs-detail", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BlogCreateTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("blog:blogs-list")
        self.admin = User.objects.create_superuser("admin", password="pass")
        self.user = User.objects.create_user("user", password="pass")
        self.payload = {
            "title": "New Blog",
            "slug": "new-blog",
            "content": "Content here",
            "status": "draft",
        }

    def test_create_blog_as_admin(self):
        self.client.force_authenticate(self.admin)
        payload = {**self.payload, "cover_image": make_image()}
        response = self.client.post(self.url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_blog_unauthenticated_is_forbidden(self):
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_blog_as_regular_user_is_forbidden(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_blog_duplicate_slug(self):
        make_blog(slug="new-blog")
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_blog_missing_required_fields(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BlogUpdateTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser("admin", password="pass")
        self.user = User.objects.create_user("user", password="pass")
        self.blog = make_blog()
        self.url = reverse("blog:blogs-detail", args=[self.blog.pk])

    def test_full_update_as_admin(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "title": "Updated",
            "slug": "updated-slug", 
            "content": "Updated content",
            "status": "published",
            "published_at": timezone.now(),
            "cover_image": make_image(),
        }
        response = self.client.put(self.url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_partial_update_as_admin(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(self.url, {"title": "Patched Title"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.blog.refresh_from_db()
        self.assertEqual(self.blog.title, "Patched Title")

    def test_update_unauthenticated_is_forbidden(self):
        response = self.client.patch(self.url, {"title": "Hacked"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_as_regular_user_is_forbidden(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(self.url, {"title": "Hacked"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class BlogDeleteTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser("admin", password="pass")
        self.user = User.objects.create_user("user", password="pass")
        self.blog = make_blog()
        self.url = reverse("blog:blogs-detail", args=[self.blog.pk])

    def test_delete_as_admin(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Blog.objects.filter(pk=self.blog.pk).exists())

    def test_delete_unauthenticated_is_forbidden(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_as_regular_user_is_forbidden(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)