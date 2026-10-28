from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class InscriptionForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Adresse e-mail")

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'telephone')
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'username': "Nom d'utilisateur",
            'telephone': 'Téléphone (facultatif)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = self.fields

        f['first_name'].required = True
        f['last_name'].required = True

        f['first_name'].widget.attrs.update({'autocomplete': 'given-name', 'autofocus': True})
        f['last_name'].widget.attrs.update({'autocomplete': 'family-name'})
        f['username'].widget.attrs.update({'placeholder': 'ex. prenom.nom', 'autocomplete': 'username'})
        f['email'].widget.attrs.update({'placeholder': 'nom@exemple.com', 'autocomplete': 'email'})
        f['telephone'].widget.attrs.update({'placeholder': '20 123 456', 'autocomplete': 'tel', 'inputmode': 'tel'})
        f['password1'].widget.attrs.update({'autocomplete': 'new-password'})
        f['password2'].widget.attrs.update({'autocomplete': 'new-password'})

        f['password1'].label = 'Mot de passe'
        f['password2'].label = 'Confirmer le mot de passe'

        # Aides courtes à la place des 4 longues puces (les règles restent appliquées)
        f['username'].help_text = "Lettres, chiffres et @ . + - _ uniquement."
        f['password1'].help_text = "8 caractères minimum, pas uniquement des chiffres."
        f['password2'].help_text = ""

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CONDUCTEUR  # tout nouvel inscrit est conducteur
        if commit:
            user.save()
        return user