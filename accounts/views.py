from django.contrib.auth import login
from django.shortcuts import render, redirect
from .forms import InscriptionForm

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