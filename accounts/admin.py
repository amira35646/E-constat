from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Informations e-Constat', {'fields': ('role', 'telephone')}),)
    list_display = ('username', 'email', 'role', 'is_active')