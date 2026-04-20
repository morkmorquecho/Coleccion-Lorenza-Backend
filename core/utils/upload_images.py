from datetime import datetime
from uuid import uuid4
import os

def generate_upload_path(base_folder, instance, filename, purpose='general', owner_field=None):
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    if ext not in ('jpg', 'jpeg', 'png', 'webp', 'mp4', 'mov'):
        ext = 'jpg'

    if owner_field:
        owner = getattr(instance, owner_field)
        owner_id = owner.pk
    else:
        owner_id = instance.uid  
    unique_name = uuid4().hex[:12]
    return f"{base_folder}/{owner_id}/{purpose}/{unique_name}.{ext}"