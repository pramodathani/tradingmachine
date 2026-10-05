"""The `indicator_triggered` synthetic order type: an order sent as a limit when one field of the live quote crosses a level.

It compares one value from the quote, not a computed indicator. The most useful is `average_price`, the day's volume-weighted average, because buying when the price comes back below the day's average cannot be written as a native stop. `trigger_price` here is the level, not the order's own trigger. It answers HTTP 202 with an `outcome` of `armed` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer. Once it fires, its limit is held in UBI's virtual order book until the other side of the book reaches it, even if the price moves back, unless `hold_limits` is False.

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

    It compares one value from the quote, not a computed indicator. The most useful is `average_price`, the day's volume-weighted average, because buying when the price comes back below the day's average cannot be written as a native stop. `trigger_price` here is the level, not the order's own trigger. It answers HTTP 202 with an `outcome` of `armed` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer. Once it fires, its limit is held in UBI's virtual order book until the other side of the book reaches it, even if the price moves back, unless `hold_limits` is False.

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
        reduce_only: bool = False,
        hold_limits: bool | None = None,
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
            reduce_only: A bool that is True to have UBI refuse, with HTTP 409, any leg that is not on the closing side of the net position held when it is sent or is bigger than that position.
            hold_limits: A bool that is True to have UBI hold each order that would rest at the broker at a fixed limit price until the other side of the book reaches it, False to send them as they come, or None to let UBI use the type's default.
            dry_run: A bool that is True to have UBI check the order and answer with the `plan` it would run, without recording or sending anything; the answer's `request` is the template as a broker would receive it, which for a stop is not the stop.
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
            reduce_only=reduce_only,
            hold_limits=hold_limits,
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

        Examples:
            Print the settings of a buy sent when the day's average price falls to 13 rupees:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import indicator_triggered

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = indicator_triggered.IndicatorTriggeredOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                trigger_price=13.0,
                limit_price=13.0,
                watch_field="average_price",
            )
            print(order.synthetic_fields())
            ```

            Show a sell sent when the best offer rises to 14.5 rupees:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import indicator_triggered

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = indicator_triggered.IndicatorTriggeredOrder(
                share,
                transaction_type="sell",
                product="mis",
                order_type="limit",
                quantity=1,
                trigger_price=14.5,
                limit_price=14.45,
                watch_field="best_offer",
                trigger_direction="at_or_above",
            )
            print(order.trigger_level)
            print(order.synthetic)
            ```
        """
        return {
            "trigger_price": self.trigger_level,
            "limit_price": self.limit_price,
            "watch_field": self.watch_field,
            "trigger_direction": self.trigger_direction,
        }
