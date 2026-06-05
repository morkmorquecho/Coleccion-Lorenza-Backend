from modeltranslation.translator import register, TranslationOptions
from blog.models import Blog

@register(Blog)
class BlogTranslationOptions(TranslationOptions):
    fields = ('title', 'content')