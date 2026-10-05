"""The `underlying_peg` synthetic order type: a resting limit whose price moves by delta times another instrument's move, such as an option bid following the index.

This is pegged-to-stock or delta-pegged, the Atlas's G6. The order is placed at the template's `price`, and UBI then keeps its price at that price plus `delta` times the watched instrument's move since it was placed, rounded to the tick, kept between `lowest_price` and `highest_price`, and changed only once it has moved at least `step_ticks`. The order's own book is never read, which matters on a far strike where one order moves the premium. The template must be a `limit` order with a price, and changing the price yourself restarts the peg from your price and the watched instrument's price at that moment. UBI keeps the watched price the peg measures from as `watched_start` in the part's `pricing_memory`, which the order's `parent` shows. `lowest_price` and `highest_price` must each be a whole number of ticks, or UBI refuses the order with HTTP 400.

Typical usage example:

  order = underlying_peg.UnderlyingPegOrder(
      nifty_call,
      transaction_type="buy",
      product="nrml",
      order_type="limit",
      quantity=75,
      price=120.0,
      watch_instrument=nifty,
      delta=0.5,
      step_ticks=4,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class UnderlyingPegOrder(synthetic_order.SyntheticOrder):
    """A resting limit whose price moves by delta times another instrument's move, such as an option bid following the index.

    This is pegged-to-stock or delta-pegged, the Atlas's G6. The order is placed at the template's `price`, and UBI then keeps its price at that price plus `delta` times the watched instrument's move since it was placed, rounded to the tick, kept between `lowest_price` and `highest_price`, and changed only once it has moved at least `step_ticks`. The order's own book is never read, which matters on a far strike where one order moves the premium. The template must be a `limit` order with a price, and changing the price yourself restarts the peg from your price and the watched instrument's price at that moment. UBI keeps the watched price the peg measures from as `watched_start` in the part's `pricing_memory`, which the order's `parent` shows. `lowest_price` and `highest_price` must each be a whole number of ticks, or UBI refuses the order with HTTP 400.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        watch_instrument: The instruments.Instrument whose price the order follows, usually the underlying, and not the traded instrument itself.
        delta: The float number of rupees the order's price moves per rupee the watched instrument moves, negative for a put.
        lowest_price: The float lowest price in rupees the order is moved to, above zero, or None for no floor.
        highest_price: The float highest price in rupees the order is moved to, above zero and not below `lowest_price`, or None for no ceiling.
        step_ticks: The int smallest move in ticks worth a modification, at least 1, or None to let UBI use 1.
    """

    SYNTHETIC_TYPE = "underlying_peg"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        watch_instrument: instruments.Instrument,
        delta: float,
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
        lowest_price: float | None = None,
        highest_price: float | None = None,
        step_ticks: int | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            watch_instrument: The instruments.Instrument whose price the order follows, usually the underlying, and not the traded instrument itself.
            delta: The float number of rupees the order's price moves per rupee the watched instrument moves, negative for a put.
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
            dry_run: A bool that is True to have UBI check the order and answer with the `plan` it would run, without recording or sending anything; the answer's `request` is the template as a broker would receive it, which for a stop is not the stop.
            lowest_price: The float lowest price in rupees the order is moved to, above zero, or None for no floor.
            highest_price: The float highest price in rupees the order is moved to, above zero and not below `lowest_price`, or None for no ceiling.
            step_ticks: The int smallest move in ticks worth a modification, at least 1, or None to let UBI use 1.

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
        self.watch_instrument = watch_instrument
        self.delta = delta
        self.lowest_price = lowest_price
        self.highest_price = highest_price
        self.step_ticks = step_ticks

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "watch_instrument_id": self.watch_instrument.instrument_id,
            "delta": self.delta,
            "lowest_price": self.lowest_price,
            "highest_price": self.highest_price,
            "step_ticks": self.step_ticks,
        }
