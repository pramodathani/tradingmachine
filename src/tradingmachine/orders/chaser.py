"""The `chaser` synthetic order type: a limit order that starts on its own side of the book and steps towards the other until it fills.

It saves the spread when the market is patient and still fills when it is not. After `cross_after_seconds` it crosses the spread outright, and it never goes past `cap_price`.

Typical usage example:

  order = chaser.ChaserOrder(
      share,
      transaction_type="sell",
      product="mis",
      order_type="limit",
      quantity=75,
      price=120.0,
      cap_price=115.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class ChaserOrder(synthetic_order.SyntheticOrder):
    """A limit order that starts on its own side of the book and steps towards the other until it fills.

    It saves the spread when the market is patient and still fills when it is not. After `cross_after_seconds` it crosses the spread outright, and it never goes past `cap_price`.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        step_ticks: The int number of ticks per step, or None to let UBI use 1.
        step_seconds: The float number of seconds between steps, or None to let UBI use 5.
        cap_price: The float worst price in rupees it will take, or None.
        cross_after_seconds: The float number of seconds after which it crosses the spread, or None never to cross.
    """

    SYNTHETIC_TYPE = "chaser"

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
        step_ticks: int | None = None,
        step_seconds: float | None = None,
        cap_price: float | None = None,
        cross_after_seconds: float | None = None,
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
            step_ticks: The int number of ticks per step, or None to let UBI use 1.
            step_seconds: The float number of seconds between steps, or None to let UBI use 5.
            cap_price: The float worst price in rupees it will take, or None.
            cross_after_seconds: The float number of seconds after which it crosses the spread, or None never to cross.

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
        self.step_ticks = step_ticks
        self.step_seconds = step_seconds
        self.cap_price = cap_price
        self.cross_after_seconds = cross_after_seconds

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "step_ticks": self.step_ticks,
            "step_seconds": self.step_seconds,
            "cap_price": self.cap_price,
            "cross_after_seconds": self.cross_after_seconds,
        }
