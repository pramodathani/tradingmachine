"""The `stepped_stop` synthetic order type: a native stop moved to set levels at set profits, and switched to trailing at the last.

This is an adjustable stop, the Atlas's G8. The stop-limit is placed at `stop_price`, and each rule names a `gain`, the profit in points from `entry_price` that sets it off, and either a `stop_at_gain`, where to move the stop measured from `entry_price`, or a `trail_points`, which starts the stop trailing as a `TrailingStopOrder` does. A market that jumps past several gains applies them all in one modification, a stop is only ever moved in the position's favour, and a trailing rule must be the last. Set `transaction_type` to the side that opened the position, so a long position is protected by asking for `buy`.

Typical usage example:

  order = stepped_stop.SteppedStopOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=1000.0,
      entry_price=1000.0,
      stop_price=990.0,
      stop_limit_offset=2.0,
      rules=[{"gain": 20, "stop_at_gain": 0}, {"gain": 60, "trail_points": 25}],
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class SteppedStopOrder(synthetic_order.SyntheticOrder):
    """A native stop moved to set levels at set profits, and switched to trailing at the last.

    This is an adjustable stop, the Atlas's G8. The stop-limit is placed at `stop_price`, and each rule names a `gain`, the profit in points from `entry_price` that sets it off, and either a `stop_at_gain`, where to move the stop measured from `entry_price`, or a `trail_points`, which starts the stop trailing as a `TrailingStopOrder` does. A market that jumps past several gains applies them all in one modification, a stop is only ever moved in the position's favour, and a trailing rule must be the last. Set `transaction_type` to the side that opened the position, so a long position is protected by asking for `buy`.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        entry_price: The float price in rupees the position was opened at, which every gain is measured from. Above zero.
        stop_price: The float trigger price in rupees the stop starts at. Above zero.
        stop_limit_offset: The float distance in rupees past the trigger that the stop's limit sits. Above zero.
        rules: The list of 1 to 20 dict rules, each with a `gain` above zero and larger than the one before and exactly one of `stop_at_gain`, a number that may be negative to keep some risk, or `trail_points`, above zero, which only the last rule may have.
        step_ticks: The int number of ticks the trigger must be able to move before it is moved once trailing, or None to let UBI use 1.
    """

    SYNTHETIC_TYPE = "stepped_stop"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        entry_price: float,
        stop_price: float,
        stop_limit_offset: float,
        rules: list[dict],
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
        step_ticks: int | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            entry_price: The float price in rupees the position was opened at, which every gain is measured from. Above zero.
            stop_price: The float trigger price in rupees the stop starts at. Above zero.
            stop_limit_offset: The float distance in rupees past the trigger that the stop's limit sits. Above zero.
            rules: The list of 1 to 20 dict rules, each with a `gain` above zero and larger than the one before and exactly one of `stop_at_gain`, a number that may be negative to keep some risk, or `trail_points`, above zero, which only the last rule may have.
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
            step_ticks: The int number of ticks the trigger must be able to move before it is moved once trailing, or None to let UBI use 1.

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
        self.entry_price = entry_price
        self.stop_price = stop_price
        self.stop_limit_offset = stop_limit_offset
        self.rules = rules
        self.step_ticks = step_ticks

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
            "stop_limit_offset": self.stop_limit_offset,
            "rules": self.rules,
            "step_ticks": self.step_ticks,
        }
