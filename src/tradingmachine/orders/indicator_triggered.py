"""The `indicator_triggered` synthetic order type: an order sent as a limit when one field of the live quote crosses a level.

It compares one value from the quote, not a computed indicator. The most useful is `average_price`, the day's volume-weighted average, because buying when the price comes back below the day's average cannot be written as a native stop. `trigger_price` here is the level, not the order's own trigger. It answers HTTP 202 with an `outcome` of `armed` or `scheduled` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer.

Typical usage example:

  order = indicator_triggered.IndicatorTriggeredOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=999.5,
      trigger_price=999.8,
      limit_price=999.5,
      watch_field="average_price",
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class IndicatorTriggeredOrder(synthetic_order.SyntheticOrder):
    """An order sent as a limit when one field of the live quote crosses a level.

    It compares one value from the quote, not a computed indicator. The most useful is `average_price`, the day's volume-weighted average, because buying when the price comes back below the day's average cannot be written as a native stop. `trigger_price` here is the level, not the order's own trigger. It answers HTTP 202 with an `outcome` of `armed` or `scheduled` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        trigger_level: The float level in rupees that fires the order. Above zero.
        limit_price: The float limit price in rupees of the order sent. Above zero.
        watch_field: The str quote field watched, `last_price`, `average_price`, `previous_close`, `best_bid`, `best_offer` or `mid`, or None to let UBI use `last_price`.
        trigger_direction: The str direction, `at_or_above` or `at_or_below`, or None to let a buy wait for a fall and a sell for a rise.
    """

    SYNTHETIC_TYPE = "indicator_triggered"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
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
        watch_field: str | None = None,
        trigger_direction: str | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            trigger_price: The float level in rupees that fires the order. Above zero.
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
            watch_field: The str quote field watched, `last_price`, `average_price`, `previous_close`, `best_bid`, `best_offer` or `mid`, or None to let UBI use `last_price`.
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
        self.trigger_level = trigger_price
        self.limit_price = limit_price
        self.watch_field = watch_field
        self.trigger_direction = trigger_direction

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "trigger_price": self.trigger_level,
            "limit_price": self.limit_price,
            "watch_field": self.watch_field,
            "trigger_direction": self.trigger_direction,
        }
