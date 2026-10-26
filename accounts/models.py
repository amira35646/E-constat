from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        CONDUCTEUR = 'conducteur', 'Conducteur'
        ADMIN = 'admin', 'Administrateur'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CONDUCTEUR)
    telephone = models.CharField(max_length=20, blank=True)
