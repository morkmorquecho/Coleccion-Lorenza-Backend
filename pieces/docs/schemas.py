from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from pieces.docs.params import PIECE_SLUG_PARAMETER
from pieces.serializer import PieceDiscountSerializer, PiecePhotoBulkCreateSerializer, PiecePhotoBulkDeleteSerializer, PiecePhotoReorderSerializer, PiecePhotoSerializer, PieceSerializer, SectionSerializer, TypePieceSerializer

_MODULE_PATH_PIECES = "pieces.views"

# ─────────────────────────────────────────────
# PIECE
# ─────────────────────────────────────────────

PIECE_VIEWSET = extend_schema_view(
    list=extend_schema(
        summary="Listar Piezas",
        tags=["pieces"],
        description=(
            "Retorna el listado de todas las piezas disponibles.\n\n"
            "Soporta filtros a través de `PieceFilter` (por tipo, sección, precio, etc.).\n\n"
            "Los resultados incluyen información relacionada de `type` y `section`.\n\n"
            "No requiere autenticación para lectura.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PieceViewSet_list`"
        ),
        responses={200: PieceSerializer}
    ),
    retrieve=extend_schema(
        summary="Obtener Pieza",
        tags=["pieces"],
        description=(
            "Retorna el detalle de una pieza específica identificada por su `slug`.\n\n"
            "No requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PieceViewSet_retrieve`"
        ),
        responses={
            200: PieceSerializer,
            404: OpenApiResponse(description="Pieza no encontrada."),
        }
    ),
    create=extend_schema(
        summary="Crear Pieza",
        tags=["pieces"],
        description=(
            "Crea una nueva pieza. El campo `slug` se genera automáticamente a partir del `title`.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PieceViewSet_create`"
        ),
        responses={
            201: PieceSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
        }
    ),
    update=extend_schema(
        summary="Actualizar Pieza",
        tags=["pieces"],
        description=(
            "Actualiza todos los campos de una pieza existente.\n\n"
            "Si el `title` cambia, el `slug` se recalcula automáticamente.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PieceViewSet_update`"
        ),
        responses={
            200: PieceSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
            404: OpenApiResponse(description="Pieza no encontrada."),
        }
    ),
    partial_update=extend_schema(
        summary="Actualizar Pieza Parcialmente",
        tags=["pieces"],
        description=(
            "Actualiza uno o más campos de una pieza sin necesidad de enviar el objeto completo.\n\n"
            "Si se modifica el `title`, el `slug` se recalcula automáticamente.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PieceViewSet_partial_update`"
        ),
        responses={
            200: PieceSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
            404: OpenApiResponse(description="Pieza no encontrada."),
        }
    ),
    destroy=extend_schema(
        summary="Eliminar Pieza",
        tags=["pieces"],
        description=(
            "Elimina una pieza existente identificada por su `slug`.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PieceViewSet_destroy`"
        ),
        responses={
            204: OpenApiResponse(description="Pieza eliminada correctamente."),
            404: OpenApiResponse(description="Pieza no encontrada."),
        }
    ),
)


# ─────────────────────────────────────────────
# PIECE PHOTO
# ─────────────────────────────────────────────

PIECE_PHOTO_VIEWSET = extend_schema_view(
    list=extend_schema(
        summary="Listar Fotos de una Pieza",
        tags=["pieces - photos"],
        parameters=[PIECE_SLUG_PARAMETER],
        description=(
            "Retorna todas las fotos activas (no eliminadas) de una pieza específica.\n\n"
            "No requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PiecePhotoViewSet_list`"
        ),
        responses={200: PiecePhotoSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Obtener Foto de una Pieza",
        tags=["pieces - photos"],
        parameters=[PIECE_SLUG_PARAMETER],
        description=(
            "Retorna el detalle de una foto específica perteneciente a la pieza indicada.\n\n"
            "No requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PiecePhotoViewSet_retrieve`"
        ),
        responses={
            200: PiecePhotoSerializer,
            404: OpenApiResponse(description="Foto no encontrada."),
        }
    ),
    create=extend_schema(
        summary="Crear Foto de una Pieza",
        parameters=[PIECE_SLUG_PARAMETER],
        tags=["pieces - photos"],
        description=(
            "Sube una foto individual y la asocia a la pieza indicada por `piece_slug`.\n\n"
            "Para subida de múltiples imágenes usar el endpoint `bulk-create`.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PiecePhotoViewSet_create`"
        ),
        responses={
            201: PiecePhotoSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
        }
    ),
    update=extend_schema(
        summary="Actualizar Foto de una Pieza",
        tags=["pieces - photos"],
        parameters=[PIECE_SLUG_PARAMETER],        
        description=(
            "Actualiza todos los campos de una foto existente perteneciente a la pieza indicada.\n\n"
            "Solo el propietario de la pieza puede modificarla.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PiecePhotoViewSet_update`"
        ),
        responses={
            200: PiecePhotoSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
            404: OpenApiResponse(description="Foto no encontrada."),
        }
    ),
    partial_update=extend_schema(
        summary="Actualizar Foto de una Pieza Parcialmente",
        tags=["pieces - photos"],
        parameters=[PIECE_SLUG_PARAMETER],
        description=(
            "Actualiza uno o más campos de una foto existente perteneciente a la pieza indicada.\n\n"
            "Solo el propietario de la pieza puede modificarla.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PiecePhotoViewSet_partial_update`"
        ),
        responses={
            200: PiecePhotoSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
            404: OpenApiResponse(description="Foto no encontrada."),
        }
    ),
    destroy=extend_schema(
        summary="Eliminar Foto de una Pieza",
        tags=["pieces - photos"],
        parameters=[PIECE_SLUG_PARAMETER],
        description=(
            "Elimina una foto específica de la pieza indicada.\n\n"
            "Para eliminar múltiples fotos a la vez usar el endpoint `bulk-delete`.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PiecePhotoViewSet_destroy`"
        ),
        responses={
            204: OpenApiResponse(description="Foto eliminada correctamente."),
            404: OpenApiResponse(description="Foto no encontrada."),
        }
    ),
    bulk_create=extend_schema(
        summary="Subida Masiva de Fotos",
        tags=["pieces - photos"],
        parameters=[PIECE_SLUG_PARAMETER],        
        description=(
            "Permite subir múltiples imágenes a una pieza en una sola petición.\n\n"
            "El body debe enviarse como `multipart/form-data` con el campo `images` conteniendo los archivos.\n\n"
            "Las posiciones se asignan automáticamente de forma consecutiva a partir de la última existente.\n\n"
            "La operación es atómica: si alguna imagen falla, ninguna se guarda.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PiecePhotoViewSet_bulk_create`"
        ),
        request=PiecePhotoBulkCreateSerializer,
        responses={
            201: PiecePhotoSerializer(many=True),
            400: OpenApiResponse(description="Datos inválidos o límite de fotos excedido."),
        }
    ),
    reorder=extend_schema(
        summary="Reordenar Fotos de una Pieza",
        tags=["pieces - photos"],
        parameters=[PIECE_SLUG_PARAMETER],        
        description=(
            "Permite reordenar múltiples fotos de una pieza en una sola petición.\n\n"
            "El body debe incluir una lista de objetos con `id` y `position`.\n\n"
            "Todos los IDs enviados deben pertenecer a la pieza indicada.\n\n"
            "La operación es atómica para evitar conflictos de posición duplicada.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PiecePhotoViewSet_reorder`"
        ),
        request=PiecePhotoReorderSerializer,
        responses={
            200: PiecePhotoSerializer(many=True),
            400: OpenApiResponse(description="Algunos IDs no pertenecen a esta pieza."),
        }
    ),
    bulk_delete=extend_schema(
        summary="Eliminación Masiva de Fotos",
        tags=["pieces - photos"],
        parameters=[PIECE_SLUG_PARAMETER],        
        description=(
            "Elimina múltiples fotos de una pieza en una sola petición.\n\n"
            "El body debe incluir una lista de `ids` a eliminar.\n\n"
            "Solo se eliminarán fotos que pertenezcan a la pieza indicada por seguridad.\n\n"
            "Retorna 404 si ningún ID corresponde a fotos de la pieza.\n\n"
            "Requiere autenticación de administrador.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PiecePhotoViewSet_bulk_delete`"
        ),
        request=PiecePhotoBulkDeleteSerializer,
        responses={
            200: OpenApiResponse(description="Fotos eliminadas correctamente."),
            404: OpenApiResponse(description="No se encontraron fotos con esos IDs."),
        }
    ),
)


# ─────────────────────────────────────────────
# PIECE DISCOUNT
# ─────────────────────────────────────────────

PIECE_DISCOUNT_VIEWSET = extend_schema_view(
    list=extend_schema(
        summary="Listar Descuentos de una Pieza",
        tags=["pieces - discounts"],
        parameters=[PIECE_SLUG_PARAMETER],        
        description=(
            "Retorna todos los descuentos activos (no eliminados) asociados a una pieza.\n\n"
            "Los resultados incluyen información relacionada del descuento (`discount`).\n\n"
            "No requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PieceDiscountViewSet_list`"
        ),
        responses={200: PieceDiscountSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Obtener Descuento de una Pieza",
        tags=["pieces - discounts"],
        parameters=[PIECE_SLUG_PARAMETER],        
        description=(
            "Retorna el detalle de un descuento específico vinculado a la pieza indicada.\n\n"
            "No requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.PieceDiscountViewSet_retrieve`"
        ),
        responses={
            200: PieceDiscountSerializer,
            404: OpenApiResponse(description="Descuento no encontrado."),
        }
    ),
)


# ─────────────────────────────────────────────
# TYPE PIECE
# ─────────────────────────────────────────────

TYPE_PIECE_VIEWSET = extend_schema_view(
    list=extend_schema(
        summary="Listar Tipos de Pieza",
        tags=["pieces - types"],
        description=(
            "Retorna el catálogo completo de tipos de pieza disponibles.\n\n"
            "No requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.TypePieceViewSet_list`"
        ),
        responses={200: TypePieceSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Obtener Tipo de Pieza",
        tags=["pieces - types"],
        description=(
            "Retorna el detalle de un tipo de pieza identificado por su `key`.\n\n"
            "No requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.TypePieceViewSet_retrieve`"
        ),
        responses={
            200: TypePieceSerializer,
            404: OpenApiResponse(description="Tipo de pieza no encontrado."),
        }
    ),
)


# ─────────────────────────────────────────────
# SECTION
# ─────────────────────────────────────────────

SECTION_VIEWSET = extend_schema_view(
    list=extend_schema(
        summary="Listar Secciones",
        tags=["pieces - sections"],
        description=(
            "Retorna el catálogo completo de secciones disponibles.\n\n"
            "No requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.SectionViewSet_list`"
        ),
        responses={200: SectionSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Obtener Sección",
        tags=["pieces - sections"],
        description=(
            "Retorna el detalle de una sección identificada por su `key`.\n\n"
            "No requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_PIECES}.SectionViewSet_retrieve`"
        ),
        responses={
            200: SectionSerializer,
            404: OpenApiResponse(description="Sección no encontrada."),
        }
    ),
)