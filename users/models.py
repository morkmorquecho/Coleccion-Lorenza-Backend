from django.db import models
from django.contrib.auth.models import User  # Importar User correctamente
from blog.models import BaseModel  # Solo importar BaseModel del blog

class Address(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # ✅ Corregido
    # ... otros campos ...