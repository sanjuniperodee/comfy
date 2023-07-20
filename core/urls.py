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
]