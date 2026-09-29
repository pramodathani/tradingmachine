"""The `attached_hedge` synthetic order type: an entry whose fills are hedged in another instrument as they happen, by a ratio or by an option's delta.

This is the Atlas's G14. After each fill, UBI works out the hedge as minus the ratio times everything filled so far, in units of the hedge instrument, rounded to its nearest whole lot, and sends a new hedge order for the whole lots still missing, so no resting order is resized. A positive ratio hedges on the opposite side, so a bought stock is hedged by a sold future, and a negative one hedges on the same side. Give exactly one of `ratio`, a fixed number of hedge units per filled unit such as a beta, or `delta_volatility`, which sizes the hedge by the option's Black-76 delta at that volatility and needs the entry to be an option. Each hedge goes to the entry's broker as a limit two ticks past the hedge instrument's other side.

Typical usage example:

  order = attached_hedge.AttachedHedgeOrder(
      share,
      transaction_type="buy",
      product="nrml",
      order_type="limit",
      quantity=1000,
      price=1000.0,
      hedge_instrument=share_future,
      ratio=1.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class AttachedHedgeOrder(synthetic_order.SyntheticOrder):
    """An entry whose fills are hedged in another instrument as they happen, by a ratio or by an option's delta.

    This is the Atlas's G14. After each fill, UBI works out the hedge as minus the ratio times everything filled so far, in units of the hedge instrument, rounded to its nearest whole lot, and sends a new hedge order for the whole lots still missing, so no resting order is resized. A positive ratio hedges on the opposite side, so a bought stock is hedged by a sold future, and a negative one hedges on the same side. Give exactly one of `ratio`, a fixed number of hedge units per filled unit such as a beta, or `delta_volatility`, which sizes the hedge by the option's Black-76 delta at that volatility and needs the entry to be an option. Each hedge goes to the entry's broker as a limit two ticks past the hedge instrument's other side.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        hedge_instrument: The instruments.Instrument to hedge in, which is not the entry's own.
        ratio: The float number of hedge units per filled unit, not zero, or None when `delta_volatility` sizes the hedge.
        delta_volatility: The float volatility as a percentage above zero at which the option's delta is worked out, or None when `ratio` sizes the hedge.
    """

    SYNTHETIC_TYPE = "attached_hedge"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        hedge_instrument: instruments.Instrument,
        price: float | None = None,
        trigger_price: float | None = None,
        validity: str | None = None,
        disclosed_quantity: int | None = None,
        after_market: bool = False,
        tag: str | None = None,
        price_reference: dict | None = None,
        quantity_reference: dict | None = None,
        closes_position: bool = False,
        reduce_only: bool = False,
        dry_run: bool = False,
        ratio: float | None = None,
        delta_volatility: float | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            hedge_instrument: The instruments.Instrument to hedge in, which is not the entry's own.
            price: The float limit price in rupees, or None for an order type that takes no price or when a price reference supplies it.
            trigger_price: The float trigger price in rupees of the order itself, or None for an order type that takes no trigger.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            disclosed_quantity: The int quantity to show on the exchange, or None to disclose the whole order.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.
            price_reference: A dict describing the price for UBI to work out, such as `{"kind": "mid"}`, or None.
            quantity_reference: A dict describing the quantity for UBI to work out, such as `{"kind": "liquidate_position"}`, or None.
            closes_position: A bool that is True when every order this type sends closes a position, so it may use the share of a broker's daily order cap kept for exits.
            reduce_only: A bool that is True to have UBI refuse, with HTTP 409, any leg that is not on the closing side of the net position held when it is sent or is bigger than that position.
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
            ratio: The float number of hedge units per filled unit, not zero, or None when `delta_volatility` sizes the hedge.
            delta_volatility: The float volatility as a percentage above zero at which the option's delta is worked out, or None when `ratio` sizes the hedge.

        Raises:
            Nothing.
        """
        super().__init__(
            instrument,
            transaction_type=transaction_type,
            product=product,
            order_type=order_type,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            validity=validity,
            disclosed_quantity=disclosed_quantity,
            after_market=after_market,
            tag=tag,
            price_reference=price_reference,
            quantity_reference=quantity_reference,
            closes_position=closes_position,
            reduce_only=reduce_only,
            dry_run=dry_run,
        )
        self.hedge_instrument = hedge_instrument
        self.ratio = ratio
        self.delta_volatility = delta_volatility

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.

        Examples:
            Print the settings of a buy in one share hedged one for one in another:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import attached_hedge

            share = equities.Equity(exchange="nse", symbol="IDEA")
            second_share = equities.Equity(exchange="nse", symbol="YESBANK")
            order = attached_hedge.AttachedHedgeOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
                hedge_instrument=second_share,
                ratio=1.0,
            )
            print(order.synthetic_fields())
            ```

            Show that a negative ratio, which hedges on the same side, is sent as it is given:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import attached_hedge

            share = equities.Equity(exchange="nse", symbol="IDEA")
            second_share = equities.Equity(exchange="nse", symbol="YESBANK")
            order = attached_hedge.AttachedHedgeOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
                hedge_instrument=second_share,
                ratio=-0.5,
            )
            print(order.synthetic)
            ```
        """
        return {
            "hedge_instrument_id": self.hedge_instrument.instrument_id,
            "ratio": self.ratio,
            "delta_volatility": self.delta_volatility,
        }
