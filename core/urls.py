from django.contrib.staticfiles.views import serve
from django.urls import path, re_path
from .views import *

app_name = 'core'

urlpatterns = [
    path('', home, name='home'),
    path('shop/<str:ctg>/<str:ctg2>', shop, name='shop'),
    path('cart', cart, name='cart'),
    path('detail/<slug>', detail, name='detail'),
    path('add-to-cart1', add_to_cart1, name='add-to-cart1'),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart, name='remove-single-item-from-cart'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('profile', profile, name='profile'),
    path('about_us', about_us, name='about_us'),
    path('delete_duplicates', delete_duplicates, name='delete_duplicates'),
    path('create', create, name='create'),
    path('sales', sales, name='sales'),
    path('price', change_prices, name='price')
]