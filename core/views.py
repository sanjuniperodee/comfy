import os
import re

import requests
from .models import *
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.core.files.base import ContentFile
from bs4 import BeautifulSoup
from requests import get
from django.db.models import Count
from django.db.models import Min
from django.db.models import Subquery





# stripe.api_key = settings.STRIPE_SECRET_KEY

def home(request):
    return render(request, 'index.html', {'categories': Category.objects.all()})

def shop(request, ctg, ctg2):
    if ctg2 != 'all':
        object_list = Item.objects.filter(category__title=ctg, subcategory__title=ctg2)
    else:
        object_list = Item.objects.filter(category__title=ctg)
    paginator = Paginator(object_list, 18)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    pages = int(len(object_list)/18)
    if len(object_list) % 18 > 0:
        pages+=1
    category = Category.objects.filter(title=ctg)[0]
    context = {
        'categories': Category.objects.all(),
        'brands': Item.objects.filter(category__title=ctg).values('brand__title').distinct(),
        'pages': range(1,pages+1),
        'category': category,
        'items': page_obj,
        'user': request.user,
    }
    return render(request, 'shop.html', context)

def detail(request, slug):
    item = Item.objects.filter(slug=slug)[0]
    context = {
        'item': item,
        'description1': item.description1.split('\n'),
        'description2': item.description2.split('\n'),
        'categories': Category.objects.all()
    }
    return render(request, 'detail.html', context)


@login_required
def add_to_cart1(request):
    print(12312)
    slug = str(request.POST.get('slug'))
    print(slug)
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, payment=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
        else:
            order.items.add(order_item)
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
    return JsonResponse({'data': '123'})

@login_required
def cart(request):
    try:
        order = Order.objects.filter(user=request.user, payment=False)[0]
    except:
        order = Order.objects.create(user=request.user, payment=False)
    print(request.user)
    context = {
        'order': order,
        'categories': Category.objects.all()
    }
    return render(request, 'cart.html', context)

@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        payment=False,
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            return redirect("core:cart")
        else:
            return redirect("core:detail", slug=slug)
    else:
        return redirect("core:detail", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        payment=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            return redirect("core:cart")
        else:
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)

@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False

    )
    order_qs = Order.objects.filter(user=request.user, payment=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            return redirect("core:cart")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:cart")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect("core:order-summary")


@login_required
def profile(request):
    if request.method == "POST":
        cnt = 0
        if len(User.objects.filter(username=request.POST['username'])) > 0 and request.POST[
            'username'] != request.user.username:
            # messages.info(request, 'User already exists')
            cnt = 1
        if len(request.POST['password1']) > 0:
            if len(request.POST['password1']) < 8:
                # messages.info(request, 'Password must contain at least 8 symbols')
                cnt = 1
            if len(request.POST['password1']) and len(request.POST['password2']) and request.POST['password1'] != \
                    request.POST['password2']:
                # messages.info(request, 'Password not matching')
                cnt = 1
            if len(request.POST['password1']) < 8 and request.POST['password1'] == request.POST['password2']:
                pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).+$'
                if not re.match(pattern, password1):
                    # messages.info(request, "Password must contain at least 1 uppercase, 1 lowercase and one number")
                    cnt = 1
        if cnt == 1:
            return redirect('core:profile')
        else:
            if len(request.POST['password1']) > 0 and len(request.POST['password2']) > 0:
                request.user.password1 = request.POST['password1']
                request.user.password2 = request.POST['password2']

            request.user.username = request.POST['username']
            request.user.email = request.POST['email']
            request.user.first_name = request.POST['first_name']
            request.user.last_name = request.POST['last_name']
            request.user.save()
            return redirect('core:profile')
    print(request.user.username)
    return render(request, 'profile.html', {'user': request.user,'categories': Category.objects.all()})


def about_us(request):
    return render(request, 'about_us.html', {'categories': Category.objects.all()})

def sales(request):
    object_list = Item.objects.filter(sales=True)
    paginator = Paginator(object_list, 18)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    pages = int(len(object_list) / 18)
    if len(object_list) % 18 > 0:
        pages += 1
    context = {
        'categories': Category.objects.all(),
        'brands': object_list.values('brand__title').distinct(),
        'pages': range(1, pages + 1),
        'category': 'Акции',
        'items': page_obj,
        'user': request.user,
    }
    return render(request, 'shop.html', context)

def delete_duplicates(request):
    duplicate_names = Item.objects.values_list('articul', flat=True).distinct()

    for email in duplicate_names:
        Item.objects.filter(pk__in=Item.objects.filter(articul=email).values_list('pk', flat=True)[1:]).delete()

# def change_prices(request):
#     for item in Item.objects.all():
#         item.price = item.price/6.5 * 5.5
#         item.save()


def create(request):
    href = 'https://newport-shop.ru'
    for i in range(1, 11):
        url = href + "/catalog/podvesnye_svetilniki/?PAGEN_1=" + str(i)
        print(url)
        soup = BeautifulSoup(get(url).text, 'html.parser')
        products = soup.find_all('a', class_='name')
        print(len(products))
        for product in products:
            length = height = width = 0
            print(href+product['href'])
            page = BeautifulSoup(get(href+product['href']).text, 'html.parser')
            title = page.find('h1', class_='main-title').text.strip()
            item = Item.objects.filter(title=title)[0]
            item.subcategory = SubCategory.objects.filter(title='Подвесные люстры')[0]
            item.save()
            # if len(Item.objects.filter(title=title)) > 0:
            #     continue
            # try:
            #     price = int(page.find('div', class_='price').find('span').text.strip().replace(' руб.', '').replace(' ', ''))
            # except:
            #     price = 0
            # options = page.find_all('div', class_='characteristics')[1].find_all('tr')
            # teh = outlook = ''
            # for option in options:
            #     spans = option.find_all('td')
            #     key = spans[0].text.strip()
            #     value = spans[1].text.strip()
            #     print(key + ": " + value)
            #     if key == 'Артикул':
            #         articul = value
            #     if key == 'Ширина,см':
            #         width = value.replace(',', '.')
            #     if key == 'Длина,см':
            #         length = value.replace(',', '.')
            #     if key == 'Высота изделия, см':
            #         height = value.replace(',', '.')
            #     if key == 'Цоколь' or key == 'Количество источников света' or key == 'Мощность, W' or key == 'Общая мощность, W' or key == 'Степень защиты, IP' or key == 'Напряжение, V':
            #         teh += key + ": " + value + '\n'
            #     if key == 'Материал основания' or key == 'Цвет основания' or key == 'Стиль' or key == 'Форма' or key == 'Место установки':
            #         outlook += key + ": " + value + '\n'
            # item = Item(title=title,
            #             category=Category.objects.get_or_create(title='Люстры')[0],
            #             subcategory=SubCategory.objects.get_or_create(title='Потолочные люстры')[0],
            #             articul=articul,
            #             price=price * 5.5,
            #             slug=articul.replace(" ", "_").replace('/', '_').replace('+', '').replace('-',''),
            #             description1=teh,
            #             description2=outlook,
            #             brand=Brand.objects.get_or_create(title='Newport')[0],
            #             height=height,
            #             length=length,
            #             width=width,
            # )
            # image = href + page.find('div', class_="main-img").find('img')['src']
            # print(image)
            # response = requests.get(image)
            # response.raise_for_status()
            # item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
            # item.save()
            # print(link)
            # teh = ""
            # vnesh = ""
            # height = width = length = diameter = 0
            # fields = page.find_all('div', class_='characteristic-list__item')
            # for field in fields:
            #     key = field.find_all('div')[0].text.strip()
            #     value = re.sub(r'\s+', ' ', field.find_all('div')[1].text.strip())
            #     if key == 'Артикул':
            #         articul = value
            #     if key == 'Диаметр':
            #         diameter = value.split(' ')[0]
            #     if key == 'Источник света' or key == 'Количество ламп' or key == 'Защита IP' or key == 'Диммируемые' or key == 'Напряжение' or key == 'Мощность':
            #         teh += key + ': ' + value + '\n'
            #     if key == 'Цвет арматуры' or key == 'Материал арматуры':
            #         vnesh += key + ': ' + value + '\n'
            #     if key == 'Высота':
            #         height = value.split(' ')[0]
            #     if key == 'Ширина':
            #         width = value.split(' ')[0]
            #     if key == 'Длина':
            #         length = value.split(' ')[0]
            # print(height)
            # price = page.find('span', class_='price').text.replace(' ', '').replace('₽', '')
            # print(price)
            # print(teh)
            # print(vnesh)
            # images = page.find_all('div', class_='product-card__thumbs-item')
            # image_urls = []
            # for image in images:
            #     image_urls.append(href+image.find('img')['src'])
            # print(str(image_urls))
            # item = Item(title=title,
            #             category=Category.objects.get_or_create(title='Люстры')[0],
            #             subcategory=SubCategory.objects.get_or_create(title='Потолочные люстры')[0],
            #             articul=articul,
            #             price=int(price) * 6.5,
            #             slug=articul.replace(" ", "_"),
            #             description1=teh,
            #             description2=vnesh,
            #             brand=Brand.objects.get_or_create(title='Maytoni')[0],
            #             height=height,
            #             length=length,
            #             width=width,
            #             diameter=diameter
            # )
            # images = page.find_all('div', class_='product-card__thumbs-item')
            # image_urls = []
            # for image in images:
            #     print()
            #     image_urls.append(href+image.find('img')['src'].replace('40_40_0/', '').replace('resize_cache/', ''))
            # print(image_urls[0])
            # print(href+images[0].find('img')['src'])
            # response = requests.get(image_urls[0])
            # response.raise_for_status()
            # item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
            # item.save()
            # i = 0
            # for imag in ItemImage.objects.filter(post=item):
            #     imag.delete()
            # for imag in image_urls:
            #     i += 1
            #     if i == 1:
            #         continue
            #     try:
            #         img = ItemImage(post=item)
            #         response = requests.get(imag)
            #         response.raise_for_status()
            #         img.images.save(f"{title}.jpg", ContentFile(response.content), save=True)
            #         img.save()
            #         print(i)
            #     except:
            #         continue

# def create_loftit(request):
#     href = 'https://loftit.ru/'
#     for i in range(1, 2):
#         url = href + "catalog/lyustry/?sp=" + str(i)
#         soup = BeautifulSoup(get(url).text, 'html.parser')
#         responses = soup.find_all('div', class_='catalog__item')
#         print(len(responses))
#         for item in responses:
#             try:
#                 link = item.find_all('a')[1].get('href')
#                 page = BeautifulSoup(get(href + link).text, 'html.parser')
#                 title = item.find('div', class_='catalog-card__title').text.strip()
#                 print(title)
                # if len(Item.objects.filter(title=title)) > 0:
                #     continue
                # price = int(page.find('div', class_='items_price').text.replace(' ', '').replace('\xa0', '').replace('\n',
                #                                                                                                      '').replace(
                #     '\t', '').replace('руб.', ''))
                # descriptions = page.find_all('div', class_='col-md-6 hars')
                # teh = ""
                # outlook = ""
                # diametre = 0
                # height = 0
                # max_height = 0
                # min_height = 0
                # for i in descriptions:
                #     if i.text.split('\n')[1].startswith('Тип цоколя:'):
                #         teh += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                #     elif i.text.split('\n')[1].startswith('Лампочки в комплекте:'):
                #         teh+=i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                #     elif i.text.split('\n')[1].startswith('Напряжение питания, В:'):
                #         teh += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                #     elif i.text.split('\n')[1].startswith('Степень защиты, IP:'):
                #         teh += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                #
                #     if i.text.split('\n')[1].startswith('Форма светильника:'):
                #         outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                #     elif i.text.split('\n')[1].startswith('Форма плафона:'):
                #         outlook+=i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                #     elif i.text.split('\n')[1].startswith('Стиль светильника:'):
                #         outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                #     elif i.text.split('\n')[1].startswith('Интерьер:'):
                #         outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                #     elif i.text.split('\n')[1].startswith('Материал основания:'):
                #         outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                #     if i.text.split('\n')[1].startswith('Диаметр, мм:'):
                #         diametre = i.text.split('\n')[2]
                #     if i.text.split('\n')[1].startswith('Высота, мм:'):
                #         height = i.text.split('\n')[2]
                #     if i.text.split('\n')[1].startswith('Высота минимальная, мм:'):
                #         min_height = i.text.split('\n')[2]
                #     if i.text.split('\n')[1].startswith('Высота максимальная, мм:'):
                #         max_height = i.text.split('\n')[2]
                # print(teh)
                # print('height: ' + str(height))
                # print('diameter: ' + str(diametre))
                # image_urls = []
                # images = page.find_all('img', class_='img-fluid')
                # for image in images:
                #     image_urls.append(href+image['src'])
                # print('Title: ' + title)
                # temp = descriptions[1].text.split('\n')[2].split('  / ')
                # category = temp[0]
                # subcategory = temp[1]
                # print("Категория: " + category)
                # print("Подкатегория: " + subcategory)
                # temp = descriptions[2].text.split('\n')[2]
                # articul = temp.replace("/", "_")
                # print("Артикул: " + articul)
                # temp = int(descriptions[4].text.split('\n')[2])
                # print("min height: " + str(temp))
                # temp = int(descriptions[5].text.split('\n')[2])
                # print("max height: " + str(temp))
                # item = Item(title=title,
                #             category=Category.objects.get_or_create(title=category)[0],
                #             subcategory=SubCategory.objects.get_or_create(title=subcategory)[0],
                #             articul=articul,
                #             price=int(price) * 6.5,
                #             slug=articul.replace(" ", "_"),
                #             description1=teh,
                #             description2=outlook,
                #             brand=Brand.objects.get_or_create(title='Loft it')[0],
                #             diameter=diametre,
                #             height=height,
                #             min_height=min_height,
                #             max_height=max_height,
                # )
                # # for image in image_urls:
                # print(image_urls[0])
                # response = requests.get(image_urls[0])
                # response.raise_for_status()
                # item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
                # item.save()
                # i = 0
                # for imag in image_urls:
                #     i += 1
                #     if i == 1:
                #         continue
                #     try:
                #         img = ItemImage(post=item)
                #         response = requests.get(imag)
                #         response.raise_for_status()
                #         img.images.save(f"{title}.jpg", ContentFile(response.content), save=True)
                #         img.save()
                #         print(i)
                #     except:
                #         continue
    #         except:
    #             print("No Link")
    #     break
    # return JsonResponse()


# duplicates = Item.objects.values('articul').annotate(count=Count('id')).filter(count__gt=1)
#
#     # Step 2: Query the Duplicate Records and Delete Duplicates
#     for duplicate in duplicates:
#         articul_value = duplicate['articul']
#         # Query the duplicate records and order by 'id' (or any unique field)
#         duplicate_records = Item.objects.filter(articul=articul_value).order_by('id')
#
#         # Keep the first record (with the smallest 'id') and delete the rest
#         for index, record in enumerate(duplicate_records):
#             if index > 0:
#                 record.delete()