"""The `trailing_stop` synthetic order type: a real stop at the broker whose trigger follows the market up, never down.

The stop sits at the exchange as a stop-limit, so it keeps protecting the position while UBI is down, and UBI moves its trigger with modifications as the best price improves. Give `trail_points` or `trail_percent`, not both. With `activate_at`, it is a trailing take-profit: nothing is placed until the last traded price reaches that level, the answer is HTTP 202 with an `outcome` of `armed`, and the stop then trails from there.

Typical usage example:

  order = trailing_stop.TrailingStopOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=1000.0,
      trail_points=5.0,
      stop_limit_offset=2.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class TrailingStopOrder(synthetic_order.SyntheticOrder):
    """A real stop at the broker whose trigger follows the market up, never down.

    The stop sits at the exchange as a stop-limit, so it keeps protecting the position while UBI is down, and UBI moves its trigger with modifications as the best price improves. Give `trail_points` or `trail_percent`, not both. With `activate_at`, it is a trailing take-profit: nothing is placed until the last traded price reaches that level, the answer is HTTP 202 with an `outcome` of `armed`, and the stop then trails from there.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        stop_limit_offset: The float distance in rupees past the trigger that the stop's limit sits. Above zero.
        trail_points: The float fixed trailing distance in rupees, or None.
        trail_percent: The float trailing distance as a percentage of the best price seen, or None.
        step_ticks: The int number of ticks the trigger must be able to move before it is moved, or None to let UBI use 1.
        activate_at: The float price in rupees the last traded price must reach before the stop is placed a trail's distance from it, which makes the order a trailing take-profit that answers HTTP 202 with an `outcome` of `armed`, or None to place the stop at once.
    """

    SYNTHETIC_TYPE = "trailing_stop"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        stop_limit_offset: float,
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
        trail_points: float | None = None,
        trail_percent: float | None = None,
        step_ticks: int | None = None,
        activate_at: float | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            stop_limit_offset: The float distance in rupees past the trigger that the stop's limit sits. Above zero.
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
            trail_points: The float fixed trailing distance in rupees, or None.
            trail_percent: The float trailing distance as a percentage of the best price seen, or None.
            step_ticks: The int number of ticks the trigger must be able to move before it is moved, or None to let UBI use 1.
            activate_at: The float price in rupees the last traded price must reach before the stop is placed a trail's distance from it, which makes the order a trailing take-profit that answers HTTP 202 with an `outcome` of `armed`, or None to place the stop at once.

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
        self.stop_limit_offset = stop_limit_offset
        self.trail_points = trail_points
        self.trail_percent = trail_percent
        self.step_ticks = step_ticks
        self.activate_at = activate_at

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "stop_limit_offset": self.stop_limit_offset,
            "trail_points": self.trail_points,
            "trail_percent": self.trail_percent,
            "step_ticks": self.step_ticks,
            "activate_at": self.activate_at,
        }
