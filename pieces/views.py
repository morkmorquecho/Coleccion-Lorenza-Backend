from django.shortcuts import get_object_or_404, render
from rest_framework.response import Response
from rest_framework import viewsets
from django.utils.text import slugify
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet

from core.mixins import ViewSetSentryMixin
from pieces.docs.schemas import PIECE_DISCOUNT_VIEWSET, PIECE_PHOTO_VIEWSET, PIECE_VIEWSET, SECTION_VIEWSET, TYPE_PIECE_VIEWSET
from .models import PieceDiscount, PiecePhoto, TypePiece, Section
from core.permission import IsAdminOrReadOnly
from pieces.filters import PieceFilter
from pieces.models import Piece
from pieces.serializer import PieceDiscountSerializer, PiecePhotoBulkCreateSerializer, PiecePhotoBulkDeleteSerializer, PiecePhotoReorderSerializer, PiecePhotoSerializer, PieceSerializer, TypePieceSerializer, SectionSerializer
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action

@PIECE_VIEWSET
class PieceViewSet(ViewSetSentryMixin, ModelViewSet):
    queryset = Piece.objects.select_related('type', 'section')
    serializer_class = PieceSerializer
    lookup_field = 'slug'
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = PieceFilter

    def perform_create(self, serializer):
        serializer.save(slug=slugify(serializer.validated_data['title']))

    def perform_update(self, serializer):
        serializer.save(slug=slugify(serializer.validated_data.get(
            'title', serializer.instance.title
        )))

@PIECE_PHOTO_VIEWSET
class PiecePhotoViewSet(ViewSetSentryMixin, ModelViewSet):
    serializer_class = PiecePhotoSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False): 
            return PiecePhoto.objects.none()
        return PiecePhoto.objects.filter(
            piece__slug=self.kwargs['piece_slug'],
            deleted_at__isnull=True
        )
    
    def perform_create(self, serializer):
        piece = self.get_piece()
        serializer.save(piece=piece)

    # Helper para no repetir esta lógica en cada action
    def get_piece(self):
        return get_object_or_404(Piece, slug=self.kwargs['piece_slug'])

    # -------------------------------------------------------
    # SUBIDA MASIVA
    # POST /pieces/{slug}/photos/bulk-create/
    # Body: form-data con campo "images" (múltiples archivos)
    # -------------------------------------------------------
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request, *args, **kwargs):
        piece = self.get_piece()

        serializer = PiecePhotoBulkCreateSerializer(
            data=request.data,
            context={'piece': piece}  # lo pasamos para validar el límite
        )
        serializer.is_valid(raise_exception=True)

        images = serializer.validated_data['images']

        # Calculamos desde qué posición seguir
        last_position = (
            PiecePhoto.objects.filter(piece=piece)
            .order_by('-position')
            .values_list('position', flat=True)
            .first() or 0  # si no hay fotos, empezamos desde 0
        )

        # transaction.atomic() garantiza que se guardan todas o ninguna
        with transaction.atomic():
            created = []
            for i, image in enumerate(images, start=1):
                photo = PiecePhoto.objects.create(
                    piece=piece,
                    image_path=image,
                    position=last_position + i
                )
                created.append(photo)

        return Response(
            PiecePhotoSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED
        )

    # -------------------------------------------------------
    # REORDENAMIENTO MASIVO
    # PATCH /pieces/{slug}/photos/reorder/
    # Body: {"photos": [{"id": "abc", "position": 1}, ...]}
    # -------------------------------------------------------
    @action(detail=False, methods=['patch'], url_path='reorder')
    def reorder(self, request, *args, **kwargs):
        piece = self.get_piece()

        serializer = PiecePhotoReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        photos_data = serializer.validated_data['photos']

        # Verificamos que todos los IDs pertenecen a esta pieza
        ids = [item['id'] for item in photos_data]
        photos = PiecePhoto.objects.filter(piece=piece, id__in=ids)

        if photos.count() != len(ids):
            return Response(
                {"detail": "Algunos IDs no pertenecen a esta pieza."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # El truco del reordenamiento sin violar unique_together:
        # Primero ponemos posiciones temporales negativas, luego las reales.
        # Sin esto, si foto A tiene position=1 y foto B tiene position=2,
        # al intentar cambiarlas directamente violarías el unique_together.
        with transaction.atomic():
            photo_map = {str(p.id): p for p in photos}

            # Paso 1: posiciones temporales para evitar conflictos
            for item in photos_data:
                photo = photo_map[str(item['id'])]
                photo.position = -(item['position'])  # negativo temporal
                photo.save()

            # Paso 2: posiciones reales
            for item in photos_data:
                photo = photo_map[str(item['id'])]
                photo.position = item['position']
                photo.save()

        return Response(
            PiecePhotoSerializer(photos.order_by('position'), many=True).data
        )

    # -------------------------------------------------------
    # BORRADO MASIVO
    # DELETE /pieces/{slug}/photos/bulk-delete/
    # Body: {"ids": ["abc", "xyz"]}
    # -------------------------------------------------------
    @action(detail=False, methods=['delete'], url_path='bulk-delete')
    def bulk_delete(self, request, *args, **kwargs):
        piece = self.get_piece()

        serializer = PiecePhotoBulkDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = serializer.validated_data['ids']

        # Solo borramos fotos que pertenecen a esta pieza (seguridad)
        photos = PiecePhoto.objects.filter(piece=piece, id__in=ids)
        deleted_count = photos.count()

        if deleted_count == 0:
            return Response(
                {"detail": "No se encontraron fotos con esos IDs."},
                status=status.HTTP_404_NOT_FOUND
            )

        photos.hard_delete()
        
        return Response(
            {"detail": f"{deleted_count} fotos eliminadas."},
            status=status.HTTP_200_OK
        )

@PIECE_DISCOUNT_VIEWSET
class PieceDiscountViewSet(ViewSetSentryMixin, ReadOnlyModelViewSet):
    serializer_class = PieceDiscountSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False): 
            return PieceDiscount.objects.none()
        return PieceDiscount.objects.filter(
            piece__slug = self.kwargs['piece_slug'],
            deleted_at__isnull=True
        ).select_related('discount')

@TYPE_PIECE_VIEWSET
class TypePieceViewSet(ViewSetSentryMixin, ReadOnlyModelViewSet):
    queryset = TypePiece.objects.all()
    serializer_class = TypePieceSerializer
    lookup_field = "key"
    permission_classes = [IsAdminOrReadOnly]

@SECTION_VIEWSET
class SectionViewSet(ViewSetSentryMixin, ReadOnlyModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    lookup_field = "key"
    permission_classes = [IsAdminOrReadOnly]
