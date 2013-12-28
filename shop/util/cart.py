# -*- coding: utf-8 -*-
from shop.models.cartmodel import Cart, CartItem  # I add CartItem <-- PB
from shop.models.ordermodel import Order, OrderItem  # I add CartItem <-- PB
from django.contrib.auth.models import AnonymousUser

from shop.models.productmodel import Product # I add this import <-- PB
from django.contrib import messages  # I add this import <-- PB
from django.utils.translation import ugettext_lazy as _   # I add this import <-- PB



def get_cart_from_database(request):
    database_cart = Cart.objects.filter(user=request.user)
    if database_cart:
        database_cart = database_cart[0]
    else:
        database_cart = None
    return database_cart

def get_cart_from_session(request):
    session_cart = None
    session = getattr(request, 'session', None)
    if session is not None:
        cart_id = session.get('cart_id')
        if cart_id:
            try:
                session_cart = Cart.objects.get(pk=cart_id)
            except Cart.DoesNotExist:
                session_cart = None
    return session_cart

def get_or_create_cart(request, save=False):
    """
    Return cart for current visitor.

    For a logged in user, try to get the cart from the database. If it's not there or it's empty,
    use the cart from the session.
    If the user is not logged in use the cart from the session.
    If there is no cart object in the database or session, create one.

    If ``save`` is True, cart object will be explicitly saved.
    """
    cart = None
    if not hasattr(request, '_cart'):
        is_logged_in = request.user and not isinstance(request.user, AnonymousUser)

        if is_logged_in:
            # if we are authenticated
            session_cart = get_cart_from_session(request)
            if session_cart and session_cart.user == request.user:
                # and the session cart already belongs to us, we are done
                cart = session_cart
            elif session_cart and session_cart.total_quantity > 0 and session_cart.user != request.user:
                # if it does not belong to us yet
                database_cart = get_cart_from_database(request)
                if database_cart:
                    # and there already is a cart that belongs to us in the database
                    # delete the old database cart
                    database_cart.delete()
                # save the user to the new one from the session
                session_cart.user = request.user
                session_cart.save()
                cart = session_cart

                """ 
                Hook by pb

                In this part, we try to delete user's own products that user put in cart before log in
                """ 
                try:
                    session_cart_items = CartItem.objects.filter(cart_id=cart.id)
                except CartItem.DoesNotExist:
                    session_cart_items = None
                if session_cart_items:
                    for item in session_cart_items:
                        if item.product_id:
                            pdt = Product.objects.get(pk=item.product_id)
                            # if video is mine
                            if pdt.user == request.user:
                                item.delete()
                                messages.add_message(request, messages.ERROR, 
                                    _("Your cart is modified."), extra_tags='alert-warning')

                if request.user.is_authenticated():
                    try:
                        orders_user = Order.objects.filter(user_id=request.user.id)
                        print "try: orders_user: " + str(orders_user)
                    except Order.DoesNotExist:
                        orders_user = None
                    if orders_user:
                        session_cart_items = CartItem.objects.filter(cart_id=cart.id)
                        product_in_orderitem = OrderItem.objects.filter(order_id__in=orders_user).values('product_id').distinct()
                        both_products_session_orders = CartItem.objects.filter(cart_id=cart.id, product_id__in=product_in_orderitem)
                        for item in both_products_session_orders:
                            if item.product_id:
                                pdt = Product.objects.get(pk=item.product_id)
                                item.delete()
                                messages.add_message(request, messages.ERROR, 
                                _("Your cart is modified because you still bought a or few videos."), extra_tags='alert-warning')

                """
                End hook by pb
                """
            else:
                # if there is no session_cart, or it's empty, use the database cart
                cart = get_cart_from_database(request)
                if cart:
                    # and save it to the session
                    request.session['cart_id'] = cart.pk
        else:
            # not authenticated? cart might be in session
            cart = get_cart_from_session(request)

        if not cart:
            # in case it's our first visit and no cart was created yet
            if is_logged_in:
                cart = Cart(user=request.user)
            elif getattr(request, 'session', None) is not None:
                cart = Cart()

        if save and not cart.pk:
            cart.save()
            request.session['cart_id'] = cart.pk

        setattr(request, '_cart', cart)

    cart = getattr(request, '_cart')  # There we *must* have a cart
    return cart
