import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_INVITATIONS = 5  # nombre maximal d'envois par constat (évite le spam)


def envoyer_invitation(constat, request):
    """Envoie au conducteur B le code du constat. Retourne True si l'e-mail est parti."""
    if not constat.email_b or constat.nb_invitations >= MAX_INVITATIONS:
        return False

    try:
        createur = constat.createur
        nom_a = createur.get_full_name() or createur.username
        lien = request.build_absolute_uri(reverse('constat_rejoindre')) + f"?code={constat.code}"
        date = timezone.localtime(constat.date_accident).strftime('%d/%m/%Y à %H:%M')

        sujet = f"{nom_a} vous invite à compléter un constat amiable (e-Constat)"
        message = (
            f"Bonjour,\n\n"
            f"{nom_a} a créé un constat amiable numérique à la suite de l'accident du {date} "
            f"et vous invite à le compléter.\n\n"
            f"Code du constat : {constat.code}\n\n"
            f"Pour rejoindre le constat :\n"
            f"1. Connectez-vous à e-Constat (ou créez un compte).\n"
            f"2. Saisissez le code ci-dessus dans « Je rejoins un constat », "
            f"ou ouvrez directement ce lien :\n{lien}\n\n"
        )
        if createur.email:
            message += f"Vous pouvez répondre à ce message pour contacter {nom_a}.\n\n"
        message += (
            "Si vous n'êtes pas concerné par cet accident, ignorez simplement ce message.\n\n"
            "L'équipe e-Constat"
        )

        courriel = EmailMessage(
            sujet,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [constat.email_b],
            reply_to=[createur.email] if createur.email else None,
        )
        courriel.send(fail_silently=False)
    except Exception:
        # Toute erreur (route manquante, serveur d'envoi indisponible...) est écrite
        # dans le terminal, sans faire planter la page
        logger.exception("Échec de l'envoi de l'invitation du constat %s", constat.code)
        return False

    constat.nb_invitations += 1
    constat.derniere_invitation = timezone.now()
    constat.save(update_fields=['nb_invitations', 'derniere_invitation', 'updated_at'])
    return True