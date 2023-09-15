import os
import re

import requests
from .models import *
from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Q

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
    articul = request.GET.get('articul')
    if articul:
        return redirect(f'/shop/all/all?articul={articul}')
    bests = Item.objects.filter(collection='EXTRA')
    return render(request, 'index.html', {'categories': Category.objects.all(), 'bests': bests})

# def parket(request):
#     return render(request, 'parket.html', {'subcategories': SubCategory.objects.filter(is_parket=True)})

def shop(request, ctg, ctg2):
    categories = set(Category.objects.all())
    subcategory = ctg2
    selected_brands = request.GET.getlist('brands')
    articul = request.GET.get('articul')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if ctg2 != 'all' and ctg !='all':
        category = Category.objects.filter(title=ctg)[0]
        object_list = Item.objects.filter(category__title=ctg, subcategory__title=ctg2)
        subcategory = SubCategory.objects.filter(title=ctg2).first()
    elif ctg2 == 'all' and ctg !='all':
        category = Category.objects.filter(title=ctg)[0]
        object_list = Item.objects.filter(category__title=ctg)
        subcategory = None
    else:
        category = 'all'
        object_list = Item.objects.all()
    if articul:
        object_list = object_list.filter(Q(articul__icontains=articul) | Q(title__icontains=articul))
        if ctg == 'all':
            categories = set()
            for item in object_list:
                categories.add(item.category)
    if selected_brands:
        object_list = object_list.filter(brand__title__in=selected_brands)
    if min_price and max_price:
        object_list = object_list.filter(price__gte=min_price, price__lte=max_price)
    paginator = Paginator(object_list, 18)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    pagination_links = []
    for page in page_obj.paginator.page_range:
        query_parameters = request.GET.copy()
        query_parameters['page'] = page
        pagination_links.append({'page_number': page, 'query_parameters': query_parameters.urlencode()})
    pages = int(len(object_list)/18)
    if len(object_list) % 18 > 0:
        pages+=1
    print(subcategory)
    print(123123123)
    context = {
        'min_price': min_price,
        'max_price': max_price,
        'subcategory' : subcategory,
        'categories': categories,
        'brandy': selected_brands,
        'brands': Item.objects.filter(category__title=ctg).values('brand__title').distinct(),
        'pages': range(1,pages+1),
        'category': category,
        'items': page_obj,
        'user': request.user,
        'pagination_links': pagination_links,
    }
    return render(request, 'shop.html', context)

def detail(request, slug):
    item = Item.objects.filter(slug=slug)[0]
    try:
        description1 = item.description1.split('\n')
        description2 = item.description2.split('\n')
    except:
        description1 = ''
        description2 = ''
    context = {
        'item': item,
        'description1': description1,
        'description2': description2,
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

def greenline(request):
    href = 'https://parket-greenline.ru'
    soup = BeautifulSoup(get(href+'/products/inzhenernaya-doska/smart/').text, 'html.parser')
    items = soup.find_all('div', class_='item_4')
    for item in items:
        page = BeautifulSoup(get(href+item.find('a')['href']).text, 'html.parser')
        print(href+'/products/inzhenernaya-doska/smart'+item.find('a')['href'])
        title = page.find('h1', class_='bx-title').text.strip()
        print(title)
        table = page.find('dl', class_='product-item-detail-properties')
        for row in table:
            value = row.find('dt').text
            key = row.find('dd').text
            if key == 'Коллекция':
                collection = key
            # if key == 'Декор':

        break

def alpin(request):
    href = 'https://alpinefloor.su'
    soup = BeautifulSoup(get(href + '/catalog/spc-laminat/kollektsii-af-spc/grand-sequoia/').text, 'html.parser')
    items = soup.find_all('a', class_='link-preset product-tile__detail')
    for item in items:
        page = BeautifulSoup(get(href+item['href']).text, 'html.parser')
        title = page.find('h1', class_='h1 item-detail__header').text
        print(title)
        price =page.find('div', class_='item-detail-price__value').text.strip().split(' ь')[0].replace(' ', '')
        print(price)
        table = page.find('table', class_='table chars-table').find_all('tr')
        for row in table:
            print(row.text.strip())
            key = row.text.strip().split('\n')[0]
            value = row.text.strip().split('\n')[1]
            description=''
            print(key + ": " + value)
            if key == 'Длина, мм':
                length = value
            elif key == 'Ширина, мм':
                width = value
            elif key == 'Толщина, мм':
                thickness = value
            elif key == 'Микрофаска':
                faska = value
            else :
                description+= key + ": " + value + '\n'
        articul = page.find('span', class_='item-detail-class__name').text
        print(articul)
        item = Item(
            title=title,
            price = price,
            length = length,
            width = width,
            thickness = thickness,
            faska = faska,
            description1= description,
            category = Category.objects.get_or_create(title='SPC')[0],
            subcategory = SubCategory.objects.get_or_create(title='GRAND SEQUOIA')[0],
            brand = Brand.objects.get_or_create(title='Apline Floor')[0],
            articul = articul,
            slug = articul.replace(' ', '_')
        )
        image = page.find('a', class_='link-preset item-detail-slide-img-wrap icon icon_search')['href']
        print(href + image)
        response = requests.get(href + image)
        response.raise_for_status()
        item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
        item.save()
        images = page.find_all('img', class_="imgResponsive imgMini")
        print(len(images))
        for imag in images:
            try:
                img = ItemImage(post=item)
                response = requests.get(href + imag['src'])
                response.raise_for_status()
                img.images.save(f"{title}.jpg", ContentFile(response.content), save=True)
                img.save()
            except:
                continue


def decor(request):
    href = 'https://decorkz.kz'
    for i in range(1,6):
        soup = BeautifulSoup(get(href + '/products?alias=Panels+I&page=' + str(i)).text, 'html.parser')
        items = soup.find_all('a', class_="h3 pt-1 stretched-link")
        for item in items:
            print(href+item['href'])
            page = BeautifulSoup(get(href + item['href']).text, 'html.parser')
            title = page.find('h1', class_='h2').text.strip()
            print(title)
            parameters = page.find('div', class_='infoBlock').find_all('li')
            price = length = height = width = '0'
            for row in parameters:
                print(row.text)
                key = row.find_all('span')[0].text.strip()
                value = row.find_all('span')[1].text.strip()
                print(key + ": " + value)
                if key == 'Ширина':
                    width = value
                if key == 'Высота':
                    height = value
                if key == 'Материал':
                    wood = value
                if key == 'Длина':
                    length = value
                if key == 'Производитель':
                    brand = value
                if key == 'Вложение в коробке':
                    description = key + ": " + value + '\n'
            price = page.find('span', class_='infoNumb price pl-3').text.strip().replace('тг', '')
            print(int(price))
            item = Item(
                title=title,
                length = length.replace('мм', ''),
                brand = Brand.objects.get_or_create(title=brand)[0],
                description1 = description,
                price = price,
                width = int(width.replace('мм', '')),
                height = int(height.replace('мм', '')),
                # diameter = int(diameter.replace('мм', '')),
                wood_type = wood,
                category = Category.objects.get_or_create(title='Декор для стен')[0],
                subcategory = SubCategory.objects.get_or_create(title='Панели и решетки')[0],
                slug = title.replace(' ', '_'),
                articul= title
            )
            item.save()
            image = page.find('img', class_='imgProd imgResponsive')['src']
            print(href+image)
            response = requests.get(href+image)
            response.raise_for_status()
            item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
            item.save()
            images = page.find_all('img', class_="imgResponsive imgMini")
            print(len(images))
            for imag in images:
                try:
                    img = ItemImage(post=item)
                    response = requests.get(href+imag['src'])
                    response.raise_for_status()
                    img.images.save(f"{title}.jpg", ContentFile(response.content), save=True)
                    img.save()
                except:
                    continue


def mir(request):
    href = 'https://mirparketa.kz'
    soup = BeautifulSoup(get(href+'/product-category/laminat/?swoof=1&pa_firma-proizvoditel=kraft-us&really_curr_tax=25-product_cat').text, 'html.parser')
    items = soup.find_all('div', class_='product-wrapper')
    for item in items:
        url = item.find('a')['href']
        print(url)
        page = BeautifulSoup(get(url).text, 'html.parser')
        title = page.find('h1').text.strip()
        print(title)
        price = page.find('p', class_='price').find('bdi').text.strip()
        print(price)
        table = page.find('table').find_all('tr')
        thickness = length = width = wood = color = selection = decor = design = collection = description = ''
        for row in table:
            key = row.find('span').text.strip()
            value = row.find('td').text.strip().replace(' мм', '')
            print(key + ": " + value)
            if key == 'Толщина':
                thickness = value
            elif key =='Длина':
                length = value
            elif key == 'Ширина':
                width = value
            elif key == 'Тип дизайна':
                design = value
            else:
                description+=key + ": " + value + '\n'
        item = Item(
            title = title,
            price = price.replace(' ', '').replace(' ', '').replace('₸', ''),
            thickness = thickness,
            length = length,
            width = width,
            description1=description,
            category=Category.objects.get_or_create(title='Ламинат')[0],
            subcategory=SubCategory.objects.get_or_create(title=design)[0],
            brand=Brand.objects.get_or_create(title='Kraft')[0],
            articul=title.split('(')[1].replace(')',''),
            slug=title.split('(')[1].replace(')','').replace('/', '')
        )
        item.save()
        image = page.find('div', class_='product-image-wrap').find('img')['src']
        print(image)
        response = requests.get(image)
        response.raise_for_status()
        item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
        item.save()

def create_mayto(request):
    href = 'https://maytoni.ru'
    for i in range(1, 2):
        url = href + "/catalog/decorative/nastolnye-svetilniki/?SHOWALL=1#product_23"
        print(url)
        soup = BeautifulSoup(get(url).text, 'html.parser')
        products = soup.find_all('a', class_='catalog-card__link')
        print(len(products))
        for item in products:
            print(href+item['href'])
            page = BeautifulSoup(get(href + item['href']).text)
            title = page.find('h1', class_='page-header').text.strip()
            if len(Item.objects.filter(title=title)) > 0:
                continue
            teh = ""
            vnesh = ""
            height = width = length = diameter = 0
            fields = page.find_all('div', class_='characteristic-list__item')
            for field in fields:
                key = field.find_all('div')[0].text.strip()
                value = re.sub(r'\s+', ' ', field.find_all('div')[1].text.strip())
                if key == 'Артикул':
                    articul = value
                if key == 'Диаметр':
                    diameter = value.split(' ')[0]
                if key == 'Источник света' or key == 'Количество ламп' or key == 'Защита IP' or key == 'Диммируемые' or key == 'Напряжение' or key == 'Мощность':
                    teh += key + ': ' + value + '\n'
                if key == 'Цвет арматуры' or key == 'Материал арматуры':
                    vnesh += key + ': ' + value + '\n'
                if key == 'Высота':
                    height = value.split(' ')[0]
                if key == 'Ширина':
                    width = value.split(' ')[0]
                if key == 'Длина':
                    length = value.split(' ')[0]
                if key == 'Тип товара':
                    type = value.strip()
            print(height)
            price = page.find('span', class_='price').text.replace(' ', '').replace('₽', '')
            print(price)
            print(teh)
            print(vnesh)
            images = page.find_all('div', class_='product-card__thumbs-item')
            image_urls = []
            for image in images:
                image_urls.append(href+image.find('img')['src'])
            print(str(image_urls))
            item = Item(title=title + " " + articul,
                        category=Category.objects.get_or_create(title='Светильники')[0],
                        subcategory=SubCategory.objects.get_or_create(title=type)[0],
                        articul=articul,
                        price=int(price) * 5.5,
                        slug=articul.replace(" ", "_"),
                        description1=teh,
                        description2=vnesh,
                        brand=Brand.objects.get_or_create(title='Maytoni')[0],
                        height=height,
                        length=length,
                        width=width,
                        diameter=diameter
            )
            images = page.find_all('div', class_='product-card__thumbs-item')
            image_urls = []
            for image in images:
                print()
                image_urls.append(href+image.find('img')['src'].replace('40_40_0/', '').replace('resize_cache/', ''))
            try:
                print(image_urls[0])
            except:
                image_urls.append(href+page.find('div', class_='product-card__img-img').find('img')['src'])
            print(href+image_urls[0])
            response = requests.get(image_urls[0])
            response.raise_for_status()
            item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
            item.save()
            i = 0
            for imag in ItemImage.objects.filter(post=item):
                imag.delete()
            for imag in image_urls:
                i += 1
                if i == 1:
                    continue
                try:
                    img = ItemImage(post=item)
                    response = requests.get(imag)
                    response.raise_for_status()
                    img.images.save(f"{title}.jpg", ContentFile(response.content), save=True)
                    img.save()
                    print(i)
                except:
                    continue

def create_maytoni(requeset):
    href = 'https://maytoni.ru'
    for i in range(1,5):
        soup = BeautifulSoup(get(href + '/catalog/decorative/lyustry/?PAGEN_1=' + str(i)).text, 'html.parser')
        items = soup.find_all('a', class_='catalog-card__link')
        print(len(items))
        for item in items:
            link =item['href']
            page = BeautifulSoup(get(href + link).text, 'html.parser')
            print(link)
            title = page.find('h1', class_='page-header').text.strip()
            teh = ""
            vnesh = ""
            height = width = length = diameter = 0
            fields = page.find_all('div', class_='characteristic-list__item')
            for field in fields:
                key = field.find_all('div')[0].text.strip()
                value = re.sub(r'\s+', ' ', field.find_all('div')[1].text.strip())
                if key == 'Артикул':
                    articul = value
                if key == 'Диаметр':
                    diameter = value.split(' ')[0]
                if key == 'Источник света':
                    cokol = value
                if key == 'Количество ламп':
                    colvo = value
                if key == 'Источник света' or key == 'Количество ламп' or key == 'Защита IP' or key == 'Диммируемые' or key == 'Напряжение' or key == 'Мощность':
                    teh += key + ': ' + value + '\n'
                if key == 'Цвет арматуры' or key == 'Материал арматуры':
                    vnesh += key + ': ' + value + '\n'
                if key == 'Высота':
                    height = value.split(' ')[0]
                if key == 'Ширина':
                    width = value.split(' ')[0]
                if key == 'Длина':
                    length = value.split(' ')[0]
            print(height)
            price = page.find('span', class_='price').text.replace(' ', '').replace('₽', '')
            print(price)
            print(teh)
            print(vnesh)
            images = page.find_all('div', class_='product-card__thumbs-item')
            image_urls = []
            for image in images:
                image_urls.append(href+image.find('img')['src'])
            print(str(image_urls))
            item = Item(title=title + ' ' + cokol + 'X' + colvo.replace(' шт', ''),
                        category=Category.objects.get_or_create(title='Люстры')[0],
                        subcategory=SubCategory.objects.get_or_create(title='Люстры')[0],
                        articul=articul,
                        price=int(price) * 6.5,
                        slug=articul.replace(" ", "_"),
                        description1=teh,
                        description2=vnesh,
                        brand=Brand.objects.get_or_create(title='Maytoni')[0],
                        height=height,
                        length=length,
                        width=width,
                        diameter=diameter
            )
            images = page.find_all('div', class_='product-card__thumbs-item')
            image_urls = []
            for image in images:
                print()
                image_urls.append(href+image.find('img')['src'].replace('40_40_0/', '').replace('resize_cache/', ''))
            print(image_urls[0])
            print(href+images[0].find('img')['src'])
            response = requests.get(image_urls[0])
            response.raise_for_status()
            item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
            item.save()
            i = 0
            for imag in ItemImage.objects.filter(post=item):
                imag.delete()
            for imag in image_urls:
                i += 1
                if i == 1:
                    continue
                try:
                    img = ItemImage(post=item)
                    response = requests.get(imag)
                    response.raise_for_status()
                    img.images.save(f"{title}.jpg", ContentFile(response.content), save=True)
                    img.save()
                    print(i)
                except:
                    continue


def create(request):
    href = 'https://newport-shop.ru'
    for i in range(1, 23):
        url = href + "/catalog/lustry/?PAGEN_1=" + str(i)
        print(url)
        soup = BeautifulSoup(get(url).text, 'html.parser')
        products = soup.find_all('a', class_='name')
        print(len(products))
        for product in products:
            try:
                length = height = width = 0
                print(href+product['href'])
                page = BeautifulSoup(get(href+product['href']).text, 'html.parser')
                title = page.find('h1', class_='main-title').text.strip()
                item = Item.objects.filter(title=title)[0]
                item.subcategory = SubCategory.objects.get_or_create(title='Люстры')[0]
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
            except:
                continue

def create_loftit(request):
    href = 'https://loftit.ru/'
    for i in range(1, 9):

        url = href + "catalog/lyustry/?sp=" + str(i)
        soup = BeautifulSoup(get(url).text, 'html.parser')
        responses = soup.find_all('div', class_='items')
        print(len(responses))
        for item in responses:
            link = item.find_all('a')[1].get('href')
            page = BeautifulSoup(get(href + link).text, 'html.parser')
            title = page.find('h1').text.strip()
            print(title)
            if len(Item.objects.filter(title=title)) > 0:
                continue
            try:
                price = int(page.find('div', class_='items_price').text.replace(' ', '').replace('\xa0', '').replace('\n',
                                                                                                                     '').replace(
                    '\t', '').replace('руб.', ''))
                descriptions = page.find_all('div', class_='col-md-6 hars')
                teh = ""
                outlook = ""
                diametre = 0
                height = 0
                max_height = 0
                min_height = 0
                for i in descriptions:
                    if i.text.split('\n')[1].startswith('Тип цоколя:'):
                        teh += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                    elif i.text.split('\n')[1].startswith('Лампочки в комплекте:'):
                        teh+=i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                    elif i.text.split('\n')[1].startswith('Напряжение питания, В:'):
                        teh += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                    elif i.text.split('\n')[1].startswith('Степень защиты, IP:'):
                        teh += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'

                    if i.text.split('\n')[1].startswith('Форма светильника:'):
                        outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                    elif i.text.split('\n')[1].startswith('Форма плафона:'):
                        outlook+=i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                    elif i.text.split('\n')[1].startswith('Стиль светильника:'):
                        outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                    elif i.text.split('\n')[1].startswith('Интерьер:'):
                        outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                    elif i.text.split('\n')[1].startswith('Материал основания:'):
                        outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
                    if i.text.split('\n')[1].startswith('Диаметр, мм:'):
                        diametre = i.text.split('\n')[2]
                    if i.text.split('\n')[1].startswith('Высота, мм:'):
                        height = i.text.split('\n')[2]
                    if i.text.split('\n')[1].startswith('Высота минимальная, мм:'):
                        min_height = i.text.split('\n')[2]
                    if i.text.split('\n')[1].startswith('Высота максимальная, мм:'):
                        max_height = i.text.split('\n')[2]
                print(teh)
                print('height: ' + str(height))
                print('diameter: ' + str(diametre))
                image_urls = []
                images = page.find_all('img', class_='img-fluid')
                for image in images:
                    image_urls.append(href+image['src'])
                print('Title: ' + title)
                temp = descriptions[1].text.split('\n')[2].split('  / ')
                category = temp[0]
                subcategory = temp[1]
                print("Категория: " + category)
                print("Подкатегория: " + subcategory)
                temp = descriptions[2].text.split('\n')[2]
                articul = temp.replace("/", "_")
                print("Артикул: " + articul)
                temp = int(descriptions[4].text.split('\n')[2])
                print("min height: " + str(temp))
                temp = int(descriptions[5].text.split('\n')[2])
                print("max height: " + str(temp))
                item = Item(title=title,
                            category=Category.objects.get_or_create(title=category)[0],
                            subcategory=SubCategory.objects.get_or_create(title=subcategory)[0],
                            articul=articul,
                            price=int(price) * 6.5,
                            slug=articul.replace(" ", "_"),
                            description1=teh,
                            description2=outlook,
                            brand=Brand.objects.get_or_create(title='Loft it')[0],
                            diameter=diametre,
                            height=height,
                            min_height=min_height,
                            max_height=max_height,
                )
                # for image in image_urls:
                print(image_urls[0])
                response = requests.get(image_urls[0])
                response.raise_for_status()
                item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
                item.save()
                i = 0
                for imag in image_urls:
                    i += 1
                    if i == 1:
                        continue
                    try:
                        img = ItemImage(post=item)
                        response = requests.get(imag)
                        response.raise_for_status()
                        img.images.save(f"{title}.jpg", ContentFile(response.content), save=True)
                        img.save()
                        print(i)
                    except:
                        continue
            except:
                continue
    return JsonResponse()

def create_greenline(request):
    href = 'https://odeon-light.com'
    sec = '?utm_source=&utm_medium=captcha_byazrov&utm_campaign=captcha&utm_referrer='
    for i in range(1, 3):
        url = href + "/catalog/odeon_light/lyustra_potolochnaya/?PAGEN_1=" + str(i) + sec
        # url = 'https://odeon-light.com/catalog/odeon_light/lyustra_podvesnaya/?PAGEN_1=1'
        print(url)
        soup = BeautifulSoup(get(url).text, 'html.parser')
        items = soup.find_all('div', class_='catalog-items__element')
        print(len(items))
        for item in items:
            link = item.find('a').get('href')
            print(link)
            page = BeautifulSoup(get(href + link + sec).text, 'html.parser')
            title = page.find('div', class_='title-H1').text.strip()
            print(title)
            if len(Item.objects.filter(title=title)) > 0:
                continue
            price = item.find_all('b')[1].text.replace(' ', '').replace('руб.', '')
            print(price)
            print(int(price))
            tables = page.find_all('div', class_='detail-product__text')
            description = ''
            description2 = page.find('div', class_='diin').text.strip()
            print(description2)
            articul = diameter = height = width = '0'
            articul = ''
            for table in tables:
                flag = False
                for row in table.find_all('div'):
                    try:
                        value = row.text.strip().split('\n')[1].strip()
                        key = row.text.strip().split('\n')[0].strip()
                    except:
                        continue
                    print(key + ": " + value)
                    if key == 'Артикул':
                        if len(articul) > 0:
                            flag=True
                            break
                        articul = value
                    elif key == 'Диаметр':
                        diameter = value
                    elif key == 'Высота':
                        height = value
                    elif key == 'Ширина':
                        width = value
                    else:
                        description += key + ": " + value + '\n'
                if flag:
                    break
            item = Item(title = title,
                        price = int(price) * 5.5,
                        articul = articul,
                        diameter = diameter,
                        height = height,
                        width = width,
                        description1 = description,
                        description2 = description2,
                        slug = articul.replace(' ', '').replace('/', ''),
                        category = Category.objects.get_or_create(title = 'Люстры')[0],
                        subcategory = SubCategory.objects.get_or_create(title = 'Потолочные люстры')[0],
                        brand = Brand.objects.get_or_create(title = 'Odeon Light')[0]
                        )
            images = page.find('div', class_='product-images__large').find_all('a')
            print(len(images))
            response = requests.get(href+images[0]['href']+sec)
            response.raise_for_status()
            item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
            item.save()
            i = 0
            for imag in images:
                i += 1
                if i == 1:
                    continue
                try:
                    img = ItemImage(post=item)
                    response = requests.get(href+imag['href']+sec)
                    response.raise_for_status()
                    img.images.save(f"{title}.jpg", ContentFile(response.content), save=True)
                    img.save()
                    print(i)
                except:
                    continue
        #     try:
        #         price = int(
        #             page.find('div', class_='items_price').text.replace(' ', '').replace('\xa0', '').replace('\n',
        #                                                                                                      '').replace(
        #                 '\t', '').replace('руб.', ''))
        #         descriptions = page.find_all('div', class_='col-md-6 hars')
        #         teh = ""
        #         outlook = ""
        #         diametre = 0
        #         height = 0
        #         max_height = 0
        #         min_height = 0
        #         for i in descriptions:
        #             if i.text.split('\n')[1].startswith('Тип цоколя:'):
        #                 teh += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
        #             elif i.text.split('\n')[1].startswith('Лампочки в комплекте:'):
        #                 teh += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
        #             elif i.text.split('\n')[1].startswith('Напряжение питания, В:'):
        #                 teh += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
        #             elif i.text.split('\n')[1].startswith('Степень защиты, IP:'):
        #                 teh += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
        #
        #             if i.text.split('\n')[1].startswith('Форма светильника:'):
        #                 outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
        #             elif i.text.split('\n')[1].startswith('Форма плафона:'):
        #                 outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
        #             elif i.text.split('\n')[1].startswith('Стиль светильника:'):
        #                 outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
        #             elif i.text.split('\n')[1].startswith('Интерьер:'):
        #                 outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
        #             elif i.text.split('\n')[1].startswith('Материал основания:'):
        #                 outlook += i.text.split('\n')[1] + " " + i.text.split('\n')[2] + '\n'
        #             if i.text.split('\n')[1].startswith('Диаметр, мм:'):
        #                 diametre = i.text.split('\n')[2]
        #             if i.text.split('\n')[1].startswith('Высота, мм:'):
        #                 height = i.text.split('\n')[2]
        #             if i.text.split('\n')[1].startswith('Высота минимальная, мм:'):
        #                 min_height = i.text.split('\n')[2]
        #             if i.text.split('\n')[1].startswith('Высота максимальная, мм:'):
        #                 max_height = i.text.split('\n')[2]
        #         print(teh)
        #         print('height: ' + str(height))
        #         print('diameter: ' + str(diametre))
        #         image_urls = []
        #         images = page.find_all('img', class_='img-fluid')
        #         for image in images:
        #             image_urls.append(href + image['src'])
        #         print('Title: ' + title)
        #         temp = descriptions[1].text.split('\n')[2].split('  / ')
        #         category = temp[0]
        #         subcategory = temp[1]
        #         print("Категория: " + category)
        #         print("Подкатегория: " + subcategory)
        #         temp = descriptions[2].text.split('\n')[2]
        #         articul = temp.replace("/", "_")
        #         print("Артикул: " + articul)
        #         temp = int(descriptions[4].text.split('\n')[2])
        #         print("min height: " + str(temp))
        #         temp = int(descriptions[5].text.split('\n')[2])
        #         print("max height: " + str(temp))
        #         item = Item(title=title,
        #                     category=Category.objects.get_or_create(title=category)[0],
        #                     subcategory=SubCategory.objects.get_or_create(title=subcategory)[0],
        #                     articul=articul,
        #                     price=int(price) * 6.5,
        #                     slug=articul.replace(" ", "_"),
        #                     description1=teh,
        #                     description2=outlook,
        #                     brand=Brand.objects.get_or_create(title='Loft it')[0],
        #                     diameter=diametre,
        #                     height=height,
        #                     min_height=min_height,
        #                     max_height=max_height,
        #                     )
        #         # for image in image_urls:
        #         print(image_urls[0])
        #         response = requests.get(image_urls[0])
        #         response.raise_for_status()
        #         item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
        #         item.save()
        #         i = 0
        #         for imag in image_urls:
        #             i += 1
        #             if i == 1:
        #                 continue
        #             try:
        #                 img = ItemImage(post=item)
        #                 response = requests.get(imag)
        #                 response.raise_for_status()
        #                 img.images.save(f"{title}.jpg", ContentFile(response.content), save=True)
        #                 img.save()
        #                 print(i)
        #             except:
        #                 continue
        #     except:
        #         continue
    return JsonResponse()



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

def copy(request):
    items = Item.objects.filter(collection='DELUXE', subcategory__title='Французская елка')
    for item in items:
        item1 = Item()
        item1.length = item.length
        item1.width = item.width
        item1.thickness = item.thickness
        item1.wood_type = item.wood_type
        item1.faska = item.faska
        item1.collection = item.collection
        item1.category = item.category
        item1.subcategory = SubCategory.objects.get_or_create(title='Английская елка')[0]
        item1.articul = item.articul
        item1.slug = item.slug
        item1.description1 = item.description1
        item1.brand = item.brand
        item1.title = item.title
        item1.price = item.price
        item1.save()


def st_luce(request):
    href = 'https://stluce.ru/'
    for i in range(1, 31):
        soup = BeautifulSoup(get(href + '/catalog/st_luce/filter/tip_svetilnika-is-5d7c9d7a-2caa-11e6-80cf-001dd8b75054-or-bf7cc4ce-2caa-11e6-80cf-001dd8b75054/apply/?BY=asc&PAGEN_1=' + str(i)).text, 'html.parser')
        items = soup.find_all('div', class_='catalog-container-thumb-photo')
        for item in items:
            # print(item)
            page = BeautifulSoup(get(href+item.find_all('a')[-1]['href']).text, 'html.parser')
            print(href+item.find_all('a')[-1]['href'])
            title = page.find('div', class_='title-page title-page-no-bord').text.strip()
            price = page.find_all('div', class_='price')[1].text.strip().replace(' руб.', '').replace(' ', '')
            print(title + ": " + price)
            table = page.find_all('div', class_='product-description_characteristics')[1]
            height = diameter = width = length = min_height = max_length = 0
            description = ''
            for row in table.find_all('li'):
                # print(row)
                key = row.find_all('span')[0].text.strip()
                value = row.find_all('span')[1].text.strip()
                if value == 'Люстра подвесная':
                    type = 'Подвесные люстры'

                elif value == 'Люстра потолочная':
                    type = 'Потолочные люстры'

                elif key == 'Артикул':
                    articul = value
                elif key == 'Высота,мм':
                    height = value
                elif key == 'Длинна,мм':
                    height = value
                elif key == 'Диаметр,мм':
                    diameter = value
                elif key == 'Высота max,мм':
                    max_height = value
                elif key == 'Ширина,мм':
                    width = value
                elif key == 'Высота min,мм':
                    min_height = value
                else:
                    description += key + ": " + value + '\n'
            item = Item(
                title=title,
                price=int(price)*5.5,
                articul=articul,
                slug=articul.replace(' ', '').replace('.', '').replace('/', ''),
                height=height,
                length = length,
                diameter=diameter,
                max_height=max_height,
                min_height=min_height,
                width=width,
                description1=description,
                brand=Brand.objects.get_or_create(title='ST LUCE')[0],
                category=Category.objects.get_or_create(title='Люстры')[0],
                subcategory=SubCategory.objects.get_or_create(title=type)[0]
            )
            images = page.find('div', class_='product-photo').find_all('img')
            images = list(set(images))
            response = requests.get(href+images[0]['src'])
            response.raise_for_status()
            item.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
            item.save()
            i = 0
            for imag in images:
                i += 1
                if i == 1:
                    continue
                try:
                    img = ItemImage(post=item)
                    response = requests.get(href+imag['src'])
                    response.raise_for_status()
                    img.images.save(f"{title}.jpg", ContentFile(response.content), save=True)
                    img.save()
                except:
                    continue

def alsa_floor(request):
    href = 'http://www.alsafloor.ru'
    soup = BeautifulSoup(get(href + '/collection').text, 'html.parser')
    collections = soup.find('ul', class_='catalog-collection collection-view-tile').find_all('div', class_='catalog-collection-item-content feed-item-content block-content')
    for collection in collections:
        print(collection.find('a')['href'])
        collection1 = collection.find('h3').text.strip()
        page = BeautifulSoup(get(href+collection.find('a')['href']).text, 'html.parser')
        items = page.find('ul', class_='catalog-collection collection-view-tile').find_all('li')
        params = page.find('div', class_='block-text block-type-catalogitem-text textcontent').find_all('li')
        description1 = description2 = ''
        for row in params:
            if len(row.text.strip().split(':')) < 2:
                description1+=row.text.strip() + '\n'
                continue
            print(row.text.strip().split(':'))
            key = row.text.strip().split(':')[0]
            value = row.text.strip().split(':')[1]
            if key == 'Размеры доски':
                print(value.split('x'))
                print(value.split('х'))
                try:
                    length = value.split('x')[0]
                    width = value.split('x')[1]
                except:
                    length = value.split('х')[0]
                    width = value.split('х')[1]
            else:
                description1 += row.text.strip() + '\n'
        print(width + " " + length)
        print(len(items))
        for item in items:
            print(item.find('h3').text.strip())
            title = item.find('h3').text.strip()
            table = item.find('div', class_='item-params').find_all('div', class_=lambda x: x and x.startswith("item-desc-row"))
            for row in table:
                print(row.text.strip())
                key = row.find_all('div')[0].text.strip()
                value = row.find_all('div')[1].text.strip()
                if key =='Артикул':
                    articul = value
                elif key == 'Толщина':
                    thickness = value
                else:
                    description2+=key + ": " + value + '\n'
            item1 = Item(title=title,
                        articul = articul,
                        slug = articul + '_' + title,
                        thickness = thickness,
                        length = length,
                        width = width,
                        description1 = description1,
                        description2 = description2,
                        brand = Brand.objects.get_or_create(title='Alsafloor')[0],
                        category=Category.objects.get_or_create(title='Ламинаи')[0],
                        subcategory=SubCategory.objects.get_or_create(title='Ламинат')[0],
                        collection = collection1
                    )
            img = item.find('img')['src']
            response = requests.get(img)
            response.raise_for_status()
            item1.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
            item1.save()

# def images(request):
#     for item in Item.objects.all():
#         if not item.image or not default_storage.exists(item.image.name):
#             print(item.title)
#             print(item.slug)
#             print(item.image.url)
#             item.image = '123123'


def new_pergo(request):
    href = 'https://pergo.su'
    soup = BeautifulSoup(get(href + '/collection/stavanger-pro-8mm').text, 'html.parser')
    items = soup.find_all('div', class_='product-preview__area-title')
    for item in items:
        print(href+item.find('a')['href'])
        href1=item.find('a')['href']
        page = BeautifulSoup(get(href+href1).text, 'html.parser')
        title = page.find('h1', class_='product__title heading').text.strip()
        print(title)
        properties = page.find('div', class_='product__variants').text.strip().split('/')
        thickness = properties[0]
        width = properties[2]
        length = properties[3]
        faska = properties[4]
        description = page.find('div', class_='product-description static-text').text.strip()
        print(thickness)
        print(width)
        print(length)
        print(faska)
        print(description)
        item = Item(
            title=title,
            thickness=thickness,
            width=width,
            length=length,
            faska=faska,
            description1=description,
            brand=Brand.objects.get_or_create(title='Pergo')[0],
            category=Category.objects.filter(title='Ламинат')[0],
            subcategory=SubCategory.objects.get_or_create(title='Ламинат')[0],
            slug=href1.split('/')[2],
            articul=href1.split('/')[2],
            collection='Stavanger pro'
        )
        item.save()


def pergo(request):
    href = 'https://vmasterskoy.kz'
    soup = BeautifulSoup(get(href + '/search/?value=pergo').text, 'html.parser')
    print(href + '/search/?value=pergo')
    items = soup.find_all('div', class_='col-md-3 designer_item')
    print(len(items))
    for item in items:
        print(href + item.find('a')['href'])
        page = BeautifulSoup(get(href + item.find('a')['href']).text, 'html.parser')
        title = page.find('h1').text.strip()
        description = ''
        table = page.find('div', class_='cont_box active').find_all('li')
        for row in table:
            key = row.find_all('div')[0].text.strip()
            value = row.find_all('div')[1].text.strip()
            print(key + ": " + value)
            if key == 'Артикул':
                articul = value
            elif key == 'Толщина':
                thickness = value.replace('мм', '')
            elif key == 'Материал':
                wood_type = value
            elif key == 'Ширина':
                width = value.replace('мм', '')
            elif key == 'Длина':
                length = value.replace('мм', '')
            else:
                description+=key + ": " + value + '\n'
        price = ''.join(filter(str.isdigit, page.find('div', class_='price').text.strip()))
        print(price)
        item1 = Item(title=title,
                    price=price,
                    articul=articul,
                    thickness=thickness,
                    wood_type=wood_type,
                    width=width,
                    length=length,
                    slug=articul,
                    brand=Brand.objects.get_or_create(title='Pergo')[0],
                    category=Category.objects.filter(title='Ламинат')[0],
                    subcategory=SubCategory.objects.get_or_create(title='Ламинат')[0],
                    description1=description
                )
        image = page.find('div', class_='card_slider').find('a')['href']
        response = requests.get(href+image)
        response.raise_for_status()
        item1.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
        item1.save()

def dogal(request):
    href='https://tineks.kz'
    for i in range(1,8):
        soup = BeautifulSoup(get(href+'/catalog/55/filter/brend-is-c260b7d6-a2ef-11e9-946a-0cc47a7ec1cf/apply/?PAGEN_1=' + str(i)).text, 'html.parser')
        print()
        items = soup.find_all('div', class_='catalog-item')
        print(len(items))
        for item in items:
            page = BeautifulSoup(get(href+item.find('a')['href']).text, 'html.parser')
            title = page.find('div', class_='detail--title').text.strip()
            print(title)
            price = ''.join(filter(str.isdigit, page.find('div', class_='col-xs-12 prices--curr').text.strip().replace('тнг за м2', '')))
            table = page.find('div', class_='props').find_all('li')
            description=''
            for row in table:
                key = row.find_all('span')[0].text.strip()
                value = row.find_all('span')[1].text.strip()
                if key == 'Длина':
                    length = value
                elif key == 'Kоллекция':
                    collection = value
                elif key == 'Дизайн':
                    design = value
                elif key == 'Ширина':
                    width = value
                elif key == 'Толщина':
                    thickness = value
                elif key == 'Цвет':
                    color = value
                else:
                    description+=key + ": " + value + '\n'
            item1 = Item(
                title=title,
                price=price,
                length=length,
                collection=collection,
                design=design,
                width=width,
                thickness=thickness,
                color=Color.objects.get_or_create(title=color)[0],
                articul=title.replace(' ', '_'),
                slug=title.replace(' ', '_'),
                category=Category.objects.filter(title='Ламинат')[0],
                subcategory=SubCategory.objects.filter(title='Ламинат')[0],
                brand=Brand.objects.get_or_create(title='Varioclic')[0],
                description1=description
            )
            try:
                image = page.find('img', class_='my-foto')['src']
                response = requests.get(href + image)
                response.raise_for_status()
                item1.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
            except:
                item1.image='123123'
            item1.save()


def firm(request):
    href='https://tineks.kz'
    for i in range(1,2):
        soup = BeautifulSoup(get(href+'/catalog/76/filter/brend-is-e4a005ba-281a-11ec-95e5-0cc47a7ec1cf/apply/').text, 'html.parser')
        print()
        items = soup.find_all('div', class_='catalog-item')
        print(len(items))
        for item in items:
            page = BeautifulSoup(get(href+item.find('a')['href']).text, 'html.parser')
            title = page.find('div', class_='detail--title').text.strip()
            print(title)
            price = ''.join(filter(str.isdigit, page.find('div', class_='col-xs-12 prices--curr').text.strip().replace('тнг за м2', '')))
            table = page.find('div', class_='props').find_all('li')
            description=''
            for row in table:
                key = row.find_all('span')[0].text.strip()
                value = row.find_all('span')[1].text.strip()
                if key == 'Длина':
                    length = value
                elif key == 'Kоллекция':
                    collection = value
                elif key == 'Дизайн':
                    design = value
                elif key == 'Ширина':
                    width = value
                elif key == 'Толщина':
                    thickness = value
                else:
                    description+=key + ": " + value + '\n'
            item1 = Item(
                title=title,
                price=price,
                length=length,
                collection=collection,
                design=design,
                width=width,
                thickness=thickness,
                articul=title.replace(' ', '_'),
                slug=title.replace(' ', '_'),
                category=Category.objects.filter(title='SPC')[0],
                subcategory=SubCategory.objects.get_or_create(title=collection)[0],
                brand=Brand.objects.get_or_create(title='FirmFit')[0],
                description1=description
            )
            try:
                image = page.find('img', class_='my-foto')['src']
                response = requests.get(href + image)
                response.raise_for_status()
                item1.image.save(f"{title}.jpg", ContentFile(response.content), save=True)
            except:
                item1.image='123123'
            item1.save()


def slug(request):
    for item in Item.objects.all():
        try:
            item.slug = item.slug.replace('/', '_')
            item.save()
        except:
            item.slug = item.pk
