"""The `cover` synthetic order type: an entry with a compulsory stop and no target.

It behaves like a bracket without a target, except that the stop is required and a target is refused: the stop is armed on the first partial fill, grows as the entry fills, and is cancelled if the entry is cancelled with nothing filled. Brokers once sold this as a product, and Flattrade's API restricts it, which is why UBI rebuilds it.

Typical usage example:

  order = cover.CoverOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=100,
      price=1000.0,
      stop_price=990.0,
      stop_limit_price=988.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class CoverOrder(synthetic_order.SyntheticOrder):
    """An entry with a compulsory stop and no target.

    It behaves like a bracket without a target, except that the stop is required and a target is refused: the stop is armed on the first partial fill, grows as the entry fills, and is cancelled if the entry is cancelled with nothing filled. Brokers once sold this as a product, and Flattrade's API restricts it, which is why UBI rebuilds it.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        stop_price: The float trigger of the stop in rupees.
        stop_limit_price: The float limit of the stop in rupees.
    """

    SYNTHETIC_TYPE = "cover"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        stop_price: float,
        stop_limit_price: float,
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
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            stop_price: The float trigger of the stop in rupees.
            stop_limit_price: The float limit of the stop in rupees.
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
        self.stop_price = stop_price
        self.stop_limit_price = stop_limit_price

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "stop_price": self.stop_price,
            "stop_limit_price": self.stop_limit_price,
        }
