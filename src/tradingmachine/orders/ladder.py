"""The `ladder` synthetic order type: several limit orders spaced evenly between two prices, sharing the quantity between them.

The quantity is divided among the rungs rather than repeated, so 100 over three steps is 34, 33 and 33. The ladder places every rung at once and then does nothing more, so the rungs keep working at the broker whether or not UBI is running. UBI never works out references for a ladder, so give real numbers. The answer carries a list of `order_ids`, one per rung.

Typical usage example:

  order = ladder.LadderOrder(
      share,
      transaction_type="buy",
      product="cnc",
      order_type="limit",
      quantity=100,
      price=1000.0,
      from_price=995.0,
      to_price=1000.0,
      steps=3,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class LadderOrder(synthetic_order.SyntheticOrder):
    """Several limit orders spaced evenly between two prices, sharing the quantity between them.

    The quantity is divided among the rungs rather than repeated, so 100 over three steps is 34, 33 and 33. The ladder places every rung at once and then does nothing more, so the rungs keep working at the broker whether or not UBI is running. UBI never works out references for a ladder, so give real numbers. The answer carries a list of `order_ids`, one per rung.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        from_price: The float price of the first rung in rupees. Above zero.
        to_price: The float price of the last rung in rupees. Above zero, and different from `from_price`.
        steps: The int number of rungs, from 2 to 20. The quantity must be at least this.
    """

    SYNTHETIC_TYPE = "ladder"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        from_price: float,
        to_price: float,
        steps: int,
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
            from_price: The float price of the first rung in rupees. Above zero.
            to_price: The float price of the last rung in rupees. Above zero, and different from `from_price`.
            steps: The int number of rungs, from 2 to 20. The quantity must be at least this.
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
        self.from_price = from_price
        self.to_price = to_price
        self.steps = steps

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "from_price": self.from_price,
            "to_price": self.to_price,
            "steps": self.steps,
        }
