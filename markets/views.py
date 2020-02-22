from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import OrderForm

def browse_view(request):
    """Browse page featuring list of all active propositions."""

    return render(request, 'markets/browse.html', {
        # The list of propositions to display.
        'propositions': map(lambda prop : {
            'code': prop.code,
            'description': prop.description,
            'trade_volume': prop.trade_volume(
                start=datetime.now()-timedelta(days=1)),
            'bid_volume': prop.bid_volume(),
            'resolves': prop.resolve_date,
            'active': prop.active,
            'leader': {
                'outcome': prop.outcomes_by_price()[0],
                'price': prop.outcomes_by_price()[0].latest_price()
            },
        }, Proposition.objects.all() if 'show-completed' in request.GET else
            Proposition.objects.filter(active=True)),
        'show_completed': 'show-completed' in request.GET
    })

def proposition_view(request, code):
    """Detailed information page for single proposition."""

    # Extract the current proposition from the request.
    prop = get_object_or_404(Proposition, code=code)

    return render(request, 'markets/proposition.html', {
        # Proposition information.
        'prop': {
            'code': prop.code,
            'description': prop.description,
            'resolves': prop.resolve_date.strftime('%b. %d, %Y'),
            'remaining': (prop.resolve_date - datetime.now().date()).days,
            'trade_volume': prop.trade_volume(
                start=datetime.now()-timedelta(days=1)),
            'bid_volume': prop.bid_volume(),
            'total_stake': prop.total_stake(),
        },
        'outcome': {
            'code': prop.outcomes_by_price()[0].code,
            'affirm': True
        },
        'result': prop.outcome if not prop.active else None
    })

def graph_view(request, code):
    """The graph displaying price history, embedded within the proposition view."""

    # Extract proposition, start time and end time from the request.
    prop = get_object_or_404(Proposition, code=code)
    end = datetime.now()
    seconds = (int(request.GET.get('time'))
        if 'time' in request.GET else 60*60*24*7)
    start = end - timedelta(seconds=seconds)

    return render(request, 'markets/graph.html', {
        # The price data for each outcome.
        'outcomes': map(lambda o: {
            'description': o.description,
            'colour': o.colour,
            'prices': o.prices(start=start)
        }, prop.outcomes_by_price()),
        # Graph display properties.
        'start_time': start,
        'end_time': end
    })

def order_view(request, code):
    """The form for ordering tokens, embedded within the proposition view."""

    # Extract the proposition and outcome from the request.
    prop = get_object_or_404(Proposition, code=code)
    d = request.GET if request.GET else request.POST
    outcome = (get_object_or_404(Outcome, code=d.get('outcome'))
        if 'outcome' in d else prop.outcomes_by_price()[0])
    affirm = d.get('affirm')=='true' if 'affirm' in d else True

    # Place a new order for tokens.
    order_placed = False
    if 'place-order' in request.POST:
        order_form = OrderForm(request.POST, user=request.user,
            outcome=outcome, affirm=affirm)
        # If the information given is all valid.
        if order_form.is_valid():
            price = order_form.cleaned_data['price']
            quantity = order_form.cleaned_data['quantity']
            # Place the order.
            prop.place_order(outcome, affirm, price, quantity, request.user)
            order_placed = True
    else: order_form = OrderForm(None, user=request.user,
        outcome=outcome, affirm=affirm)

    # Cancel a pending order.
    if 'cancel-order' in request.POST:
        id = request.POST.get('cancel-order')
        order = get_object_or_404(Order, id=id)
        if order.user == request.user: order.cancel()

    # Resolve a proposition in favour of some outcome.
    if 'resolve' in request.POST:
        if request.user.is_staff:
            prop.resolve(outcome)

    return render(request, 'markets/order.html', {
        # The proposition to which this page is dedicated.
        'prop': {
            'code': prop.code,
            'description': prop.description,
            'active': prop.active
        },
        # The currently selected outcome.
        'outcome': {
            'code': outcome.code,
            'description': outcome.description,
            'affirm': affirm,
            'bid_price': outcome.bid_price(affirm),
            'ask_price': outcome.ask_price(affirm),
            'latest_price': outcome.latest_price(affirm),
            'price_change': outcome.percentage_change(affirm)
        },
        # Form details.
        'outcomes': prop.outcomes_by_price(),
        'orders': outcome.orders(affirm)[:10],
        'order_form': order_form,
        'order_placed': order_placed,
        'funds': Funds.users.get(request.user)
    })

def balances_view(request):
    """Balances page for showing funds, stakes and orders."""

    # User must be logged in to view balances.
    if not request.user.is_authenticated:
        return redirect('/accounts/login?next=/markets/balances')

    # Cancel a pending order.
    if 'cancel-order' in request.GET:
        id = request.GET.get('cancel-order')
        order = get_object_or_404(Order, id=id)
        if order.user == request.user:
            order.cancel()
            return redirect('/markets/balances')

    # Remove completed tokens.
    if 'dismiss-payout' in request.GET:
        id = request.GET.get('dismiss-payout')
        tokens = get_object_or_404(Tokens, id=id)
        if tokens.user == request.user and not tokens.proposition.active:
            tokens.delete()
            return redirect('/markets/balances')

    # Get balances owned by the user.
    funds = Funds.users.get(request.user)
    tokens = Tokens.tokens.filter(user_id=request.user.id)

    return render(request, 'markets/balances.html', {
        'funds': funds.value,
        'est_value': funds.estimated_value(),
        'active_tokens': tokens.filter(proposition__active=True),
        'inactive_tokens': tokens.filter(proposition__active=False),
        'orders': Order.objects.filter(user_id=request.user.id),
    })