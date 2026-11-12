from django import forms
from django.utils import timezone

from .models import Constat, Partie, Vehicule

FORMAT_DATETIME = '%Y-%m-%dT%H:%M'
TAILLE_MAX_PHOTO = 5 * 1024 * 1024  # 5 Mo
MAX_PHOTOS = 6


# ---------- Champ « plusieurs images » ----------
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """Un seul champ qui accepte plusieurs images."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={'accept': 'image/*'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        clean_un = super().clean
        if isinstance(data, (list, tuple)):
            resultat = [clean_un(d, initial) for d in data]
        else:
            resultat = [clean_un(data, initial)]
        return [f for f in resultat if f]


class PhotosForm(forms.Form):
    photos = MultipleImageField(
        label='Photos des dommages',
        required=False,
        help_text=f"Vous pouvez choisir plusieurs photos ({MAX_PHOTOS} au plus, 5 Mo maximum chacune).",
    )

    def clean_photos(self):
        fichiers = self.cleaned_data['photos']
        if len(fichiers) > MAX_PHOTOS:
            raise forms.ValidationError(f"Maximum {MAX_PHOTOS} photos.")
        for f in fichiers:
            if f.size > TAILLE_MAX_PHOTO:
                raise forms.ValidationError(f"« {f.name} » dépasse 5 Mo.")
        return fichiers


# ---------- Formulaires du constat ----------
class ConstatForm(forms.ModelForm):
    date_accident = forms.DateTimeField(
        label="Date et heure de l'accident",
        input_formats=[FORMAT_DATETIME],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format=FORMAT_DATETIME),
    )

    class Meta:
        model = Constat
        fields = ('date_accident', 'lieu', 'email_b')
        labels = {
            'lieu': "Lieu de l'accident",
            'email_b': "E-mail du conducteur B (facultatif)",
        }
        widgets = {
            'lieu': forms.TextInput(attrs={'placeholder': 'Rue, ville, repère proche'}),
            'email_b': forms.EmailInput(attrs={'placeholder': 'conducteur.b@exemple.com', 'autocomplete': 'off'}),
        }
        help_texts = {
            'email_b': "Le code du constat lui sera envoyé automatiquement par e-mail.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Empêche de choisir une date future dans le sélecteur
        self.fields['date_accident'].widget.attrs['max'] = timezone.localtime().strftime(FORMAT_DATETIME)

    def clean_date_accident(self):
        date = self.cleaned_data['date_accident']
        if date > timezone.now():
            raise forms.ValidationError("La date de l'accident ne peut pas être dans le futur.")
        return date

    def clean_email_b(self):
        return self.cleaned_data['email_b'].strip().lower()


class PartieForm(forms.ModelForm):
    class Meta:
        model = Partie
        fields = ('nom', 'prenom', 'adresse', 'telephone', 'numero_permis', 'circonstances')
        labels = {
            'nom': 'Nom',
            'prenom': 'Prénom',
            'adresse': 'Adresse',
            'telephone': 'Téléphone',
            'numero_permis': 'Numéro de permis',
            'circonstances': "Circonstances de l'accident",
        }
        widgets = {
            'circonstances': forms.Textarea(attrs={'rows': 4}),
            'telephone': forms.TextInput(attrs={'inputmode': 'tel', 'autocomplete': 'tel'}),
        }
        help_texts = {
            'circonstances': "Décrivez ce qui s'est passé de votre point de vue.",
        }


class VehiculeForm(forms.ModelForm):
    class Meta:
        model = Vehicule
        fields = ('marque', 'modele', 'immatriculation', 'compagnie_assurance', 'numero_police', 'degats')
        labels = {
            'marque': 'Marque',
            'modele': 'Modèle',
            'immatriculation': "Numéro d'immatriculation",
            'compagnie_assurance': "Compagnie d'assurance",
            'numero_police': 'Numéro de police',
            'degats': 'Dégâts apparents',
        }
        widgets = {
            'degats': forms.Textarea(attrs={'rows': 3}),
            'immatriculation': forms.TextInput(attrs={'placeholder': 'ex. 123 TUN 4567'}),
        }


class InvitationForm(forms.Form):
    email_b = forms.EmailField(label="E-mail du conducteur B")

    def clean_email_b(self):
        return self.cleaned_data['email_b'].strip().lower()