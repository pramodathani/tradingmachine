"""The Black-Scholes model, which prices a European option and measures how its price responds to change.

`BlackScholes` holds one option's inputs and reports its fair price and its five greeks as properties. Its `implied_volatility` class method works the other way round, finding the volatility at which the model reproduces a premium seen in the market. `tradingmachine.assets.instruments.Option` uses both for its `implied_volatility` and `greeks` methods, and they can be used on their own with any figures.

The model assumes no dividends and a European option, one exercised only at expiry. Theta is given per calendar day, and vega and rho per percentage point, which is how brokers' option chains show them.

Typical usage example:

  model = option_pricing.BlackScholes(
      underlying_price=24000.0,
      strike_price=24100.0,
      years_to_expiry=7 / 365,
      risk_free_rate=0.065,
      volatility=0.12,
      is_call=True,
  )
  fair_price = model.price
  delta = model.delta

  volatility = option_pricing.BlackScholes.implied_volatility(
      premium=150.0,
      underlying_price=24000.0,
      strike_price=24100.0,
      years_to_expiry=7 / 365,
      risk_free_rate=0.065,
      is_call=True,
  )
"""

import math

DEFAULT_RISK_FREE_RATE = 0.065

LOWEST_VOLATILITY = 0.0001

HIGHEST_VOLATILITY = 5.0

SEARCH_STEPS = 100

DAYS_PER_YEAR = 365

PERCENT = 100


class BlackScholes:
    """One European option priced by the Black-Scholes model without dividends.

    Attributes:
        underlying_price: The float price of the underlying.
        strike_price: The float strike price of the option.
        years_to_expiry: The float time left until expiry, in years.
        risk_free_rate: The float annual risk-free interest rate, continuously compounded, such as 0.065 for 6.5 per cent.
        volatility: The float annual volatility of the underlying, such as 0.12 for 12 per cent.
        is_call: A bool that is True for a call and False for a put.
    """

    def __init__(
        self,
        underlying_price: float,
        strike_price: float,
        years_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        is_call: bool,
    ):
        """Keeps the option's inputs after checking that the model can use them.

        Args:
            underlying_price: The float price of the underlying, above zero.
            strike_price: The float strike price of the option, above zero.
            years_to_expiry: The float time left until expiry in years, above zero.
            risk_free_rate: The float annual risk-free interest rate, continuously compounded.
            volatility: The float annual volatility of the underlying, above zero.
            is_call: A bool that is True for a call and False for a put.

        Raises:
            ValueError: The underlying price, strike price, years to expiry or volatility is not above zero.
        """
        if underlying_price <= 0:
            raise ValueError(
                f"The underlying price must be above zero: {underlying_price=}"
            )
        if strike_price <= 0:
            raise ValueError(f"The strike price must be above zero: {strike_price=}")
        if years_to_expiry <= 0:
            raise ValueError(
                f"The time to expiry must be above zero: {years_to_expiry=}"
            )
        if volatility <= 0:
            raise ValueError(f"The volatility must be above zero: {volatility=}")
        self.underlying_price = underlying_price
        self.strike_price = strike_price
        self.years_to_expiry = years_to_expiry
        self.risk_free_rate = risk_free_rate
        self.volatility = volatility
        self.is_call = is_call

    @classmethod
    def implied_volatility(
        cls,
        premium: float,
        underlying_price: float,
        strike_price: float,
        years_to_expiry: float,
        risk_free_rate: float,
        is_call: bool,
    ) -> float | None:
        """Finds the volatility at which the model's price equals a premium.

        The search halves the range from `LOWEST_VOLATILITY` to `HIGHEST_VOLATILITY` for `SEARCH_STEPS` rounds, which is far finer than any premium's tick. A premium outside the prices the model gives at the two ends of that range has no volatility to find, which happens when the premium is below the option's discounted intrinsic value or implausibly high.

        Args:
            premium: The float price the option trades at.
            underlying_price: The float price of the underlying, above zero.
            strike_price: The float strike price of the option, above zero.
            years_to_expiry: The float time left until expiry in years, above zero.
            risk_free_rate: The float annual risk-free interest rate, continuously compounded.
            is_call: A bool that is True for a call and False for a put.

        Returns:
            The float annual volatility, such as 0.12 for 12 per cent, or None when the premium is not above zero or lies outside the prices the model can give.

        Raises:
            ValueError: The underlying price, strike price or years to expiry is not above zero.
        """
        if premium <= 0:
            return None
        lowest_price = cls(
            underlying_price,
            strike_price,
            years_to_expiry,
            risk_free_rate,
            LOWEST_VOLATILITY,
            is_call,
        ).price
        highest_price = cls(
            underlying_price,
            strike_price,
            years_to_expiry,
            risk_free_rate,
            HIGHEST_VOLATILITY,
            is_call,
        ).price
        if premium < lowest_price or premium > highest_price:
            return None
        low_volatility = LOWEST_VOLATILITY
        high_volatility = HIGHEST_VOLATILITY
        for _ in range(SEARCH_STEPS):
            middle_volatility = (low_volatility + high_volatility) / 2
            middle_price = cls(
                underlying_price,
                strike_price,
                years_to_expiry,
                risk_free_rate,
                middle_volatility,
                is_call,
            ).price
            if middle_price > premium:
                high_volatility = middle_volatility
            else:
                low_volatility = middle_volatility
        return (low_volatility + high_volatility) / 2

    @property
    def price(self) -> float:
        """The option's fair price by the model.

        Returns:
            The float price, in the same units as the underlying price.

        Raises:
            Nothing.
        """
        first_distance = self._first_distance()
        second_distance = self._second_distance()
        discounted_strike = self._discounted_strike()
        if self.is_call:
            return self.underlying_price * self._normal_cumulative(
                first_distance
            ) - discounted_strike * self._normal_cumulative(second_distance)
        return discounted_strike * self._normal_cumulative(
            -second_distance
        ) - self.underlying_price * self._normal_cumulative(-first_distance)

    @property
    def delta(self) -> float:
        """How much the option's price moves for a one-unit move in the underlying.

        Returns:
            The float delta, between 0 and 1 for a call and between -1 and 0 for a put.

        Raises:
            Nothing.
        """
        cumulative = self._normal_cumulative(self._first_distance())
        if self.is_call:
            return cumulative
        return cumulative - 1

    @property
    def gamma(self) -> float:
        """How much the delta moves for a one-unit move in the underlying, the same for a call and a put.

        Returns:
            The float gamma.

        Raises:
            Nothing.
        """
        density = self._normal_density(self._first_distance())
        return density / (
            self.underlying_price * self.volatility * math.sqrt(self.years_to_expiry)
        )

    @property
    def theta(self) -> float:
        """How much the option's price changes as one calendar day passes.

        Returns:
            The float theta per calendar day, usually negative, because an option loses value as time runs out.

        Raises:
            Nothing.
        """
        density = self._normal_density(self._first_distance())
        time_decay = -(self.underlying_price * density * self.volatility) / (
            2 * math.sqrt(self.years_to_expiry)
        )
        second_distance = self._second_distance()
        discounted_strike = self._discounted_strike()
        if self.is_call:
            interest = (
                self.risk_free_rate
                * discounted_strike
                * self._normal_cumulative(second_distance)
            )
            annual_theta = time_decay - interest
        else:
            interest = (
                self.risk_free_rate
                * discounted_strike
                * self._normal_cumulative(-second_distance)
            )
            annual_theta = time_decay + interest
        return annual_theta / DAYS_PER_YEAR

    @property
    def vega(self) -> float:
        """How much the option's price moves when volatility rises by one percentage point, the same for a call and a put.

        Returns:
            The float vega per percentage point of volatility.

        Raises:
            Nothing.
        """
        density = self._normal_density(self._first_distance())
        annual_vega = self.underlying_price * density * math.sqrt(self.years_to_expiry)
        return annual_vega / PERCENT

    @property
    def rho(self) -> float:
        """How much the option's price moves when the risk-free rate rises by one percentage point.

        Returns:
            The float rho per percentage point of the rate, positive for a call and negative for a put.

        Raises:
            Nothing.
        """
        second_distance = self._second_distance()
        discounted_strike = self._discounted_strike()
        if self.is_call:
            annual_rho = (
                self.years_to_expiry
                * discounted_strike
                * self._normal_cumulative(second_distance)
            )
        else:
            annual_rho = (
                -self.years_to_expiry
                * discounted_strike
                * self._normal_cumulative(-second_distance)
            )
        return annual_rho / PERCENT

    def _first_distance(self) -> float:
        """Works out the model's d1, the standardised distance of the underlying from the strike.

        Returns:
            The float d1.

        Raises:
            Nothing.
        """
        spread = self.volatility * math.sqrt(self.years_to_expiry)
        drift = (
            self.risk_free_rate + self.volatility * self.volatility / 2
        ) * self.years_to_expiry
        return (math.log(self.underlying_price / self.strike_price) + drift) / spread

    def _second_distance(self) -> float:
        """Works out the model's d2, which is d1 less the volatility over the option's life.

        Returns:
            The float d2.

        Raises:
            Nothing.
        """
        spread = self.volatility * math.sqrt(self.years_to_expiry)
        return self._first_distance() - spread

    def _discounted_strike(self) -> float:
        """Works out the strike price discounted back from expiry to today.

        Returns:
            The float discounted strike price.

        Raises:
            Nothing.
        """
        discount = math.exp(-self.risk_free_rate * self.years_to_expiry)
        return self.strike_price * discount

    @staticmethod
    def _normal_cumulative(value: float) -> float:
        """Works out the standard normal distribution's cumulative probability at a value.

        Args:
            value: The float point to evaluate at.

        Returns:
            The float probability that a standard normal variable is at most value.

        Raises:
            Nothing.
        """
        return (1 + math.erf(value / math.sqrt(2))) / 2

    @staticmethod
    def _normal_density(value: float) -> float:
        """Works out the standard normal distribution's density at a value.

        Args:
            value: The float point to evaluate at.

        Returns:
            The float density.

        Raises:
            Nothing.
        """
        return math.exp(-value * value / 2) / math.sqrt(2 * math.pi)
