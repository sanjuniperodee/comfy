import requests
from .models import *
from django.conf import settings
from django.shortcuts import render, get_object_or_404

# stripe.api_key = settings.STRIPE_SECRET_KEY

def home(request):
    return render(request, 'index.html')

def shop(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, 'shop.html', context)

def detail(request, slug):
    context = {
        'item': Item.objects.filter(slug=slug)[0]
    }
    return render(request, 'detail.html', context)