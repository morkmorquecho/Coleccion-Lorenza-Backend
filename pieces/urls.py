# urls.py
from django.urls import include, path
from pieces.views import PieceDiscountViewSet, PiecePhotoViewSet, PieceViewSet, TypePieceViewSet, SectionViewSet
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

router = DefaultRouter()
router.register(r'pieces', PieceViewSet, basename='piece')
router.register(r'types', TypePieceViewSet, basename='type')
router.register(r'sections', SectionViewSet, basename='section')

pieces_router = routers.NestedSimpleRouter(router, r'pieces', lookup='piece')
pieces_router.register(r'photos', PiecePhotoViewSet, basename='piece-photos')
pieces_router.register(r'discounts', PieceDiscountViewSet, basename='piece-discounts')

pieces_patterns = ([
    path('', include(router.urls)),
    path('', include(pieces_router.urls)),
])