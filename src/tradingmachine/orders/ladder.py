"""The `ladder` synthetic order type: several limit orders spaced evenly between two prices, sharing the quantity between them.

The quantity is divided among the rungs rather than repeated, in whole lots with the first rungs taking the remainder, so 100 over three steps is 34, 33 and 33, and 225 on a lot of 75 over two steps is 150 and 75. UBI refuses with HTTP 400 a quantity of fewer lots than `steps`. By default UBI holds every rung in its virtual order book and sends each one only when the other side of the book reaches that rung's own price, so a rung the market never reaches costs no order message, and the answer is HTTP 202 with an `outcome` of `armed`. A held rung is the plan part `root.pieces.0`, `root.pieces.1` and so on, which `PlanOrder`'s part methods can change or cancel without a broker message, and it gives up its place in the queue. With `hold_limits` False every rung is sent at once and rests at the broker, and the answer carries a `legs` list with one entry per rung. UBI never works out references for a ladder, so give real numbers.

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

    The quantity is divided among the rungs rather than repeated, in whole lots with the first rungs taking the remainder, so 100 over three steps is 34, 33 and 33, and 225 on a lot of 75 over two steps is 150 and 75. UBI refuses with HTTP 400 a quantity of fewer lots than `steps`. By default UBI holds every rung in its virtual order book and sends each one only when the other side of the book reaches that rung's own price, so a rung the market never reaches costs no order message, and the answer is HTTP 202 with an `outcome` of `armed`. A held rung is the plan part `root.pieces.0`, `root.pieces.1` and so on, which `PlanOrder`'s part methods can change or cancel without a broker message, and it gives up its place in the queue. With `hold_limits` False every rung is sent at once and rests at the broker, and the answer carries a `legs` list with one entry per rung. UBI never works out references for a ladder, so give real numbers.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        from_price: The float price of the first rung in rupees. Above zero.
        to_price: The float price of the last rung in rupees. Above zero, and different from `from_price`.
        steps: The int number of rungs, from 2 to 20. The quantity must be at least this many lots.
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
        reduce_only: bool = False,
        hold_limits: bool | None = None,
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
            steps: The int number of rungs, from 2 to 20. The quantity must be at least this many lots.
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
        self.from_price = from_price
        self.to_price = to_price
        self.steps = steps

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.

        Examples:
            Print the settings of a ladder of three bids from 13 rupees down to 12.8:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import ladder

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = ladder.LadderOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=3,
                from_price=13.0,
                to_price=12.8,
                steps=3,
            )
            print(order.synthetic_fields())
            ```

            Work out the price of every rung of a ladder of offers:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import ladder

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = ladder.LadderOrder(
                share,
                transaction_type="sell",
                product="mis",
                order_type="limit",
                quantity=4,
                from_price=14.0,
                to_price=14.3,
                steps=4,
            )
            fields = order.synthetic_fields()
            gap = (fields["to_price"] - fields["from_price"]) / (fields["steps"] - 1)
            for rung in range(fields["steps"]):
                print(f"rung {rung + 1}: {fields['from_price'] + gap * rung:.2f}")
            ```
        """
        return {
            "from_price": self.from_price,
            "to_price": self.to_price,
            "steps": self.steps,
        }
