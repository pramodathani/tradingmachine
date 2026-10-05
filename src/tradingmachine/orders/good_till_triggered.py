"""The `gtt` synthetic order type: a limit-if-touched order that keeps waiting across days until it fires or expires.

Native Indian stops expire at the end of the day, and this is what brokers sell as GTT for multi-day holdings. A gap through the level fires it at the open, and nothing that watches prices can act on a price that never traded. `trigger_price` here is the level, not the order's own trigger. With `trigger_on`, the level is compared with the bid, the offer or the midpoint instead of the last trade, or must be reached on two ticks in a row (`double_last`) or for `hold_seconds` (`held`), so a single stray trade does not fire it. It answers HTTP 202 with an `outcome` of `armed` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer. Once touched, its limit is held in UBI's virtual order book, across days until `valid_days` runs out, until the other side of the book reaches it, unless `hold_limits` is False; a held one therefore does not die at the close as a `day` limit sent at the touch would.

Typical usage example:

  order = good_till_triggered.GoodTillTriggeredOrder(
      share,
      transaction_type="sell",
      product="cnc",
      order_type="limit",
      quantity=10,
      price=951.0,
      trigger_price=950.0,
      limit_price=951.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class GoodTillTriggeredOrder(synthetic_order.SyntheticOrder):
    """A limit-if-touched order that keeps waiting across days until it fires or expires.

    Native Indian stops expire at the end of the day, and this is what brokers sell as GTT for multi-day holdings. A gap through the level fires it at the open, and nothing that watches prices can act on a price that never traded. `trigger_price` here is the level, not the order's own trigger. With `trigger_on`, the level is compared with the bid, the offer or the midpoint instead of the last trade, or must be reached on two ticks in a row (`double_last`) or for `hold_seconds` (`held`), so a single stray trade does not fire it. It answers HTTP 202 with an `outcome` of `armed` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer. Once touched, its limit is held in UBI's virtual order book, across days until `valid_days` runs out, until the other side of the book reaches it, unless `hold_limits` is False; a held one therefore does not die at the close as a `day` limit sent at the touch would.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        trigger_level: The float level in rupees that fires the order. Above zero.
        limit_price: The float limit price in rupees of the order sent. Above zero.
        valid_days: The int number of days to keep waiting, from 1 to 365, or None to let UBI use 30.
        trigger_direction: The str direction, `at_or_above` or `at_or_below`, or None to let a buy wait for a fall and a sell for a rise.
        trigger_on: The str price compared with the level and how it must confirm, `last`, `bid`, `ask`, `mid`, `double_last` or `held`, or None to let UBI use `last`.
        hold_seconds: The float number of seconds the level must stay reached before a `held` trigger fires, which `held` requires, or None.
    """

    SYNTHETIC_TYPE = "gtt"

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
        valid_days: int | None = None,
        trigger_direction: str | None = None,
        trigger_on: str | None = None,
        hold_seconds: float | None = None,
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
            valid_days: The int number of days to keep waiting, from 1 to 365, or None to let UBI use 30.
            trigger_direction: The str direction, `at_or_above` or `at_or_below`, or None to let a buy wait for a fall and a sell for a rise.
            trigger_on: The str price compared with the level and how it must confirm, `last`, `bid`, `ask`, `mid`, `double_last` or `held`, or None to let UBI use `last`.
            hold_seconds: The float number of seconds the level must stay reached before a `held` trigger fires, which `held` requires, or None.

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
        self.valid_days = valid_days
        self.trigger_direction = trigger_direction
        self.trigger_on = trigger_on
        self.hold_seconds = hold_seconds

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.

        Examples:
            Print the settings of a buy that waits up to ninety days for the price to fall to 12 rupees:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import good_till_triggered

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = good_till_triggered.GoodTillTriggeredOrder(
                share,
                transaction_type="buy",
                product="cnc",
                order_type="limit",
                quantity=1,
                trigger_price=12.0,
                limit_price=12.05,
                valid_days=90,
            )
            print(order.synthetic_fields())
            ```

            Show a sell that fires only when the price reaches 16 rupees on two trades in a row:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import good_till_triggered

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = good_till_triggered.GoodTillTriggeredOrder(
                share,
                transaction_type="sell",
                product="cnc",
                order_type="limit",
                quantity=1,
                trigger_price=16.0,
                limit_price=15.95,
                trigger_on="double_last",
            )
            print(order.trigger_level)
            print(order.synthetic)
            ```
        """
        return {
            "trigger_price": self.trigger_level,
            "limit_price": self.limit_price,
            "valid_days": self.valid_days,
            "trigger_direction": self.trigger_direction,
            "trigger_on": self.trigger_on,
            "hold_seconds": self.hold_seconds,
        }
