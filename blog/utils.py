import os
import uuid

from core.utils.upload_images import generate_upload_path


def upload_image_blog(instance, filename):
    return generate_upload_path('blog', instance, filename, purpose='thumbnail')