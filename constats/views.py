from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .emails import MAX_INVITATIONS, envoyer_invitation
from .forms import ConstatForm, InvitationForm, PartieForm, PhotosForm, VehiculeForm
from .models import Constat, Partie, Photo


def _est_admin(user):
    return user.is_superuser or user.role == 'admin'


# ---------- Liste des constats de l'utilisateur ----------
@login_required
def mes_constats(request):
    parties = (
        Partie.objects.filter(conducteur=request.user)
        .select_related('constat')
        .order_by('-constat__created_at')
    )
    return render(request, 'constats/liste.html', {'parties': parties})


# ---------- Étape 4 : le conducteur A crée le constat ----------
@login_required
def creer_constat(request):
    user = request.user

    if request.method == 'POST':
        constat_form = ConstatForm(request.POST)
        partie_form = PartieForm(request.POST, prefix='partie')
        vehicule_form = VehiculeForm(request.POST, prefix='vehicule')
        photos_form = PhotosForm(request.POST, request.FILES)

        # Évalue tous les formulaires pour afficher toutes les erreurs d'un coup
        valides = [f.is_valid() for f in (constat_form, partie_form, vehicule_form, photos_form)]

        if all(valides):
            with transaction.atomic():
                constat = constat_form.save(commit=False)
                constat.createur = user
                constat.statut = Constat.Statut.ATTENTE_B
                constat.save()

                partie = partie_form.save(commit=False)
                partie.constat = constat
                partie.conducteur = user
                partie.role = Partie.Role.A
                partie.save()

                vehicule = vehicule_form.save(commit=False)
                vehicule.partie = partie
                vehicule.save()

                for fichier in photos_form.cleaned_data['photos']:
                    Photo.objects.create(partie=partie, image=fichier)

            # Envoi automatique du code au conducteur B (si son e-mail est renseigné)
            if not constat.email_b:
                messages.success(request, "Constat créé. Transmettez le code ci-dessous à l'autre conducteur.")
            elif envoyer_invitation(constat, request):
                messages.success(request, f"Constat créé. Le code a été envoyé à {constat.email_b}.")
            else:
                messages.warning(request, "Constat créé, mais l'e-mail n'a pas pu être envoyé. "
                                          "Transmettez le code manuellement ou réessayez ci-dessous.")
            return redirect('constat_detail', code=constat.code)
    else:
        constat_form = ConstatForm()
        partie_form = PartieForm(
            prefix='partie',
            initial={'nom': user.last_name, 'prenom': user.first_name, 'telephone': user.telephone},
        )
        vehicule_form = VehiculeForm(prefix='vehicule')
        photos_form = PhotosForm()

    return render(request, 'constats/creer.html', {
        'constat_form': constat_form,
        'partie_form': partie_form,
        'vehicule_form': vehicule_form,
        'photos_form': photos_form,
    })


# ---------- Détail d'un constat ----------
@login_required
def detail_constat(request, code):
    constat = get_object_or_404(Constat, code=code.upper())
    ma_partie = constat.parties.filter(conducteur=request.user).first()

    # Seuls les participants et les administrateurs voient un constat
    if ma_partie is None and not _est_admin(request.user):
        raise Http404

    return render(request, 'constats/detail.html', {
        'constat': constat,
        'ma_partie': ma_partie,
        'partie_a': constat.partie_a,
        'partie_b': constat.partie_b,
    })


# ---------- Étape 5 : le conducteur B rejoint le constat ----------
MAX_ESSAIS = 5          # codes erronés autorisés
DUREE_BLOCAGE = 600     # en secondes (10 minutes)


def _normaliser_code(code):
    """Enlève les espaces et met en majuscules : « k7mz 4qpa » devient « K7MZ4QPA »."""
    return ''.join((code or '').split()).upper()


@login_required
def rejoindre_constat(request):
    code = _normaliser_code(request.GET.get('code') or request.POST.get('code'))
    cle = f'essais_code_{request.user.pk}'

    # Protection contre les essais répétés de codes
    if cache.get(cle, 0) >= MAX_ESSAIS:
        messages.error(request, "Trop de tentatives. Réessayez dans quelques minutes.")
        return redirect('home')

    constat = Constat.objects.filter(code=code).first() if code else None

    # Message volontairement identique pour « code inconnu » et « constat complet »
    if constat is None or constat.statut != Constat.Statut.ATTENTE_B:
        cache.set(cle, cache.get(cle, 0) + 1, DUREE_BLOCAGE)
        messages.error(request, "Code invalide ou constat déjà complet.")
        return redirect('home')

    # Le conducteur A (ou B) qui ouvre son propre constat est simplement redirigé
    if constat.parties.filter(conducteur=request.user).exists():
        messages.info(request, "Vous participez déjà à ce constat.")
        return redirect('constat_detail', code=constat.code)

    user = request.user

    if request.method == 'POST':
        partie_form = PartieForm(request.POST, prefix='partie')
        vehicule_form = VehiculeForm(request.POST, prefix='vehicule')
        photos_form = PhotosForm(request.POST, request.FILES)

        valides = [f.is_valid() for f in (partie_form, vehicule_form, photos_form)]

        if all(valides):
            try:
                with transaction.atomic():
                    # Relecture : un autre conducteur a pu rejoindre entre-temps
                    constat = Constat.objects.get(pk=constat.pk)
                    if constat.statut != Constat.Statut.ATTENTE_B:
                        raise IntegrityError("constat déjà complet")

                    partie = partie_form.save(commit=False)
                    partie.constat = constat
                    partie.conducteur = user
                    partie.role = Partie.Role.B
                    partie.save()

                    vehicule = vehicule_form.save(commit=False)
                    vehicule.partie = partie
                    vehicule.save()

                    for fichier in photos_form.cleaned_data['photos']:
                        Photo.objects.create(partie=partie, image=fichier)

                    constat.statut = Constat.Statut.EN_COURS
                    constat.save(update_fields=['statut', 'updated_at'])
            except IntegrityError:
                messages.error(request, "Ce constat vient d'être complété par un autre conducteur.")
                return redirect('home')

            cache.delete(cle)
            messages.success(request, "Vous avez rejoint le constat. Vérifiez les informations des deux parties.")
            return redirect('constat_detail', code=constat.code)
    else:
        partie_form = PartieForm(
            prefix='partie',
            initial={'nom': user.last_name, 'prenom': user.first_name, 'telephone': user.telephone},
        )
        vehicule_form = VehiculeForm(prefix='vehicule')
        photos_form = PhotosForm()

    return render(request, 'constats/rejoindre.html', {
        'constat': constat,
        'partie_form': partie_form,
        'vehicule_form': vehicule_form,
        'photos_form': photos_form,
    })


# ---------- Envoi (ou renvoi) du code à B par e-mail ----------
@login_required
@require_POST
def inviter_conducteur_b(request, code):
    """Envoie (ou renvoie) le code du constat par e-mail. Réservé au conducteur A."""
    constat = get_object_or_404(Constat, code=code.upper(), createur=request.user)

    if constat.statut != Constat.Statut.ATTENTE_B:
        messages.error(request, "L'invitation n'est possible que tant que le conducteur B n'a pas rejoint le constat.")
        return redirect('constat_detail', code=constat.code)

    if constat.nb_invitations >= MAX_INVITATIONS:
        messages.error(request, f"Limite de {MAX_INVITATIONS} envois atteinte. Transmettez le code manuellement.")
        return redirect('constat_detail', code=constat.code)

    form = InvitationForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Adresse e-mail invalide.")
        return redirect('constat_detail', code=constat.code)

    constat.email_b = form.cleaned_data['email_b']
    constat.save(update_fields=['email_b', 'updated_at'])

    if envoyer_invitation(constat, request):
        messages.success(request, f"Le code a été envoyé à {constat.email_b}.")
    else:
        messages.warning(request, "L'e-mail n'a pas pu être envoyé. Transmettez le code manuellement.")
    return redirect('constat_detail', code=constat.code)