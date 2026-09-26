"""The `trailing_entry` synthetic order type: a stop entry that follows a falling market down, so the first bounce of the trailing distance fills it.

It is the mirror of a trailing stop for entering: as the price falls, the buy stop's trigger is lowered to stay the trailing distance above the low. Give `trail_points` or `trail_percent`, not both.

Typical usage example:

  order = trailing_entry.TrailingEntryOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="sl",
      quantity=10,
      price=1002.0,
      trigger_price=1000.0,
      trail_points=5.0,
      stop_limit_offset=2.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class TrailingEntryOrder(synthetic_order.SyntheticOrder):
    """A stop entry that follows a falling market down, so the first bounce of the trailing distance fills it.

    It is the mirror of a trailing stop for entering: as the price falls, the buy stop's trigger is lowered to stay the trailing distance above the low. Give `trail_points` or `trail_percent`, not both.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        stop_limit_offset: The float distance in rupees past the trigger that the stop's limit sits. Above zero.
        trail_points: The float fixed trailing distance in rupees, or None.
        trail_percent: The float trailing distance as a percentage of the best price seen, or None.
        step_ticks: The int number of ticks the trigger must be able to move before it is moved, or None to let UBI use 1.
    """

    SYNTHETIC_TYPE = "trailing_entry"

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
        dry_run: bool = False,
        trail_points: float | None = None,
        trail_percent: float | None = None,
        step_ticks: int | None = None,
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
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
            trail_points: The float fixed trailing distance in rupees, or None.
            trail_percent: The float trailing distance as a percentage of the best price seen, or None.
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
        self.stop_limit_offset = stop_limit_offset
        self.trail_points = trail_points
        self.trail_percent = trail_percent
        self.step_ticks = step_ticks

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
        }
