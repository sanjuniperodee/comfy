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
    item = Item.objects.filter(slug=slug)[0]
    context = {
        'item': item,
        'description1': item.description1.split('\n')
    }
    return render(request, 'detail.html', context)