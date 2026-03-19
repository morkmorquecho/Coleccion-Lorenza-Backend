from django.db import models
from blog.utils import upload_image_blog
from core.mixins import ImagenPKMixin
from core.models import BaseModel
from pieces.models import Piece, Section

class Blog(ImagenPKMixin, BaseModel):
    title = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    cover_image = models.ImageField(upload_to=upload_image_blog)
    pieces = models.ManyToManyField( Piece, related_name="blogs", blank=True)
    status = models.CharField( max_length=10,
        choices=[("draft", "Draft"), 
                 ("published", "Published")
        ]
    )
    published_at = models.DateTimeField(null=True, blank=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Blog'
        verbose_name_plural = 'Blogs'

    def __str__(self):
        return f'{self.title}'