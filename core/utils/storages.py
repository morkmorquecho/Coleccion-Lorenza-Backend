
def borrar_archivo_storage(imagen_field):
    """Elimina el archivo del storage (R2) si existe."""
    if imagen_field and imagen_field.name:
        storage = imagen_field.storage
        if storage.exists(imagen_field.name):
            storage.delete(imagen_field.name)