# utils.py (créalo en tu app)
import os
import uuid

def upload_pieces_thumb(instance, filename):
    ext = os.path.splitext(filename)[1].lower()  
    
    # Si el objeto ya tiene ID lo usamos, si no generamos un uuid temporal
    identificador = instance.pk if instance.pk else uuid.uuid4().hex
    
    nuevo_nombre = f"{identificador}{ext}"
    return f"pieces/thumbnails/{nuevo_nombre}"

def upload_piece_image(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    identificador = instance.pk if instance.pk else uuid.uuid4().hex
    # Usa el PK de la pieza padre para la carpeta
    piece_pk = instance.piece_id if instance.piece_id else 'temp'
    return f"pieces/{piece_pk}/{identificador}{ext}"