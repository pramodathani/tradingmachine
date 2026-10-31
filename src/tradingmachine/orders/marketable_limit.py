"""The `marketable_limit` synthetic order type: a market order sent as a limit that follows the other side of the book until it fills.

A market order with a worst price: a limit a few ticks past the other side's best price, moved after that price until it fills, with whatever is left cancelled after a time. UBI sends it as a `limit` priced `buffer_ticks` past the other side's best price, which for a buy is the best offer, so it trades at once against what rests there but never fills far from the price that was showing. On every later tick UBI moves it to `buffer_ticks` past the other side's best price again, through its repricing throttle, and once `fill_within_seconds` have passed since it was placed it cancels whatever has not filled, so the parent ends `completed` with what filled or `cancelled` when nothing did. UBI refuses the order with HTTP 409, and sends nothing, when it cannot be priced as it arrives: when nobody is offering for a buy, nobody is bidding for a sell, no live quote has arrived, or the quote is marked stale. UBI already runs every plain `market` order that names no `synthetic` type and is not an after-market order as this type with its defaults, while its `UNIFIED_BROKER_INTERFACE_API_ORDER_MARKET_AS_LIMIT` switch is on, which it is by default, so this class is needed only to choose a different buffer or time. A `limit` template that names this type is priced from the book in the same way, and its own price is not used. Each move of the resting limit is a modification that counts against the broker's daily order messages. Two settings guard a large order. `maximum_cost_bps` has UBI estimate, just before sending, what filling the whole quantity against the visible book would cost in basis points of the midpoint, and refuse the order with HTTP 409, sending nothing, when that is above the maximum or when the five visible levels do not hold the whole quantity. `reaches_size` sets the limit no nearer than the deepest visible level the unfilled quantity reaches, up to the fifth, so an order bigger than the first levels takes them at once instead of filling in part and chasing the price; a small order keeps `buffer_ticks`. Left as None, each follows a UBI switch that every plain market order follows too, `UNIFIED_BROKER_INTERFACE_API_ORDER_MAXIMUM_COST_BPS`, unset by default so no maximum applies, and `UNIFIED_BROKER_INTERFACE_API_ORDER_MARKET_REACHES_SIZE`, off by default.

Typical usage example:

  order = marketable_limit.MarketableLimitOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="market",
      quantity=10,
      buffer_ticks=0,
      fill_within_seconds=10,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class MarketableLimitOrder(synthetic_order.SyntheticOrder):
    """A market order sent as a limit that follows the other side of the book until it fills.

    A market order with a worst price: a limit a few ticks past the other side's best price, moved after that price until it fills, with whatever is left cancelled after a time. UBI sends it as a `limit` priced `buffer_ticks` past the other side's best price, which for a buy is the best offer, so it trades at once against what rests there but never fills far from the price that was showing. On every later tick UBI moves it to `buffer_ticks` past the other side's best price again, through its repricing throttle, and once `fill_within_seconds` have passed since it was placed it cancels whatever has not filled, so the parent ends `completed` with what filled or `cancelled` when nothing did. UBI refuses the order with HTTP 409, and sends nothing, when it cannot be priced as it arrives: when nobody is offering for a buy, nobody is bidding for a sell, no live quote has arrived, or the quote is marked stale. UBI already runs every plain `market` order that names no `synthetic` type and is not an after-market order as this type with its defaults, while its `UNIFIED_BROKER_INTERFACE_API_ORDER_MARKET_AS_LIMIT` switch is on, which it is by default, so this class is needed only to choose a different buffer or time. A `limit` template that names this type is priced from the book in the same way, and its own price is not used. Each move of the resting limit is a modification that counts against the broker's daily order messages. Two settings guard a large order. `maximum_cost_bps` has UBI estimate, just before sending, what filling the whole quantity against the visible book would cost in basis points of the midpoint, and refuse the order with HTTP 409, sending nothing, when that is above the maximum or when the five visible levels do not hold the whole quantity. `reaches_size` sets the limit no nearer than the deepest visible level the unfilled quantity reaches, up to the fifth, so an order bigger than the first levels takes them at once instead of filling in part and chasing the price; a small order keeps `buffer_ticks`. Left as None, each follows a UBI switch that every plain market order follows too, `UNIFIED_BROKER_INTERFACE_API_ORDER_MAXIMUM_COST_BPS`, unset by default so no maximum applies, and `UNIFIED_BROKER_INTERFACE_API_ORDER_MARKET_REACHES_SIZE`, off by default.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        buffer_ticks: The int number of ticks past the other side's best price the limit sits, at least 0, or None to let UBI use 2.
        fill_within_seconds: The float number of seconds, above zero, the order may work before whatever is left is cancelled, or None to let UBI use 30.
        maximum_cost_bps: The float most, above zero, that crossing the spread may cost in basis points of the midpoint, or None to let UBI use its configured maximum, which is unset by default.
        reaches_size: A bool that is True to set the limit as deep into the visible book as the unfilled quantity needs, up to the fifth level, False to keep it `buffer_ticks` past the best price, or None to let UBI use its configured default, which is False.
    """

    SYNTHETIC_TYPE = "marketable_limit"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
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
        hold_limits: bool | None = None,
        dry_run: bool = False,
        buffer_ticks: int | None = None,
        fill_within_seconds: float | None = None,
        maximum_cost_bps: float | None = None,
        reaches_size: bool | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
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
            hold_limits: A bool that is True to have UBI hold each order that would rest at the broker at a fixed limit price until the other side of the book reaches it, False to send them as they come, or None to let UBI use the type's default.
            dry_run: A bool that is True to have UBI check the order and answer with the `plan` it would run, without recording or sending anything; the answer's `request` is the template as written, so a `market` template still shows as a market order there.
            buffer_ticks: The int number of ticks past the other side's best price the limit sits, at least 0, or None to let UBI use 2.
            fill_within_seconds: The float number of seconds, above zero, the order may work before whatever is left is cancelled, or None to let UBI use 30.
            maximum_cost_bps: The float most, above zero, that crossing the spread may cost in basis points of the midpoint, as UBI estimates it from the visible book just before sending, or None to let UBI use its configured maximum, which is unset by default. Above it, or when the five visible levels do not hold the whole quantity, UBI refuses the order with HTTP 409 and sends nothing.
            reaches_size: A bool that is True to set the limit no nearer than the deepest visible level the unfilled quantity reaches on the other side, up to the fifth, False to keep it `buffer_ticks` past the best price, or None to let UBI use its configured default, which is False.

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
            hold_limits=hold_limits,
            dry_run=dry_run,
        )
        self.buffer_ticks = buffer_ticks
        self.fill_within_seconds = fill_within_seconds
        self.maximum_cost_bps = maximum_cost_bps
        self.reaches_size = reaches_size

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.

        Examples:
            Print the settings of a market buy that works for ten seconds right at the best offer:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import marketable_limit

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = marketable_limit.MarketableLimitOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="market",
                quantity=10,
                buffer_ticks=0,
                fill_within_seconds=10,
            )
            print(order.synthetic_fields())
            ```

            Print the settings of a large market buy that reaches as deep as its size needs but is refused if crossing the spread would cost more than fifteen basis points:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import marketable_limit

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = marketable_limit.MarketableLimitOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="market",
                quantity=5000,
                maximum_cost_bps=15,
                reaches_size=True,
            )
            print(order.synthetic)
            ```
        """
        return {
            "buffer_ticks": self.buffer_ticks,
            "fill_within_seconds": self.fill_within_seconds,
            "maximum_cost_bps": self.maximum_cost_bps,
            "reaches_size": self.reaches_size,
        }
