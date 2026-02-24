from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from pieces.models import TypePiece, Section
from users.models import User  # ajusta al path real


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def create_type_piece(type_name="Cerámica", key="ceramica"):
    return TypePiece.objects.create(type=type_name, key=key)


def create_section(section_name="Sala", key="sala"):
    return Section.objects.create(section=section_name, key=key)


def get_results(resp):
    if isinstance(resp.data, dict) and "results" in resp.data:
        return resp.data["results"]
    return resp.data


TYPE_LIST_URL   = "/api/v1/types/"
SECTION_LIST_URL = "/api/v1/sections/"


def type_detail_url(key):
    return f"/api/v1/types/{key}/"


def section_detail_url(key):
    return f"/api/v1/sections/{key}/"


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
# 1. TypePiece — LIST
# ══════════════════════════════════════════════

class TypePieceListTests(AnonClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.t1 = create_type_piece(type_name="Cerámica", key="ceramica")
        self.t2 = create_type_piece(type_name="Vidrio",   key="vidrio")

    def test_list_returns_200(self):
        resp = self.client.get(TYPE_LIST_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_returns_all_types(self):
        resp = self.client.get(TYPE_LIST_URL)
        results = get_results(resp)
        keys = [t["key"] for t in results]
        self.assertIn(self.t1.key, keys)
        self.assertIn(self.t2.key, keys)

    def test_list_accessible_by_anon(self):
        resp = self.client.get(TYPE_LIST_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_excludes_soft_deleted(self):
        from django.utils import timezone
        TypePiece.objects.filter(id=self.t1.id).update(deleted_at=timezone.now())
        resp = self.client.get(TYPE_LIST_URL)
        results = get_results(resp)
        keys = [t["key"] for t in results]
        self.assertNotIn(self.t1.key, keys)

    def test_list_response_contains_expected_fields(self):
        resp = self.client.get(TYPE_LIST_URL)
        item = get_results(resp)[0]
        self.assertIn("key",  item)
        self.assertIn("type", item)


# ══════════════════════════════════════════════
# 2. TypePiece — RETRIEVE
# ══════════════════════════════════════════════

class TypePieceRetrieveTests(AnonClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.t1 = create_type_piece(type_name="Cerámica", key="ceramica")

    def test_retrieve_returns_200(self):
        resp = self.client.get(type_detail_url(self.t1.key))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_retrieve_by_key_not_pk(self):
        """El lookup_field es 'key', no el id numérico."""
        resp = self.client.get(type_detail_url(self.t1.key))
        self.assertEqual(resp.data["key"], self.t1.key)

    def test_retrieve_returns_correct_fields(self):
        resp = self.client.get(type_detail_url(self.t1.key))
        self.assertEqual(resp.data["type"], self.t1.type)
        self.assertEqual(resp.data["key"],  self.t1.key)

    def test_retrieve_nonexistent_key_returns_404(self):
        resp = self.client.get(type_detail_url("clave-inexistente"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_accessible_by_anon(self):
        resp = self.client.get(type_detail_url(self.t1.key))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ══════════════════════════════════════════════
# 3. TypePiece — WRITE FORBIDDEN
# ══════════════════════════════════════════════

class TypePieceWriteForbiddenTests(AdminClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.t1 = create_type_piece()

    def test_post_not_allowed(self):
        resp = self.client.post(TYPE_LIST_URL, {"type": "Nuevo", "key": "nuevo"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_not_allowed(self):
        resp = self.client.put(type_detail_url(self.t1.key), {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_not_allowed(self):
        resp = self.client.patch(type_detail_url(self.t1.key), {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        resp = self.client.delete(type_detail_url(self.t1.key))
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ══════════════════════════════════════════════
# 4. Section — LIST
# ══════════════════════════════════════════════

class SectionListTests(AnonClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.s1 = create_section(section_name="Sala",    key="sala")
        self.s2 = create_section(section_name="Cocina",  key="cocina")

    def test_list_returns_200(self):
        resp = self.client.get(SECTION_LIST_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_returns_all_sections(self):
        resp = self.client.get(SECTION_LIST_URL)
        results = get_results(resp)
        keys = [s["key"] for s in results]
        self.assertIn(self.s1.key, keys)
        self.assertIn(self.s2.key, keys)

    def test_list_accessible_by_anon(self):
        resp = self.client.get(SECTION_LIST_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_excludes_soft_deleted(self):
        from django.utils import timezone
        Section.objects.filter(id=self.s1.id).update(deleted_at=timezone.now())
        resp = self.client.get(SECTION_LIST_URL)
        results = get_results(resp)
        keys = [s["key"] for s in results]
        self.assertNotIn(self.s1.key, keys)

    def test_list_response_contains_expected_fields(self):
        resp = self.client.get(SECTION_LIST_URL)
        item = get_results(resp)[0]
        self.assertIn("key",     item)
        self.assertIn("section", item)


# ══════════════════════════════════════════════
# 5. Section — RETRIEVE
# ══════════════════════════════════════════════

class SectionRetrieveTests(AnonClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.s1 = create_section(section_name="Sala", key="sala")

    def test_retrieve_returns_200(self):
        resp = self.client.get(section_detail_url(self.s1.key))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_retrieve_by_key_not_pk(self):
        """El lookup_field es 'key', no el id numérico."""
        resp = self.client.get(section_detail_url(self.s1.key))
        self.assertEqual(resp.data["key"], self.s1.key)

    def test_retrieve_returns_correct_fields(self):
        resp = self.client.get(section_detail_url(self.s1.key))
        self.assertEqual(resp.data["section"], self.s1.section)
        self.assertEqual(resp.data["key"],     self.s1.key)

    def test_retrieve_nonexistent_key_returns_404(self):
        resp = self.client.get(section_detail_url("clave-inexistente"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_accessible_by_anon(self):
        resp = self.client.get(section_detail_url(self.s1.key))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ══════════════════════════════════════════════
# 6. Section — WRITE FORBIDDEN
# ══════════════════════════════════════════════

class SectionWriteForbiddenTests(AdminClientMixin, APITestCase):

    def setUp(self):
        super().setUp()
        self.s1 = create_section()

    def test_post_not_allowed(self):
        resp = self.client.post(SECTION_LIST_URL, {"section": "Nueva", "key": "nueva"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_not_allowed(self):
        resp = self.client.put(section_detail_url(self.s1.key), {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_not_allowed(self):
        resp = self.client.patch(section_detail_url(self.s1.key), {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        resp = self.client.delete(section_detail_url(self.s1.key))
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)