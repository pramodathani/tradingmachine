"""The `accumulation` synthetic order type: a fixed quantity bought at a fixed interval, each purchase resting on its own side of the book.

This is a systematic plan in the manner of a SIP, run by UBI. Each purchase rests on its own side of the book rather than paying the spread. A `limit` template's price is a cap: the most a buy pays or the least a sell takes, so a purchase rests at the book's own touch when that is better and at the template's price otherwise. A template price that is not a whole number of ticks is refused with HTTP 400 when the order is placed, and by a dry run as well, and a `purchases` or `every_minutes` out of range is refused with HTTP 400 under its own name. Purchases follow the clock rather than the market's hours, so hourly purchases on an intraday product carry on after the close.

Typical usage example:

  order = accumulation.AccumulationOrder(
      share,
      transaction_type="buy",
      product="cnc",
      order_type="limit",
      quantity=5,
      price_reference={"kind": "bid_level", "level": 1},
      every_minutes=30.0,
      purchases=10,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class AccumulationOrder(synthetic_order.SyntheticOrder):
    """A fixed quantity bought at a fixed interval, each purchase resting on its own side of the book.

    This is a systematic plan in the manner of a SIP, run by UBI. Each purchase rests on its own side of the book rather than paying the spread. A `limit` template's price is a cap: the most a buy pays or the least a sell takes, so a purchase rests at the book's own touch when that is better and at the template's price otherwise. A template price that is not a whole number of ticks is refused with HTTP 400 when the order is placed, and by a dry run as well, and a `purchases` or `every_minutes` out of range is refused with HTTP 400 under its own name. Purchases follow the clock rather than the market's hours, so hourly purchases on an intraday product carry on after the close.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        every_minutes: The float number of minutes between purchases. Above zero.
        purchases: The int number of purchases, from 1 to 100.
    """

    SYNTHETIC_TYPE = "accumulation"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        every_minutes: float,
        purchases: int,
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
            every_minutes: The float number of minutes between purchases. Above zero.
            purchases: The int number of purchases, from 1 to 100.
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
        self.every_minutes = every_minutes
        self.purchases = purchases

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.

        Examples:
            Print the settings of ten purchases of one share, one every thirty minutes:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import accumulation

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = accumulation.AccumulationOrder(
                share,
                transaction_type="buy",
                product="cnc",
                order_type="limit",
                quantity=1,
                price=13.0,
                every_minutes=30,
                purchases=10,
            )
            print(order.synthetic_fields())
            ```

            Work out how many shares the plan buys in all and how long it runs:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import accumulation

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = accumulation.AccumulationOrder(
                share,
                transaction_type="buy",
                product="cnc",
                order_type="limit",
                quantity=2,
                price=13.0,
                every_minutes=15,
                purchases=8,
            )
            fields = order.synthetic_fields()
            total_quantity = order.quantity * fields["purchases"]
            total_minutes = fields["every_minutes"] * (fields["purchases"] - 1)
            print(f"{total_quantity} shares over {total_minutes} minutes")
            ```
        """
        return {
            "every_minutes": self.every_minutes,
            "purchases": self.purchases,
        }
