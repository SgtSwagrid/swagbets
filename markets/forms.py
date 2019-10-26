from django import forms
from .models import Order, Funds

class OrderForm(forms.Form):
    """Form used to place an order for a proposition."""

    # The number of tokens ordered.
    quantity = forms.IntegerField(
        widget=forms.NumberInput({
            'class': 'form-control'
    }))

    # The price offered for each token (c).
    price = forms.IntegerField(
        widget=forms.NumberInput({
            'class': 'form-control'
    }))

    # The total price of the order ($).
    total = forms.DecimalField(decimal_places=2, max_digits=12,
        widget=forms.NumberInput({
            'class': 'form-control no-spinners'
    }))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(OrderForm, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        
        # Get quantity, price and total from form input.
        quantity = self.cleaned_data.get('quantity')
        price = self.cleaned_data.get('price')
        total = self.cleaned_data.get('total')

        # Ensure form inputs are all valid.
        # Usually handled by the browser, should not be triggered without malicious intent.

        if not self.user.is_authenticated:
            raise forms.ValidationError('Not signed-in.')

        if not quantity or not price or not total:
            raise forms.ValidationError('Value is missing.')

        if quantity <= 0 or price <= 0 or total <= 0:
            raise forms.ValidationError('All values must be positive.')

        if price >= 100:
            raise forms.ValidationError('Bid can\'t equal or exceed $1.')

        if abs(float(total) - (quantity * price / 100)) >= 0.001:
            raise forms.ValidationError('Total doesn\'t match quantity and price.')

        # Ensure user has enough funds to complete transaction.
        funds = Funds.objects.filter(user_id=self.user.id)
        balance = funds.get().value if funds.exists() else 0
        if total > balance:
            raise forms.ValidationError('Insufficient funds.')

        return super(OrderForm, self).clean(*args, **kwargs)