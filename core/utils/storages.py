
import os
import uuid


def borrar_archivo_storage(imagen_field):
    """Elimina el archivo del storage (R2) si existe."""
    if imagen_field and imagen_field.name:
        storage = imagen_field.storage
        if storage.exists(imagen_field.name):
            storage.delete(imagen_field.name)

def archivo_campo_cambio(instance, anterior, field_name: str) -> bool:
    """
    Retorna True si el archivo de `field_name` cambió entre
    la instancia anterior y la nueva.
    Compatible con cualquier FileField / ImageField de Django.
    """
    archivo_anterior = getattr(anterior, field_name)
    archivo_nuevo = getattr(instance, field_name)
    nombre_nuevo = archivo_nuevo.name if archivo_nuevo else None
    return bool(
        archivo_anterior
        and archivo_anterior.name
        and archivo_anterior.name != nombre_nuevo
    )
