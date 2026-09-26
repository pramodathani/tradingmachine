"""The `time_stop` synthetic order type: an entry placed now whose filled part is closed at a time of day, or after some minutes.

When the time comes, the unfilled part of the entry is cancelled first and only then is what filled closed, so the entry cannot go on buying into the position being closed. It closes only what this order filled, not everything held in the instrument. Give `until_time` or `minutes`, not both.

Typical usage example:

  order = time_stop.TimeStopOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=1000.0,
      until_time="15:10",
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class TimeStopOrder(synthetic_order.SyntheticOrder):
    """An entry placed now whose filled part is closed at a time of day, or after some minutes.

    When the time comes, the unfilled part of the entry is cancelled first and only then is what filled closed, so the entry cannot go on buying into the position being closed. It closes only what this order filled, not everything held in the instrument. Give `until_time` or `minutes`, not both.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        until_time: The str time of day to close at, as `HH:MM` or `HH:MM:SS` India time, or None.
        minutes: The float number of minutes after placing to close at, or None.
    """

    SYNTHETIC_TYPE = "time_stop"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
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
        until_time: str | None = None,
        minutes: float | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
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
            until_time: The str time of day to close at, as `HH:MM` or `HH:MM:SS` India time, or None.
            minutes: The float number of minutes after placing to close at, or None.

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
        self.until_time = until_time
        self.minutes = minutes

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "until_time": self.until_time,
            "minutes": self.minutes,
        }
