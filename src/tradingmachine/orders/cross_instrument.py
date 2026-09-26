"""The `cross_instrument` synthetic order type: a limit-if-touched order whose trigger watches the last traded price of a different instrument.

It lets an option be exited when the index crosses a level rather than when the option's own premium spikes in a thin book. A native stop can only watch its own instrument, so this has to run in UBI. UBI does not check that the two instruments are related. `trigger_price` here is the level on the watched instrument, not the order's own trigger. It answers HTTP 202 with an `outcome` of `armed` or `scheduled` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer.

Typical usage example:

  order = cross_instrument.CrossInstrumentOrder(
      share,
      transaction_type="sell",
      product="nrml",
      order_type="limit",
      quantity=75,
      price=80.0,
      watch_instrument=nifty,
      trigger_price=24800.0,
      trigger_direction="at_or_below",
      limit_price=80.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class CrossInstrumentOrder(synthetic_order.SyntheticOrder):
    """A limit-if-touched order whose trigger watches the last traded price of a different instrument.

    It lets an option be exited when the index crosses a level rather than when the option's own premium spikes in a thin book. A native stop can only watch its own instrument, so this has to run in UBI. UBI does not check that the two instruments are related. `trigger_price` here is the level on the watched instrument, not the order's own trigger. It answers HTTP 202 with an `outcome` of `armed` or `scheduled` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        watch_instrument: The instruments.Instrument whose last traded price is watched, which may be an index.
        trigger_level: The float level in rupees on the watched instrument that fires the order. Above zero.
        limit_price: The float limit price in rupees of the order sent. Above zero.
        trigger_direction: The str direction, `at_or_above` or `at_or_below`, or None to let a buy wait for a fall and a sell for a rise.
    """

    SYNTHETIC_TYPE = "cross_instrument"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        watch_instrument: instruments.Instrument,
        trigger_price: float,
        limit_price: float,
        price: float | None = None,
        validity: str | None = None,
        disclosed_quantity: int | None = None,
        after_market: bool = False,
        tag: str | None = None,
        price_reference: dict | None = None,
        quantity_reference: dict | None = None,
        closes_position: bool = False,
        dry_run: bool = False,
        trigger_direction: str | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            watch_instrument: The instruments.Instrument whose last traded price is watched, which may be an index.
            trigger_price: The float level in rupees on the watched instrument that fires the order. Above zero.
            limit_price: The float limit price in rupees of the order sent. Above zero.
            price: The float limit price in rupees, or None for an order type that takes no price or when a price reference supplies it.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            disclosed_quantity: The int quantity to show on the exchange, or None to disclose the whole order.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.
            price_reference: A dict describing the price for UBI to work out, such as `{"kind": "mid"}`, or None.
            quantity_reference: A dict describing the quantity for UBI to work out, such as `{"kind": "liquidate_position"}`, or None.
            closes_position: A bool that is True when every order this type sends closes a position, so it may use the share of a broker's daily order cap kept for exits.
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
            trigger_direction: The str direction, `at_or_above` or `at_or_below`, or None to let a buy wait for a fall and a sell for a rise.

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
            trigger_price=None,
            validity=validity,
            disclosed_quantity=disclosed_quantity,
            after_market=after_market,
            tag=tag,
            price_reference=price_reference,
            quantity_reference=quantity_reference,
            closes_position=closes_position,
            dry_run=dry_run,
        )
        self.watch_instrument = watch_instrument
        self.trigger_level = trigger_price
        self.limit_price = limit_price
        self.trigger_direction = trigger_direction

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "watch_instrument_id": self.watch_instrument.instrument_id,
            "trigger_price": self.trigger_level,
            "limit_price": self.limit_price,
            "trigger_direction": self.trigger_direction,
        }
