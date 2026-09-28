"""One instrument in a basket, with its weight or quantity.

A basket that describes an allocation, such as an index or a fund's contents, gives each member a `weight`. A portfolio gives each member a `quantity` and, when it is known, the `average_price` it was bought at. A watchlist gives neither.

Typical usage example:

  infosys = equities.Equity(exchange="nse", symbol="INFY")
  member = basket_member.BasketMember(infosys, weight=0.05)
  held = basket_member.BasketMember(infosys, quantity=10, average_price=1450.0)
"""

import datetime

from tradingmachine.assets import instruments


class BasketMember:
    """One instrument held in a basket.

    Attributes:
        instrument: The tradingmachine.assets.instruments.Instrument this member is.
        weight: The float share of the basket this member is meant to be, in any units such as fractions or percentages because the basket normalises them, or None when the basket is not weighted.
        quantity: The int or float number of units held, negative for a short position, or None when the basket is not counted in units.
        average_price: The float average price in rupees the quantity was bought at, or None when it is not known.
    """

    def __init__(
        self,
        instrument: instruments.Instrument,
        weight: float | None = None,
        quantity: float | None = None,
        average_price: float | None = None,
    ):
        """Initialises the member.

        Args:
            instrument: The tradingmachine.assets.instruments.Instrument this member is.
            weight: The float share of the basket, or None.
            quantity: The int or float number of units held, or None.
            average_price: The float average price in rupees the quantity was bought at, or None.

        Raises:
            Nothing.
        """
        self.instrument = instrument
        self.weight = weight
        self.quantity = quantity
        self.average_price = average_price

    @property
    def label(self) -> str:
        """The str readable name of the member, such as `nse:INFY` or `nse:NIFTY 2026-10-27 25000.0CE`."""
        instrument = self.instrument
        if instrument.symbol is not None:
            return f"{instrument.exchange}:{instrument.symbol}"
        parts = [
            instrument.underlying_symbol,
        ]
        if isinstance(instrument.expiry_date, datetime.date):
            parts.append(instrument.expiry_date.isoformat())
        if instrument.strike_price is not None:
            parts.append(f"{instrument.strike_price}{instrument.option_type}")
        return f"{instrument.exchange}:{' '.join(parts)}"

    def document(self) -> dict:
        """Describes the member as a dict for storing in MongoDB.

        Returns:
            A dict with the instrument's `instrument_id`, `exchange`, `segment`, `symbol`, `underlying_symbol`, `expiry_date`, `strike_price` and `option_type`, and the member's `weight`, `quantity` and `average_price`.

        Raises:
            Nothing.
        """
        instrument = self.instrument
        expiry_date = None
        if isinstance(instrument.expiry_date, datetime.date):
            expiry_date = instrument.expiry_date.isoformat()
        return {
            "instrument_id": instrument.instrument_id,
            "exchange": instrument.exchange,
            "segment": instrument.segment,
            "symbol": instrument.symbol,
            "underlying_symbol": instrument.underlying_symbol,
            "expiry_date": expiry_date,
            "strike_price": instrument.strike_price,
            "option_type": instrument.option_type,
            "weight": self.weight,
            "quantity": self.quantity,
            "average_price": self.average_price,
        }

    def __repr__(self) -> str:
        """Describes the member by its label and whichever of weight and quantity it has.

        Returns:
            A str such as `BasketMember('nse:INFY', weight=0.05)`.

        Raises:
            Nothing.
        """
        described_fields = [
            repr(self.label),
        ]
        if self.weight is not None:
            described_fields.append(f"weight={self.weight!r}")
        if self.quantity is not None:
            described_fields.append(f"quantity={self.quantity!r}")
        if self.average_price is not None:
            described_fields.append(f"average_price={self.average_price!r}")
        return f"BasketMember({', '.join(described_fields)})"
