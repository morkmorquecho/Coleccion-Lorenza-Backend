from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework import permissions

class IsAdminOrReadOnly(BasePermission):
    """
    Permite lectura a cualquier usuario (autenticado o no),
    solo admins pueden escribir o eliminar.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
    
class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id 