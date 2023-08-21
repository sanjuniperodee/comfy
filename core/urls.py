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
    path('create_loftit', create_loftit, name='create_loftit'),
    path('create_greenline', create_greenline, name='create_greenline'),
    path('sales', sales, name='sales'),
    path('mir', mir, name='mir'),
    path('decor', decor, name='decor'),
    path('alpin', alpin, name='alpin'),
    path('greenline', greenline, name='greenline'),
    path('create_mayto', create_mayto, name='create_mayto'),
    path('copy', copy, name='copy'),
    path('st_luce', st_luce, name='st_luce'),
    path('alsa_floor', alsa_floor, name='alsa_floor'),
    path('pergo', pergo, name='pergo')
]