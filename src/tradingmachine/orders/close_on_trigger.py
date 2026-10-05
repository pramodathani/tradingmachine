"""The `close_on_trigger` synthetic order type: a level that, when reached, cancels every order on the instrument to free margin and then closes the whole position.

This is the Atlas's G12, a stop whose exit is not refused for margin. When the level is reached, UBI first cancels every order resting on the instrument at every broker, including orders placed outside UBI, because pending orders hold margin, and then closes the whole net position held in the instrument and the template's product with a limit two ticks past the other side's best price. It closes what is held when it fires, so the template's `quantity` is not used, and when nothing is held it completes without sending an order. Set `transaction_type` to the side that opened the position, so a long position is protected by asking for `buy`, which fires when the price falls to the level. `trigger_price` here is that level, not the order's own trigger. With `trigger_on`, the level is compared with the bid, the offer or the midpoint instead of the last trade, or must be reached on two ticks in a row (`double_last`) or for `hold_seconds` (`held`), so a single stray trade does not fire it. It answers HTTP 202 with an `outcome` of `armed` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer. Only orders on the template's product are cancelled, since orders on another product belong to another position, and a change to the order's price or quantity while it waits is refused with HTTP 409.

Typical usage example:

  order = close_on_trigger.CloseOnTriggerOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=995.0,
      trigger_price=995.0,
      trigger_on="held",
      hold_seconds=3.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class CloseOnTriggerOrder(synthetic_order.SyntheticOrder):
    """A level that, when reached, cancels every order on the instrument to free margin and then closes the whole position.

    This is the Atlas's G12, a stop whose exit is not refused for margin. When the level is reached, UBI first cancels every order resting on the instrument at every broker, including orders placed outside UBI, because pending orders hold margin, and then closes the whole net position held in the instrument and the template's product with a limit two ticks past the other side's best price. It closes what is held when it fires, so the template's `quantity` is not used, and when nothing is held it completes without sending an order. Set `transaction_type` to the side that opened the position, so a long position is protected by asking for `buy`, which fires when the price falls to the level. `trigger_price` here is that level, not the order's own trigger. With `trigger_on`, the level is compared with the bid, the offer or the midpoint instead of the last trade, or must be reached on two ticks in a row (`double_last`) or for `hold_seconds` (`held`), so a single stray trade does not fire it. It answers HTTP 202 with an `outcome` of `armed` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer. Only orders on the template's product are cancelled, since orders on another product belong to another position, and a change to the order's price or quantity while it waits is refused with HTTP 409.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        trigger_level: The float level in rupees that fires the order. Above zero.
        trigger_direction: The str direction, `at_or_above` or `at_or_below`, or None to let a buy wait for a fall and a sell for a rise.
        trigger_on: The str price compared with the level and how it must confirm, `last`, `bid`, `ask`, `mid`, `double_last` or `held`, or None to let UBI use `last`.
        hold_seconds: The float number of seconds the level must stay reached before a `held` trigger fires, which `held` requires, or None.
    """

    SYNTHETIC_TYPE = "close_on_trigger"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        trigger_price: float,
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
            Print the settings that close a long position when the price falls to 12 rupees:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import close_on_trigger

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = close_on_trigger.CloseOnTriggerOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                trigger_price=12.0,
            )
            print(order.synthetic_fields())
            ```

            Show a level that must hold on the bid for ten seconds before it fires:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import close_on_trigger

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = close_on_trigger.CloseOnTriggerOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                trigger_price=12.0,
                trigger_on="held",
                hold_seconds=10,
            )
            print(order.synthetic)
            ```
        """
        return {
            "trigger_price": self.trigger_level,
            "trigger_direction": self.trigger_direction,
            "trigger_on": self.trigger_on,
            "hold_seconds": self.hold_seconds,
        }
