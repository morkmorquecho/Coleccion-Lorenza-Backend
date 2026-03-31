from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
)
from drf_spectacular.types import OpenApiTypes

from blog.serializer import BlogSerializer

_MODULE_PATH_BLOG = "blog.views"

# ─────────────────────────────────────────────
# PIECE
# ─────────────────────────────────────────────

BLOG_VIEWSET = extend_schema_view(
    list=extend_schema(
        summary="Listar Articulos de blogs",
        tags=["blog"],
        description=(
            "Retorna el listado de todas las Articulos disponibles.\n\n"
            "No requiere autenticación para lectura.\n\n"
            f"**Code:** `{_MODULE_PATH_BLOG}.BlogViewSet_list`"
        ),
        responses={200: BlogSerializer}
    ),
    retrieve=extend_schema(
        summary="Obtener Articulo",
        tags=["blog"],
        description=(
            "Retorna el detalle de una Articulo específico.\n\n"
            "No requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_BLOG}.BlogViewSet_retrieve`"
        ),
        responses={
            200: BlogSerializer,
            404: OpenApiResponse(description="Articulo no encontrada."),
        }
    ),
    create=extend_schema(
        summary="Crear Articulo",
        tags=["blog"],
        description=(
            "Crea una nueva Articulo. El campo `slug` se genera automáticamente a partir del `title`.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_BLOG}.BlogViewSet_create`"
        ),
        responses={
            201: BlogSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
        }
    ),
    update=extend_schema(
        summary="Actualizar Articulo",
        tags=["blog"],
        description=(
            "Actualiza todos los campos de una Articulo existente.\n\n"
            "Si el `title` cambia, el `slug` se recalcula automáticamente.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_BLOG}.BlogViewSet_update`"
        ),
        responses={
            200: BlogSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
            404: OpenApiResponse(description="Articulo no encontrada."),
        }
    ),
    partial_update=extend_schema(
        summary="Actualizar Articulo Parcialmente",
        tags=["blog"],
        description=(
            "Actualiza uno o más campos de una Articulo sin necesidad de enviar el objeto completo.\n\n"
            "Si se modifica el `title`, el `slug` se recalcula automáticamente.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_BLOG}.BlogViewSet_partial_update`"
        ),
        responses={
            200: BlogSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
            404: OpenApiResponse(description="Articulo no encontrada."),
        }
    ),
    destroy=extend_schema(
        summary="Eliminar Articulo",
        tags=["blog"],
        description=(
            "Elimina una Articulo existente identificada por su `slug`.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_BLOG}.BlogViewSet_destroy`"
        ),
        responses={
            204: OpenApiResponse(description="Articulo eliminada correctamente."),
            404: OpenApiResponse(description="Articulo no encontrada."),
        }
    ),
)