from django import forms
from .models import Funds

class OrderForm(forms.Form):
    """Form used to place an order for some proposition tokens."""

    # The price offered for each token (c).
    price = forms.IntegerField(
        widget=forms.NumberInput({
            'class': 'form-control',
            'title': 'Maximum bid per token.'
        }))

    # The number of tokens ordered.
    quantity = forms.IntegerField(
        widget=forms.NumberInput({
            'class': 'form-control',
            'title': 'Number of tokens.'
    }))

    # The total price of the order ($).
    total = forms.DecimalField(decimal_places=2, max_digits=12,
        widget=forms.NumberInput({
            'class': 'form-control no-spinners',
            'title': 'Total order cost ($AUD).'
    }))

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop('user', None)
        self.outcome = kwargs.pop('outcome', None)
        self.affirm = kwargs.pop('affirm', None)

        super(OrderForm, self).__init__(*args, **kwargs)

        # Determine initial field values.
        price = self.outcome.latest_price(affirm=self.affirm)
        total = round(10 * 100/price) * price/100 if price > 0 else 0
        quantity = round(100 * total / price) if price > 0 else 0

        self.fields['price'].initial = price
        self.fields['quantity'].initial = quantity
        self.fields['total'].initial = total

    def clean(self, *args, **kwargs):

        # Get quantity, price and total from form input.
        quantity = self.cleaned_data.get('quantity')
        price = self.cleaned_data.get('price')
        total = self.cleaned_data.get('total')

        # Ensure form inputs are all valid.

        if not quantity or not price or not total:
            raise forms.ValidationError('Value is missing.')

        if quantity < 0 or price < 0 or total < 0:
            raise forms.ValidationError('Values are negative.')

        if price > 100:
            raise forms.ValidationError('Bid exceeds $1.')

        if abs(float(total) - (quantity * price / 100)) >= 0.001:
            raise forms.ValidationError('Total doesn\'t match quantity and price.')

        if not self.outcome.proposition.active:
            raise forms.ValidationError('Proposition has already resolved.')

        # Ensure user is logged in.
        if not self.user.is_authenticated:
            raise forms.ValidationError('Not signed-in.')

        # Ensure user has enough funds to complete transaction.
        funds = Funds.users.get(self.user).value
        if total > funds:
            raise forms.ValidationError('Insufficient funds.')

        return super(OrderForm, self).clean(*args, **kwargs)