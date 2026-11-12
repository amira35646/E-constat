from django.urls import path
from . import views

urlpatterns = [
    path('', views.mes_constats, name='mes_constats'),
    path('nouveau/', views.creer_constat, name='constat_creer'),
    path('rejoindre/', views.rejoindre_constat, name='constat_rejoindre'),
    path('<str:code>/', views.detail_constat, name='constat_detail'),
    path('<str:code>/inviter/', views.inviter_conducteur_b, name='constat_inviter'),
]