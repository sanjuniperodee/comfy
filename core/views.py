import requests
from .models import *
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator


# stripe.api_key = settings.STRIPE_SECRET_KEY

def home(request):
    return render(request, 'index.html')

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
        'description3': item.description3.split('\n')
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
    return render(request, 'profile.html', {'user': request.user})


def about_us(request):
    return render(request, 'about_us.html')