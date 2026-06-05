from modeltranslation.translator import register, TranslationOptions
from .models import *

@register(TypePiece)
class TypePiecesTranslationOptions(TranslationOptions):
    fields = ('type',)

@register(Section)
class SectionTranslationOptions(TranslationOptions):
    fields = ('section',)

@register(Piece)
class PieceTranslationOptions(TranslationOptions):
    fields = ('title','description')