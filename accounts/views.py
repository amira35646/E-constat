from django.contrib.auth import login
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render, redirect

from .forms import InscriptionForm
from .models import User


def inscription(request):
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = InscriptionForm()
    return render(request, 'accounts/inscription.html', {'form': form})


def est_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == User.Role.ADMIN)


def liste_utilisateurs(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not est_admin(request.user):
        raise PermissionDenied

    q = request.GET.get('q', '').strip()
    utilisateurs = User.objects.order_by('-date_joined')
    if q:
        utilisateurs = utilisateurs.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(email__icontains=q)
        )

    return render(request, 'accounts/liste_utilisateurs.html', {
        'utilisateurs': utilisateurs,
        'q': q,
    })