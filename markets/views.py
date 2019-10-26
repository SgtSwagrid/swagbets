from django.shortcuts import render, redirect, get_object_or_404
from datetime import date, datetime, timedelta
from .models import *
from .forms import OrderForm

def browse_view(request):
    """Browse page featuring list of all active propositions."""

    yesterday = datetime.now() - timedelta(days=1)

    return render(request, 'markets/browse.html', {
        # For each active proposition:
        'propositions': map(lambda prop : {
            # Proposition information.
            'code': prop.code,
            'description': prop.description,
            'resolve_date': prop.resolve_date,
            'volume': prop.get_volume(start=yesterday),
            # Latest prices.
            'price_aff': prop.get_price(affirm=True),
            'price_neg': prop.get_price(affirm=False),
            # Percentage change in prices.
            'change_aff': '{:+d}'.format(prop.get_change(start=yesterday, affirm=True)),
            'change_neg': '{:+d}'.format(prop.get_change(start=yesterday, affirm=False))
         }, Proposition.objects.filter(active=True))
    })

def proposition_view(request, code):
    """Detailed information page for single proposition."""

    prop = get_object_or_404(Proposition, code=code)
    yesterday = datetime.now() - timedelta(days=1)

    # User must be logged in to place order.
    if request.POST and not request.user.is_authenticated:
        return redirect('/accounts/login?next=/markets/'+code)

    # If an order for the affirmative was submitted.
    if request.POST.get('order-aff'):
        form_aff = OrderForm(request.POST, user=request.user, prefix='aff')
        if form_aff.is_valid():
            prop.place_order(request.user, True, form_aff.cleaned_data['quantity'],
                form_aff.cleaned_data['price'], form_aff.cleaned_data['total'])
            return redirect('/markets/'+code)
    else: form_aff = OrderForm(None, user=request.user, prefix='aff')

    # If an order for the negative was submitted.
    if request.POST.get('order-neg'):
        form_neg = OrderForm(request.POST, user=request.user, prefix='neg')
        if form_neg.is_valid():
            prop.place_order(request.user, False, form_neg.cleaned_data['quantity'],
                form_neg.cleaned_data['price'], form_neg.cleaned_data['total'])
            return redirect('/markets/'+code)
    else: form_neg = OrderForm(None, user=request.user, prefix='neg')

    return render(request, 'markets/proposition.html', {
        # Proposition information.
        'code': prop.code,
        'description': prop.description,
        'resolve_date': prop.resolve_date,
        'days_remaining': (prop.resolve_date - datetime.now().date()).days,
        'stake': prop.get_stake(user=request.user),
        # Latest prices.
        'price_aff': prop.get_price(affirm=True),
        'price_neg': prop.get_price(affirm=False),
        # Lists of pending orders.
        'orders_aff': prop.get_orders(affirm=True),
        'orders_neg': prop.get_orders(affirm=False),
        # Order placement forms.
        'form_aff': form_aff,
        'form_neg': form_neg
    })

def balances_view(request):
    """Balances page for showing funds, stakes and orders."""

    # User must be logged in to view balances.
    if not request.user.is_authenticated:
        return redirect('/accounts/login?next=/markets/balances')

    if Funds.objects.filter(user_id=request.user.id).exists():
        f = Funds.objects.get(user_id=request.user.id)
        funds = f.value; value = f.get_estimated_value();
    else: funds = 0; value = 0

    return render(request, 'markets/balances.html', {
        'funds': funds,
        'value': value,
        'stakes': Stake.objects.filter(user_id=request.user.id),
        'orders': Order.objects.filter(user=request.user.id)
    })

def history_view(request, code):
    """Provides the full history of prices for a proposition."""

    prop = get_object_or_404(Proposition, code=code)
    # 'history.js' will initialize the variable 'price_data'.
    return render(request, 'markets/history.js', {
        'prices': prop.get_price_history()
    })

def cancel_view(request, id):
    """Cancels an order with a particular ID."""

    order = get_object_or_404(Order, id=id)
    # Ensure order is owned by current user; delete and refund order.
    if order.user == request.user: order.refund()
    return redirect('/markets/balances')