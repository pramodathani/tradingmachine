"""The `hidden_stop` synthetic order type: a stop kept inside UBI that watches the bid or the offer, with an optional real stop behind it.

Set `transaction_type` to the side that opened the position, so a long position is protected by asking for `buy`. The stop watches the bid when protecting a long and the offer when protecting a short, so a single stray trade does not fire it. It protects nothing while UBI is down, which is what the backstop is for: a real stop-loss limit placed at the broker when the order is armed. `trigger_price` here is the hidden level, not the order's own trigger. It answers HTTP 202 with an `outcome` of `armed` or `scheduled` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer.

Typical usage example:

  order = hidden_stop.HiddenStopOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=990.0,
      trigger_price=990.0,
      backstop_price=980.0,
      backstop_limit_price=978.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class HiddenStopOrder(synthetic_order.SyntheticOrder):
    """A stop kept inside UBI that watches the bid or the offer, with an optional real stop behind it.

    Set `transaction_type` to the side that opened the position, so a long position is protected by asking for `buy`. The stop watches the bid when protecting a long and the offer when protecting a short, so a single stray trade does not fire it. It protects nothing while UBI is down, which is what the backstop is for: a real stop-loss limit placed at the broker when the order is armed. `trigger_price` here is the hidden level, not the order's own trigger. It answers HTTP 202 with an `outcome` of `armed` or `scheduled` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        trigger_level: The float hidden level in rupees.
        backstop_price: The float trigger in rupees of a real stop placed at the broker, given together with `backstop_limit_price`, or None.
        backstop_limit_price: The float limit in rupees of that real stop, or None.
        buffer_ticks: The int number of ticks past the best price to price the exit, or None to let UBI use 2.
        trigger_direction: The str direction, `at_or_above` or `at_or_below`, or None to let UBI work it out from the side.
    """

    SYNTHETIC_TYPE = "hidden_stop"

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
        dry_run: bool = False,
        backstop_price: float | None = None,
        backstop_limit_price: float | None = None,
        buffer_ticks: int | None = None,
        trigger_direction: str | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            trigger_price: The float hidden level in rupees.
            price: The float limit price in rupees, or None for an order type that takes no price or when a price reference supplies it.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            disclosed_quantity: The int quantity to show on the exchange, or None to disclose the whole order.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.
            price_reference: A dict describing the price for UBI to work out, such as `{"kind": "mid"}`, or None.
            quantity_reference: A dict describing the quantity for UBI to work out, such as `{"kind": "liquidate_position"}`, or None.
            closes_position: A bool that is True when every order this type sends closes a position, so it may use the share of a broker's daily order cap kept for exits.
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
            backstop_price: The float trigger in rupees of a real stop placed at the broker, given together with `backstop_limit_price`, or None.
            backstop_limit_price: The float limit in rupees of that real stop, or None.
            buffer_ticks: The int number of ticks past the best price to price the exit, or None to let UBI use 2.
            trigger_direction: The str direction, `at_or_above` or `at_or_below`, or None to let UBI work it out from the side.

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
        self.backstop_price = backstop_price
        self.backstop_limit_price = backstop_limit_price
        self.buffer_ticks = buffer_ticks
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
            "backstop_price": self.backstop_price,
            "backstop_limit_price": self.backstop_limit_price,
            "buffer_ticks": self.buffer_ticks,
            "trigger_direction": self.trigger_direction,
        }
