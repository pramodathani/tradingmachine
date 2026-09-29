"""Value a dollar-rupee put nearest the money with Black-76.

A currency option is priced off the future on the same pair that expires first on or after it. The program picks the USDINR put nearest that future's rate on the soonest expiry after today, and prints its premium, the future it is priced off, and its implied volatility and greeks.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency_option/usdinr_option_valuation.py
"""

import datetime

from tradingmachine.assets import currencies


class DollarRupeeOptionValuation:
    """A valuation of the put nearest the money on one currency pair.

    Attributes:
        underlying_symbol: The str symbol of the pair, such as `USDINR`.
    """

    def __init__(self, underlying_symbol: str = "USDINR"):
        """Stores the pair whose option to value.

        Args:
            underlying_symbol: The str symbol of the pair.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Chooses the option, builds it and prints its valuation.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.CurrencyOptionError: UBI has no such option.
            tradingmachine.assets.exceptions.UnderlyingError: The option's future cannot be found.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiries = currencies.CurrencyOption.expiries(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        if not expiries:
            print(f"No options are listed on {self.underlying_symbol}.")
            return
        expiry_date = expiries[0]
        today = datetime.date.today()
        for expiry in expiries:
            if expiry > today:
                expiry_date = expiry
                break
        strikes = currencies.CurrencyOption.strikes(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )
        probe = currencies.CurrencyOption(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
            strike_price=strikes[0],
            option_type="PE",
        )
        future = probe.underlying
        future_rate = future.last_price
        strike_price = strikes[0]
        for strike in strikes:
            if abs(strike - future_rate) < abs(strike_price - future_rate):
                strike_price = strike
        option = currencies.CurrencyOption(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
            strike_price=strike_price,
            option_type="PE",
            underlying=future,
        )
        print(f"Put at {strike_price} expiring {option.expiry_date}")
        print(f"Priced off the future expiring {future.expiry_date} at {future_rate}")
        print(f"Premium: {option.last_price}")
        print(f"Breakeven rate: {option.breakeven_price}")
        greeks = option.greeks()
        if greeks is None:
            print("No greeks, because the prices needed are not known.")
            return
        print(f"Model: {greeks['model']}")
        print(f"Implied volatility: {greeks['volatility']:.1%}")
        print(f"Delta: {greeks['delta']:.3f}")
        print(f"Vega per point of volatility: {greeks['vega']:.4f}")


if __name__ == "__main__":
    DollarRupeeOptionValuation().run()
