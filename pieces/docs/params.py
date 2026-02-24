from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
    
PIECE_SLUG_PARAMETER = OpenApiParameter(
    name="piece_slug",
    type=str,
    location=OpenApiParameter.PATH,
    description="Slug de la pieza",
)