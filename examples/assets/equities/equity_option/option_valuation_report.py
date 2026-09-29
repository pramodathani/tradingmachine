"""Value the share option nearest the money and print its greeks.

The program finds the soonest RELIANCE option expiry after today, picks the call whose strike is closest to the share's price, and prints its premium, its implied volatility and the greeks the Black-Scholes model gives for it.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity_option/option_valuation_report.py
"""

import datetime

from tradingmachine.assets import equities


class ShareOptionValuationReport:
    """A valuation of the call nearest the money on one share.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the option is written on.
    """

    def __init__(self, underlying_symbol: str = "RELIANCE"):
        """Looks the share up in UBI.

        Args:
            underlying_symbol: The str nse symbol of the share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI has no nse share with that symbol.
        """
        self.share = equities.Equity(exchange="nse", symbol=underlying_symbol)

    def next_expiry(self) -> datetime.date:
        """Chooses the soonest option expiry after today.

        Returns:
            The datetime.date of the expiry.

        Raises:
            ValueError: No options are listed on the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        expiries = equities.EquityOption.expiries(
            exchange="nse",
            underlying_symbol=self.share.symbol,
        )
        if not expiries:
            raise ValueError(f"No options are listed on {self.share.symbol}")
        today = datetime.date.today()
        for expiry in expiries:
            if expiry > today:
                return expiry
        return expiries[0]

    def nearest_strike(self, expiry_date: datetime.date) -> float:
        """Finds the listed strike closest to the share's last price.

        Args:
            expiry_date: The datetime.date of the expiry whose strikes to search.

        Returns:
            The float strike price in rupees.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        share_price = self.share.last_price
        strikes = equities.EquityOption.strikes(
            exchange="nse",
            underlying_symbol=self.share.symbol,
            expiry_date=expiry_date,
        )
        nearest = strikes[0]
        for strike in strikes:
            if abs(strike - share_price) < abs(nearest - share_price):
                nearest = strike
        return nearest

    def run(self) -> None:
        """Builds the option and prints its valuation.

        Returns:
            None.

        Raises:
            ValueError: No options are listed on the share.
            tradingmachine.assets.exceptions.EquityOptionError: UBI has no such option.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date = self.next_expiry()
        option = equities.EquityOption(
            exchange="nse",
            underlying_symbol=self.share.symbol,
            expiry_date=expiry_date,
            strike_price=self.nearest_strike(expiry_date),
            option_type="CE",
            underlying=self.share,
        )
        print(
            f"{option.underlying_symbol} {option.strike_price} "
            f"{option.option_type} expiring {option.expiry_date}"
        )
        print(f"Lot size: {option.lot_size} shares")
        print(f"Share price: {option.underlying_price}")
        print(f"Premium: {option.last_price}")
        print(f"Moneyness: {option.moneyness_percent:.2f}%")
        print(f"Intrinsic value: {option.intrinsic_value}")
        print(f"Time value: {option.time_value}")
        print(f"Breakeven price: {option.breakeven_price}")
        print(f"Premium per lot: {option.premium_per_lot}")
        greeks = option.greeks()
        if greeks is None:
            print("The greeks cannot be worked out from the prices available.")
            return
        print(f"Model: {greeks['model']}")
        print(f"Implied volatility: {greeks['volatility']:.1%}")
        print(f"Delta: {greeks['delta']:.3f}")
        print(f"Gamma: {greeks['gamma']:.5f}")
        print(f"Theta per day: {greeks['theta']:.2f}")
        print(f"Vega per point of volatility: {greeks['vega']:.2f}")


if __name__ == "__main__":
    ShareOptionValuationReport().run()
