from django.contrib import admin
from .models import Constat, Partie, Vehicule, Photo, AnalyseIA


class PartieInline(admin.TabularInline):
    model = Partie
    extra = 0
    fields = ('role', 'conducteur', 'nom', 'prenom', 'valide')


@admin.register(Constat)
class ConstatAdmin(admin.ModelAdmin):
    list_display = ('code', 'statut', 'date_accident', 'lieu', 'createur', 'created_at')
    list_filter = ('statut', 'date_accident')
    search_fields = ('code', 'lieu', 'createur__username')
    readonly_fields = ('code', 'created_at', 'updated_at')
    inlines = [PartieInline]


class VehiculeInline(admin.StackedInline):
    model = Vehicule
    extra = 0


@admin.register(Partie)
class PartieAdmin(admin.ModelAdmin):
    list_display = ('constat', 'role', 'nom', 'prenom', 'conducteur', 'valide')
    list_filter = ('role', 'valide')
    search_fields = ('nom', 'prenom', 'numero_permis', 'constat__code')
    inlines = [VehiculeInline]


class AnalyseInline(admin.StackedInline):
    model = AnalyseIA
    extra = 0


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'partie', 'uploaded_at')
    inlines = [AnalyseInline]


@admin.register(AnalyseIA)
class AnalyseIAAdmin(admin.ModelAdmin):
    list_display = ('photo', 'verdict', 'score', 'analyse_le')
    list_filter = ('verdict',)