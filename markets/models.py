from django.db import models
from django.db.models import Sum
from datetime import datetime, timedelta
from django.contrib.auth.models import User

class Proposition(models.Model):
    """A propostional market for which tokens may be traded."""

    code = models.CharField(max_length=3,
        help_text='The three-letter proposition code.')

    description = models.CharField(max_length=100,
        help_text='The definitive proposition statement.')

    resolve_date = models.DateField(
        help_text='The date on which this proposition will resolve.')

    active = models.BooleanField(
        help_text='Whether this proposition is enabled and unresolved.')

    result = models.BooleanField(
        help_text='Whether this proposition resolved in favour of the affirmative.')

    def __str__(self): return '['+self.code+'] '+self.description

    class Meta: ordering = ['active', 'resolve_date', 'code']

    def get_price(self, time=None, affirm=True):
        """Get the current (or previous) price of this proposition."""

        # Default to the current time.
        if not time: time = datetime.now()
        time_str = time.strftime('%Y-%m-%d %H:%M:%S')

        # Get all transactions for this proposition before the given time.
        transactions = (Transaction.objects
            .filter(proposition_id=self.id)
            .filter(time__lt=time_str))

        if(transactions.exists()):
            # Price is given by the most recent transaction.
            price = transactions.first().price
            if not affirm: price = 100 - price
            return price
        else: return 50

    def get_change(self, start, end=None, affirm=True):
        """Get the percentage change in price between two times."""

        # Default to the current time.
        if not end: end = datetime.now()

        # Get prices and start and end of given period.
        start_price = self.get_price(time=start, affirm=affirm)
        end_price = self.get_price(time=end, affirm=affirm)

        # Calculate percentage change.
        return 100 * (end_price - start_price) // start_price

    def get_volume(self, start, end=None):
        """Get the trade volume between two times."""

        # Default to the current time.
        if not end: end = datetime.now()
        start_str = start.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end.strftime('%Y-%m-%d %H:%M:%S')

        # Sum the quantity of all transactions in the given period.
        sum = (Transaction.objects
            .filter(proposition_id=self.id)
            .filter(time__gt=start_str)
            .filter(time__lt=end_str)
            .aggregate(Sum('quantity'))['quantity__sum'])

        return sum if sum != None else 0

    def get_orders(self, affirm=True):
        """Get pending orders of given type sorted by decreasing price."""
        return (Order.objects
            .filter(proposition_id=self.id)
            .filter(affirmative=affirm))

    def get_price_history(self, affirm=True):
        """Get price history for proposition."""
        history = list(map(lambda t : {'time': t.time, 'price': t.price},
                   Transaction.objects.filter(proposition_id=self.id)))
        history.insert(0, {'time': datetime.now(), 'price': self.get_price(affirm=affirm)})
        return history

    def get_stake(self, user):
        """Get stake of given user in this proposition, or None."""

        stake = (Stake.objects
            .filter(user_id=user.id)
            .filter(proposition_id=self.id))

        return stake.get() if stake.exists() else None

    def place_order(self, user, affirm, quantity, price, total):
        """Place a new order of this proposition."""

        # Deduct price of order from user.
        funds = Funds.objects.get(user_id=user.id)
        funds.value -= total
        funds.save()

        # Get all orders which match with this one.
        orders = (Order.objects
            .filter(proposition_id=self.id)
            .filter(affirmative=not affirm))

        # For each matching order.
        for order in orders:
            # Stop if the matching price isn't good enough.
            if order.price + price < 100: break

            # Create a new transaction.
            trans = Transaction.objects.create(
                proposition=self,
                affirmative_user=user if affirm else order.user,
                negative_user=order.user if affirm else user,
                price=(price-order.price+100)/2 if affirm else (order.price-price+100)/2,
                quantity=min(quantity, order.quantity)
            )

            # Add stake to both users.
            self.add_stake(trans.affirmative_user, True, trans.quantity)
            self.add_stake(trans.negative_user, False, trans.quantity)

            # Subtract amount matched from pending orders.
            order.quantity -= trans.quantity
            if order.quantity == 0: order.delete()
            else: order.save()

            # Stop if the new order is completed.
            quantity -= trans.quantity
            if quantity == 0: break

        # Save the remainder of the order if it wasn't completed.
        if quantity > 0:
            Order.objects.create(
                proposition=self,
                user=user,
                price=price,
                quantity=quantity,
                affirmative=affirm
            )

    def add_stake(self, user, affirm, quantity):
        """Give stake in this proposition to a user."""
        
        # Get the current stake the user has in this proposition.
        stake = (Stake.objects
            .filter(user_id=user.id)
            .filter(proposition_id=self.id))

        # Create a new stake with the given amount if none already exists.
        if not stake.exists():
            Stake.objects.create(
                user=user,
                proposition=self,
                quantity=quantity,
                affirmative=affirm
            )

        else:
            stake = stake.get()
            
            # Add the given amount to the existing stake if the types match.
            if stake.affirmative == affirm:
                stake.quantity += quantity
                stake.save()

            # Stakes of opposite types cancel out.
            else:
                # Provide a refund for cancelled stakes.
                funds = Funds.objects.get(user_id=user.id)
                funds.value += min(quantity, stake.quantity)
                funds.save()

                # Subtract the given amount from the existing stake.
                stake.quantity -= quantity

                # A negative stake means the type should be flipped.
                if stake.quantity < 0:
                    stake.quantity *= -1
                    stake.affirmative ^= True

                # A zero stake should be deleted.
                if(stake.quantity == 0): stake.delete()
                else: stake.save()

class Order(models.Model):
    """A pending order awaiting a matching counter-order."""

    proposition = models.ForeignKey('Proposition', on_delete=models.CASCADE,
        help_text='The proposition on which the order is placed.')

    user = models.ForeignKey(User, on_delete=models.CASCADE,
        help_text='The user who placed the order.')

    price = models.IntegerField(
        help_text='The price the user is willing to pay per token (c).')

    quantity = models.IntegerField(
        help_text='The number of tokens the user wants to purchase.')

    affirmative = models.BooleanField(
        help_text='Whether the order is for the negative or affirmative.')

    time = models.DateTimeField(auto_now=True)

    def __str__(self):
        type = 'Affirmative' if self.affirmative else 'Negative'
        return ('['+str(self.proposition.code)+'] '+self.user.username
                +': '+str(self.quantity)+'x '+type+' @ '+str(self.price)+'c')

    class Meta: ordering = ['proposition', 'affirmative', '-price', 'time']

    def refund(self):
        """Cancels this order and refunds the user."""

        # Refund price of order.
        funds = Funds.objects.get(user_id=request.user.id)
        funds.value = float(funds.value) + (self.price * self.quantity / 100)

        # Delete order.
        self.delete()
        funds.save()

class Transaction(models.Model):
    """A successful transaction between two users."""

    proposition = models.ForeignKey('Proposition', on_delete=models.CASCADE,
        help_text='The proposition which was traded.')

    affirmative_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='yes_bidder',
        help_text='The user in favour of the affirmative.')

    negative_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='no_bidder',
        help_text='The user in favour of the negative.')

    price = models.IntegerField(
        help_text='The affirmative price at which the tokens were traded (c).')

    quantity = models.IntegerField(
        help_text='The number of tokens which were traded.')

    time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return ('['+str(self.proposition.code)+'] '+str(self.quantity)
                +'x @ ('+str(self.price)+'c/'+str(100-self.price)+'c)')

    class Meta: ordering = ['proposition', '-time']

class Stake(models.Model):
    """The stake in some proposition currently held by some user."""

    proposition = models.ForeignKey('Proposition', on_delete=models.CASCADE,
        help_text='The propostion in which the stake is held.')

    user = models.ForeignKey(User, on_delete=models.CASCADE,
        help_text='The owner of the stake.')

    quantity = models.IntegerField(
        help_text='The amount of stake owned ($).')

    affirmative = models.BooleanField(
        help_text='Whether the stake is for the negative or affirmative.')

    def __str__(self):
        type = 'Affirmative' if self.affirmative else 'Negative'
        return ('['+str(self.proposition.code)+'] '+self.user.username
                +': '+str(self.quantity)+'x '+type)

    class Meta: ordering = ['user', 'proposition']

class Funds(models.Model):
    """The current available balance of some user ($AUD)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    value = models.DecimalField(decimal_places=2, max_digits=12,
        help_text='Available funds ($AUD).')

    def __str__(self): return str(self.user) + ': $' + str(self.value)

    class Meta:
        ordering = ['user']
        verbose_name_plural = 'funds'

    def get_estimated_value(self):
        """Provides an estimate for the net worth of this user."""

        # Include available funds.
        value = float(self.value)

        # Include stakes, scaled down by latest prices.
        for s in Stake.objects.filter(user_id=self.user.id):
            if s.affirmative: value += s.quantity * s.proposition.get_price(affirm=True) / 100
            else: value += s.quantity * s.proposition.get_price(affirm=False) / 100

        # Include pending orders.
        for order in Order.objects.filter(user_id=self.user.id):
            value += order.price * order.quantity / 100

        return round(value, 2)