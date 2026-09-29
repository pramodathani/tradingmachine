"""The `discretionary` synthetic order type: a limit order that shows one price and quietly takes a slightly worse one when it comes within reach.

The visible limit rests at `price`. When the other side comes within `discretion_points` of it, UBI takes what is there and reduces the resting order by the same amount.

Typical usage example:

  order = discretionary.DiscretionaryOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=1000.0,
      discretion_points=1.5,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class DiscretionaryOrder(synthetic_order.SyntheticOrder):
    """A limit order that shows one price and quietly takes a slightly worse one when it comes within reach.

    The visible limit rests at `price`. When the other side comes within `discretion_points` of it, UBI takes what is there and reduces the resting order by the same amount.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        discretion_points: The float number of rupees beyond the shown price it will pay. Above zero.
        discretion_quantity: The int quantity to take when the chance comes, or None to take everything still resting.
    """

    SYNTHETIC_TYPE = "discretionary"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        discretion_points: float,
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
        discretion_quantity: int | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            discretion_points: The float number of rupees beyond the shown price it will pay. Above zero.
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
            discretion_quantity: The int quantity to take when the chance comes, or None to take everything still resting.

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
        self.discretion_points = discretion_points
        self.discretion_quantity = discretion_quantity

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.

        Examples:
            Print the settings of a bid that shows 13 rupees and will pay up to five paise more:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import discretionary

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = discretionary.DiscretionaryOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
                discretion_points=0.05,
            )
            print(order.synthetic_fields())
            ```

            Work out the worst price a discretionary sell will take:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import discretionary

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = discretionary.DiscretionaryOrder(
                share,
                transaction_type="sell",
                product="mis",
                order_type="limit",
                quantity=2,
                price=14.0,
                discretion_points=0.1,
                discretion_quantity=1,
            )
            fields = order.synthetic_fields()
            worst_price = order.price - fields["discretion_points"]
            print(f"Shows {order.price}, takes down to {worst_price:.2f}")
            ```
        """
        return {
            "discretion_points": self.discretion_points,
            "discretion_quantity": self.discretion_quantity,
        }
