from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from colorfield.fields import ColorField

class Proposition(models.Model):
    """A propostion market for which tokens may be traded."""

    code = models.CharField(max_length=3,
        help_text='The three-letter proposition code.')

    description = models.CharField(max_length=100,
        help_text='The definitive proposition statement.')

    resolve_date = models.DateField(
        help_text='The date on which this proposition will resolve.')

    creation_date = models.DateField(
        help_text='The date on which this proposition was created.')

    active = models.BooleanField(
        help_text='Whether this proposition is enabled and unresolved.',
        default=True)

    outcome = models.ForeignKey('Outcome', related_name='outcome',
        on_delete=models.CASCADE, default=None, blank=True, null=True,
        help_text='The result of this proposition.')

    def __str__(self): return '['+self.code+'] '+self.description

    class Meta: ordering = ['-active', 'resolve_date', 'code']

    def outcomes(self):
        """Return the queryset of all possible outcomes for this proposition."""
        return Outcome.objects.filter(proposition=self)

    def outcomes_by_price(self):
        """Return a list of all outcomes, sorted by price."""
        return list(sorted(self.outcomes(), key=lambda o: -o.latest_price()))

    def place_order(self, outcome, affirm, price, quantity, user):
        """Place a new order on the proposition."""

        # Deduct funds from the user's account.
        funds = Funds.users.get(user)
        funds.value = float(funds.value) - quantity * price / 100
        funds.save()

        # Place the order.
        Order.objects.create(proposition=self, outcome=outcome, affirm=affirm,
             price=price, quantity=quantity, user=user).match()

    def trade_volume(self, start=None, end=None):
        """Returns total trade volume in a time period."""

        # Start from the beginning of time by default.
        if not start: start = datetime.min

        # End at the current time by default.
        if not end: end = datetime.now()

        # Calculate the total trade volume between the start and end times.
        prices = list(Price.prices
            .filter(proposition=self)
            .filter(time__gt=start)
            .filter(time__lt=end))
        return round(sum(p.price * p.quantity for p in prices) / 100)

    def bid_volume(self):
        """Returns current total volume (cents) of ongoing bids."""

        volume = 0
        for order in Order.objects.filter(proposition=self):
            volume += order.quantity * order.price
        return round(volume / 100)

    def total_stake(self):
        """Returns the total stake held among all users."""

        if self.active:
            return sum(t.quantity for t in self.matching_tokens(
                self.outcomes_by_price()[0]))
        else: return 0

    def stake(self, user):
        """Returns the stake held by the user in this proposition."""
        return Tokens.tokens.filter(proposition=self).filter(user=user)

    def resolve(self, outcome):
        """Resolve this proposition in favour of a particular outcome."""

        # A proposition cannot be resolved multiple times.
        if not self.active: return

        # Cancel all outstanding orders.
        for order in Order.objects.filter(proposition=self):
            order.cancel()

        # Mark the proposition as resolved.
        self.outcome = outcome
        self.active = False
        self.save()

        # Give payouts to the winners.
        for tokens in self.matching_tokens(outcome):
            funds = Funds.users.get(tokens.user)
            funds.value += tokens.quantity
            funds.save()

    def matching_tokens(self, outcome):
        """Get all tokens predicting a particular outcome."""

        return (Tokens.tokens

            # Correct affirmative bets.
            .filter(outcome=outcome)
            .filter(affirm=True)
            .union(Tokens.tokens

                # Correct negative bets.
                .filter(proposition=self)
                .exclude(outcome=outcome)
                .filter(affirm=False)))

class Outcome(models.Model):
    """A possible, mutually-exclusive outcome for a proposition."""

    code = models.CharField(max_length=3,
        help_text='The three-letter outcome code.')

    description = models.CharField(max_length=100,
       help_text='The outcome description.')

    colour = ColorField(default="#444466",
        help_text='Display colour for this outcome.')

    proposition = models.ForeignKey('Proposition',
        related_name='proposition', on_delete=models.CASCADE,
        help_text='The proposition to which this outcome belongs.')

    def __str__(self):
        return '[' + self.proposition.code + ':' + self.code + '] ' + self.description

    class Meta: ordering = ['proposition', 'code']

    def bid_price(self, affirm=True):
        """Returns price of top bid."""

        # Find the most recent bid.
        bids = (Order.objects
            .filter(outcome=self)
            .filter(affirm=affirm))

        return bids[0].price if bids else 0

    def ask_price(self, affirm=True):
        """Returns price required to match counter-bid(s)."""

        # Ask price for reverse of same outcome.
        direct_ask = 100 - self.bid_price(not affirm)

        num_outcomes = (Outcome.objects
            .filter(proposition=self.proposition).count())
        # Combined ask price for all other outcomes.
        indirect_ask = 100 if affirm else 100*(num_outcomes-1)

        # Subtract bids for other outcomes from combined ask.
        for outcome in (self.proposition.outcomes()
            .exclude(id=self.id)):

            indirect_ask -= outcome.bid_price(affirm)

        # Return ask price corresponding to the best deal.
        return min(direct_ask, indirect_ask)

    def latest_transaction(self, time=None):
        """Returns the latest transaction which took place."""

        # Use the current time by default.
        if not time: time = datetime.now()

        # Find the latest price.
        return (Price.prices
             .filter(outcome=self)
             .filter(time__lte=time)
             .first())

    def latest_price(self, affirm=True, time=None):
        """Returns the latest price for this outcome."""

        # Get the most recent transaction.
        transaction = self.latest_transaction(time)

        if transaction: price = transaction.price
        # If there are no prices, assume all outcomes are equally likely.
        else: price = round(100 / self.proposition.outcomes().count())

        # Complement the price if it is for the negative.
        return round(price if affirm else 100 - price)

    def average_price(self, affirm=True, start=None, end=None):
        """Determine the average price in the time period."""

        # Use the current time by default.
        if not start: start = datetime.now()
        if not end: end = datetime.now()

        # Find all the prices before the end of the interval.
        prices = Price.prices.filter(outcome=self).filter(time__lte=end)

        if prices:

            # Use the prices in the interval if there are any.
            prices_in_interval = prices.filter(time__gte=start)
            if prices_in_interval: prices = prices_in_interval
            # Otherwise, use most recent interval of prices.
            else: prices = prices.filter(time__gte=prices.first().time - (end-start))

            # Calculate the average price in the interval.
            vol = sum(p.quantity for p in prices)
            price = sum(p.price * p.quantity for p in prices) / vol

        # If there are no prices, assume all outcomes are equally likely.
        else: price = round(100 / self.proposition.outcomes().count())

        # Complement the price if it is for the negative.
        return round(price if affirm else 100 - price)

    def price_change(self, affirm=True, start=None, end=None):
        """Get the amount (cents) by which the price has changed."""

        # Start from yesterday by default.
        if not start: start = datetime.now() - timedelta(days=1)
        # End at the current time by default.
        if not end: end = datetime.now()

        # Return price difference.
        return self.latest_price(affirm, end) - self.latest_price(affirm, start)

    def percent_change(self, affirm=True, start=None, end=None):
        """Get the percentage by which the price has changed."""

        # Start from yesterday by default.
        if not start: start = datetime.now() - timedelta(days=1)

        # Return change as a percentage.
        change = self.price_change(affirm, start, end)
        price = self.latest_price(affirm, start)
        return int(100 * change / price) if price > 0 else 0

    def orders(self, affirm=True):
        """Get all of the orders on this outcome."""
        return Order.objects.filter(outcome=self).filter(affirm=affirm)

    def prices(self, start, end=None, res=20):
        """Get a list of price-time tuples representing price history."""

        if not end: end = datetime.now()
        # Determine the time interval size.
        step = (end - start) / res

        prices = list()

        transaction = self.latest_transaction(start)
        if transaction:
            # Include the latest transaction before start time if present.
            i_price = self.average_price(start=transaction.time-step, end=transaction.time)
            i_time = transaction.time - step/2
            prices.append({'price': i_price, 'time': i_time})
        else:
            # Otherwise, include the initial price.
            created = datetime.combine(self.proposition.creation_date, datetime.min.time())
            prices.append({'price': self.latest_price(time=created), 'time': created})

        for t in range(res):

            # Determine the bounds of the current time interval.
            i_start = start + step*(t-0.5)
            i_middle = start + step*t
            i_end = start + step*(t+0.5)

            # Get average price and trade volume in this interval.
            price = self.average_price(start=i_start, end=i_end)
            vol = self.proposition.trade_volume(start=i_start, end=i_end)

            # Only include the price if there was any volume.
            if vol>0: prices.append({'price': price, 'time': i_middle})

        prices.append({'price': self.latest_price(time=end), 'time': end})
        return prices

class Order(models.Model):
    """A pending order awaiting a matching counter-order."""

    proposition = models.ForeignKey('Proposition', on_delete=models.CASCADE,
        help_text='The proposition on which the order is placed.')

    outcome = models.ForeignKey('Outcome', on_delete=models.CASCADE,
        help_text='The outcome being bet on.')

    affirm = models.BooleanField(
        help_text='Whether the order is for the affirmative.')

    price = models.IntegerField(
        help_text='The price the user is willing to pay per token (c).')

    quantity = models.IntegerField(
        help_text='The number of tokens the user wants to purchase.')

    user = models.ForeignKey(User, on_delete=models.CASCADE,
         help_text='The user who placed the order.')

    time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return ('[' + self.outcome.code + ':' + ("YES" if self.affirm else "NO")
            + '] x' + str(self.quantity) + ' @ ' + str(self.price) + 'c')

    class Meta: ordering = ['proposition', 'outcome', '-price', 'time']

    def match(self):
        """Attempt to match this order with opposing orders."""

        # Continue until all possible matches are made.
        while self.quantity > 0:

            # Find best direct and indirect match.
            direct_match, direct_ask = self.get_direct_match()
            indirect_matches, indirect_ask = self.get_indirect_match()

            # Stop if all other bids are too expensive to be matched.
            if direct_ask > self.price and indirect_ask > self.price: break

            # If trading with the direct match is the best deal.
            elif direct_ask <= indirect_ask:
                self.do_direct_match(direct_match, direct_ask)

            # If trading with the indirect match is the best deal.
            elif indirect_ask < direct_ask:
                self.do_indirect_match(indirect_matches, indirect_ask)

    def get_direct_match(self):
        """Get the best deal on a direct match on this outcome."""

        # Find the best direct match.
        # That is, another order on the opposite side of the same outcome.
        direct_match = (Order.objects
            .filter(outcome=self.outcome)
            .filter(affirm=not self.affirm)
            .filter(price__gte=100 - self.price)
            .first())

        # Determine the direct ask price.
        direct_ask = 100 - (direct_match.price if direct_match else 0)

        return direct_match, direct_ask

    def get_indirect_match(self):
        """Get the best deal on an indirect match across this proposition."""

        # Find the best indirect match.
        # That is, a group of orders on the same side of all the other outcomes.
        indirect_matches = [o for o in (Order.objects
            .filter(outcome=o)
            .filter(affirm=self.affirm)
            .first()
            for o in self.proposition.outcomes()
                .exclude(id=self.outcome.id)) if o]

        # Determine the indirect ask price.
        num_outcomes = self.proposition.outcomes().count()
        indirect_ask = 100 if self.affirm else 100 * (num_outcomes - 1)
        indirect_ask -= sum(o.price for o in indirect_matches)

        return indirect_matches, indirect_ask

    def do_direct_match(self, direct_match, direct_ask):
        """Perform a direct match, a trade on a single outcome."""

        # Determine how many tokens are to be traded.
        trade_quantity = (min(direct_match.quantity, self.quantity)
            if direct_match else self.quantity)

        # Assign tokens to self.
        self.fulfill(trade_quantity)
        Tokens.tokens.add(self.outcome, self.affirm, trade_quantity, self.user)

        # Assign tokens to trade partner.
        if direct_match:
            direct_match.fulfill(trade_quantity)
            Tokens.tokens.add(direct_match.outcome, direct_match.affirm,
                trade_quantity, direct_match.user)

        # Register new price.
        Price.prices.add_direct(self.outcome,
            self.affirm, trade_quantity, direct_ask)

    def do_indirect_match(self, indirect_matches, indirect_ask):
        """Perform an indirect match, a trade across multiple outcomes."""

        # Determine how many tokens are to be traded.
        trade_quantity = min(o.quantity for o in indirect_matches)
        trade_quantity = min(trade_quantity, self.quantity)

        # Assign tokens to self.
        self.fulfill(trade_quantity)
        Tokens.tokens.add(self.outcome, self.affirm, trade_quantity, self.user)

        # Assign tokens to trading partners.
        for match in indirect_matches:
            match.fulfill(trade_quantity)
            Tokens.tokens.add(match.outcome, match.affirm,
                  trade_quantity, match.user)

        # Register new price.
        offers = dict((o.outcome, o.price) for o in indirect_matches)
        offers[self.outcome] = indirect_ask
        volume = (trade_quantity if self.affirm else
            (trade_quantity*(self.proposition.outcomes().count()-1)))
        Price.prices.add_indirect(self.proposition,
            self.affirm, volume, offers)

    def fulfill(self, quantity):
        """Remove some tokens from this order."""

        self.quantity -= quantity
        if self.quantity <= 0: self.delete()
        else: self.save()

    def cancel(self):
        """Cancels the order and refunds the user."""

        # Refund order.
        funds = Funds.users.get(self.user)
        funds.value = float(funds.value) + self.price * self.quantity / 100
        funds.save()

        # Delete order.
        self.delete()

class PriceManager(models.Manager):
    """Manager for maintaining price statistics."""

    def add_direct(self, outcome, affirm, quantity, price):
        """Add a price from a direct trade on only one outcome."""

        prop = outcome.proposition
        if not affirm: price = 100 - price

        # Create a new price entry for this outcome.
        self.create(proposition=prop, outcome=outcome,
            price=price, quantity=quantity)

        # Calculate the sum of the price of each outcome.
        total = sum(o.latest_price() for o in prop.outcomes())

        # Get the existing price of each outcome.
        old_prices = dict((o, o.latest_price()) for o in prop.outcomes())

        # For each other outcome.
        for o in prop.outcomes().exclude(id=outcome.id):

            # Scale price of each other outcome to reach target sum.
            scaled_price = old_prices[o] * (100-price) / (total-price)

            # Create a new price entry for each other outcome.
            self.create(proposition=prop, outcome=o,
                price=scaled_price, quantity=quantity)

    def add_indirect(self, prop, affirm, quantity, prices):
        """Add a price from an indirect trade on a group of outcomes."""

        for o in prop.outcomes():

            # Use actual price if it is included.
            if o in prices: price = prices[o]
            # Otherwise, assume the price is 0.
            else: price = 0
            # Complement price in case of negative.
            if not affirm: price = 100 - price

            # Create a new price for this outcome.
            self.create(proposition=prop, outcome=o,
                price=price, quantity=quantity)

class Price(models.Model):
    """Record of a transaction for statistical purposes."""

    proposition = models.ForeignKey('Proposition', on_delete=models.CASCADE,
        help_text='The proposition which was traded.')

    outcome = models.ForeignKey('Outcome', on_delete=models.CASCADE,
        help_text='The outcome with which this price is associated.')

    price = models.IntegerField(
        help_text='The price which was offered for this outcome.')

    quantity = models.IntegerField(
        help_text='The number of tokens which were traded.')

    time = models.DateTimeField(auto_now=True)

    prices = PriceManager()

    def __str__(self):
        return '[' + self.outcome.code + '] ' + str(self.price) + 'c'

    class Meta: ordering = ['proposition', 'outcome', '-time']

class TokensManager(models.Manager):
    """Manager for giving tokens to a user."""

    def add(self, outcome, affirm, quantity, user):
        """Give a user some tokens."""

        # Get the currently held tokens.
        tokens = self.filter(outcome=outcome).filter(user=user)

        # Create new tokens if none already exist.
        if not tokens.exists():
            self.create(proposition=outcome.proposition, outcome=outcome,
                affirm=affirm, quantity=quantity, user=user)

        # Otherwise, modify the existing tokens.
        else:
            tokens = tokens.get()

            # If tokens are of the same type, they are combined.
            if tokens.affirm == affirm:
                tokens.quantity += quantity
                tokens.save()

            # If tokens are of opposite types, they cancel out.
            else:
                # Provide a refund for cancelled tokens.
                funds = Funds.users.get(user)
                funds.value += min(quantity, tokens.quantity)
                funds.save()

                # Subtract the new quantity from the existing tokens.
                tokens.quantity -= quantity

                # A negative quantity means the type should be flipped.
                if tokens.quantity < 0:
                    tokens.quantity *= -1
                    tokens.affirm ^= True

                # A zero-quantity token should be deleted.
                if tokens.quantity == 0: tokens.delete()
                else: tokens.save()

class Tokens(models.Model):
    """The stake in some proposition currently held by some user."""

    proposition = models.ForeignKey('Proposition', on_delete=models.CASCADE,
        help_text='The propostion in which the stake is held.')

    outcome = models.ForeignKey('Outcome', on_delete=models.CASCADE,
        help_text='The outcome for which the stake is held.')

    affirm = models.BooleanField(
        help_text='Whether the stake is for the affirmative.')

    quantity = models.IntegerField(
        help_text='The amount of stake owned ($).')

    user = models.ForeignKey(User, on_delete=models.CASCADE,
         help_text='The owner of the stake.')

    tokens = TokensManager()

    def __str__(self):
        return ('[' + self.outcome.code + ':' + ("YES" if self.affirm else "NO")
            + '] x' + str(self.quantity) + ' (' + str(self.user) + ')')

    class Meta:
        ordering = ['user', 'proposition']
        verbose_name_plural = 'tokens'

class FundsManager(models.Manager):

    """Provides the funds associated with a user."""
    def get(self, user):
        if not user.is_authenticated: return None
        funds = self.filter(user_id=user.id)
        if funds.exists(): return funds.get()
        else: return self.create(user=user, value=0)

class Funds(models.Model):
    """The current available balance of some user ($AUD)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    value = models.DecimalField(decimal_places=2, max_digits=12,
        help_text='Available funds ($AUD).')

    users = FundsManager()

    def __str__(self): return str(self.user) + ': $' + str(self.value)

    class Meta:
        ordering = ['user']
        verbose_name_plural = 'funds'

    def estimated_value(self):
        """Provides an estimate for the net worth of this user."""

        # Include available funds.
        value = float(self.value)

        # Include stakes, scaled down by latest prices.
        stakes = (Tokens.tokens
            .filter(user_id=self.user.id)
            .filter(proposition__active=True))
        for s in stakes:
            value += s.quantity * s.outcome.latest_price(affirm=s.affirm) / 100

        # Include pending orders.
        for order in Order.objects.filter(user_id=self.user.id):
            value += order.price * order.quantity / 100

        return round(value, 2)