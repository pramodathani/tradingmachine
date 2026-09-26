"""The `atr_trail` synthetic order type: a trailing stop whose distance is a multiple of the recent average true range.

The distance widens when the market is volatile and narrows when it is quiet. Until enough bars exist to measure the average true range, `trail_points` is used instead.

Typical usage example:

  order = average_true_range_trail.AverageTrueRangeTrailOrder(
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


class AverageTrueRangeTrailOrder(synthetic_order.SyntheticOrder):
    """A trailing stop whose distance is a multiple of the recent average true range.

    The distance widens when the market is volatile and narrows when it is quiet. Until enough bars exist to measure the average true range, `trail_points` is used instead.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        trail_points: The float fixed distance in rupees used until enough bars exist. Above zero.
        stop_limit_offset: The float distance in rupees past the trigger that the stop's limit sits. Above zero.
        bar_minutes: The float length of each bar in minutes, or None to let UBI use 5.
        periods: The int number of bars averaged, at least 2, or None to let UBI use 14.
        average_true_range_multiple: The float multiple of the average true range to trail by, or None to let UBI use 2.
        step_ticks: The int number of ticks the trigger must be able to move before it is moved, or None to let UBI use 1.
    """

    SYNTHETIC_TYPE = "atr_trail"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        trail_points: float,
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
        dry_run: bool = False,
        bar_minutes: float | None = None,
        periods: int | None = None,
        average_true_range_multiple: float | None = None,
        step_ticks: int | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            trail_points: The float fixed distance in rupees used until enough bars exist. Above zero.
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
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
            bar_minutes: The float length of each bar in minutes, or None to let UBI use 5.
            periods: The int number of bars averaged, at least 2, or None to let UBI use 14.
            average_true_range_multiple: The float multiple of the average true range to trail by, or None to let UBI use 2.
            step_ticks: The int number of ticks the trigger must be able to move before it is moved, or None to let UBI use 1.

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
            dry_run=dry_run,
        )
        self.trail_points = trail_points
        self.stop_limit_offset = stop_limit_offset
        self.bar_minutes = bar_minutes
        self.periods = periods
        self.average_true_range_multiple = average_true_range_multiple
        self.step_ticks = step_ticks

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "trail_points": self.trail_points,
            "stop_limit_offset": self.stop_limit_offset,
            "bar_minutes": self.bar_minutes,
            "periods": self.periods,
            "atr_multiple": self.average_true_range_multiple,
            "step_ticks": self.step_ticks,
        }
