import requests
from django.conf import settings
from django.shortcuts import render, get_object_or_404

# stripe.api_key = settings.STRIPE_SECRET_KEY

def home(request):
    return render(request, 'index.html')
