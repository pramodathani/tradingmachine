"""The `good_till_time` synthetic order type: an order placed now whose unfilled part is cancelled at a time of day.

Indian exchanges offer only `day` and `ioc` validity, with nothing in between, so this fills that gap: whatever has filled by `until_time` is kept, and the rest is cancelled. With `at_expiry` set to `market`, the rest is instead made marketable at `until_time`, as a limit two ticks past the other side's best price, and the order carries on until it fills. Times follow the instrument's exchange trading calendar: on a weekend or an exchange holiday a time means that time on the next trading day, and the answer names the date.

Typical usage example:

  order = good_till_time.GoodTillTimeOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=100,
      price=995.0,
      until_time="14:30",
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class GoodTillTimeOrder(synthetic_order.SyntheticOrder):
    """An order placed now whose unfilled part is cancelled at a time of day.

    Indian exchanges offer only `day` and `ioc` validity, with nothing in between, so this fills that gap: whatever has filled by `until_time` is kept, and the rest is cancelled. With `at_expiry` set to `market`, the rest is instead made marketable at `until_time`, as a limit two ticks past the other side's best price, and the order carries on until it fills. Times follow the instrument's exchange trading calendar: on a weekend or an exchange holiday a time means that time on the next trading day, and the answer names the date.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        until_time: The str time of day to cancel what has not filled, as `HH:MM` or `HH:MM:SS` India time, later on the trading day.
        at_expiry: The str action at `until_time`, `cancel` to cancel whatever has not filled or `market` to modify it to a limit two ticks past the other side's best price so it takes what is there, or None to let UBI use `cancel`.
    """

    SYNTHETIC_TYPE = "good_till_time"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        until_time: str,
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
        at_expiry: str | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            until_time: The str time of day to cancel what has not filled, as `HH:MM` or `HH:MM:SS` India time, later on the trading day.
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
            at_expiry: The str action at `until_time`, `cancel` to cancel whatever has not filled or `market` to modify it to a limit two ticks past the other side's best price so it takes what is there, or None to let UBI use `cancel`.

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
        self.until_time = until_time
        self.at_expiry = at_expiry

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "until_time": self.until_time,
            "at_expiry": self.at_expiry,
        }
