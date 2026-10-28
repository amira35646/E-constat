import secrets

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Alphabet sans caractères ambigus (pas de I, O, 0, 1) : le code se dicte facilement
ALPHABET_CODE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generer_code(longueur=8):
    return ''.join(secrets.choice(ALPHABET_CODE) for _ in range(longueur))


def chemin_photo(instance, filename):
    return f"constats/{instance.partie.constat.code}/photos/{filename}"


def chemin_gradcam(instance, filename):
    return f"constats/{instance.photo.partie.constat.code}/gradcam/{filename}"


class Constat(models.Model):
    class Statut(models.TextChoices):
        BROUILLON = 'brouillon', 'Brouillon'
        ATTENTE_B = 'attente_b', 'En attente du conducteur B'
        EN_COURS = 'en_cours', 'En cours de validation'
        FINALISE = 'finalise', 'Finalisé'

    code = models.CharField(max_length=12, unique=True, editable=False)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.BROUILLON)
    date_accident = models.DateTimeField("date et heure de l'accident")
    lieu = models.CharField(max_length=255)
    createur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='constats_crees'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'constat'

    def __str__(self):
        return f"Constat {self.code} ({self.get_statut_display()})"

    def save(self, *args, **kwargs):
        if not self.code:
            code = generer_code()
            while Constat.objects.filter(code=code).exists():
                code = generer_code()
            self.code = code
        super().save(*args, **kwargs)

    @property
    def partie_a(self):
        return self.parties.filter(role=Partie.Role.A).first()

    @property
    def partie_b(self):
        return self.parties.filter(role=Partie.Role.B).first()

    @property
    def est_complet(self):
        """Vrai quand les deux conducteurs ont validé leur partie."""
        parties = self.parties.all()
        return parties.count() == 2 and all(p.valide for p in parties)


class Partie(models.Model):
    class Role(models.TextChoices):
        A = 'A', 'Conducteur A'
        B = 'B', 'Conducteur B'

    constat = models.ForeignKey(Constat, on_delete=models.CASCADE, related_name='parties')
    conducteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='parties'
    )
    role = models.CharField(max_length=1, choices=Role.choices)

    # Informations personnelles saisies pour CE constat
    nom = models.CharField(max_length=100)
    prenom = models.CharField("prénom", max_length=100)
    adresse = models.CharField(max_length=255)
    telephone = models.CharField("téléphone", max_length=20, blank=True)
    numero_permis = models.CharField("numéro de permis", max_length=50)

    circonstances = models.TextField(blank=True)

    valide = models.BooleanField(default=False)
    date_validation = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['constat', 'role'], name='un_seul_role_par_constat'),
            models.UniqueConstraint(fields=['constat', 'conducteur'], name='un_conducteur_par_constat'),
        ]
        ordering = ['constat', 'role']

    def __str__(self):
        return f"{self.get_role_display()} - {self.prenom} {self.nom} ({self.constat.code})"


class Vehicule(models.Model):
    partie = models.OneToOneField(Partie, on_delete=models.CASCADE, related_name='vehicule')
    marque = models.CharField(max_length=60)
    modele = models.CharField("modèle", max_length=60)
    immatriculation = models.CharField(max_length=20)
    compagnie_assurance = models.CharField("compagnie d'assurance", max_length=100)
    numero_police = models.CharField("numéro de police", max_length=50)
    degats = models.TextField("dégâts apparents", blank=True)

    class Meta:
        verbose_name = 'véhicule'

    def __str__(self):
        return f"{self.marque} {self.modele} ({self.immatriculation})"


class Photo(models.Model):
    partie = models.ForeignKey(Partie, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to=chemin_photo)
    description = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Photo {self.pk} - {self.partie}"


class AnalyseIA(models.Model):
    class Verdict(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        AUTHENTIQUE = 'authentique', 'Authentique'
        SUSPECTE = 'suspecte', 'Suspecte'
        ERREUR = 'erreur', "Erreur d'analyse"

    photo = models.OneToOneField(Photo, on_delete=models.CASCADE, related_name='analyse')
    verdict = models.CharField(max_length=20, choices=Verdict.choices, default=Verdict.EN_ATTENTE)
    score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Score de confiance entre 0 et 1.",
    )
    gradcam = models.ImageField(upload_to=chemin_gradcam, null=True, blank=True)
    analyse_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "analyse IA"
        verbose_name_plural = "analyses IA"

    def __str__(self):
        return f"Analyse photo {self.photo_id} : {self.get_verdict_display()}"

    @property
    def est_suspecte(self):
        return self.verdict == self.Verdict.SUSPECTE
    