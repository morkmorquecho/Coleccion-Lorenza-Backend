import os
import uuid


def upload_image_blog(instance, filename):
    ext = os.path.splitext(filename)[1].lower()  
    
    identificador = instance.pk if instance.pk else uuid.uuid4().hex
    
    nuevo_nombre = f"{identificador}{ext}"
    return f"blog/{nuevo_nombre}"