"""The `scale_with_profit_taker` synthetic order type: a ladder whose every filled rung gets its own profit-taker, and is placed again once that profit is taken.

This is the Atlas's G15, what Interactive Brokers sells as ScaleTrader. The rungs are placed as a `LadderOrder` places them. Once a rung has filled completely, a limit for the same quantity goes out `profit_points` better, a sell above a filled buy or a buy below a filled sell, and once that fills the rung is placed again at its own price, up to `most_cycles` times per rung. A rung is placed again only after its profit-taker has closed it, so the position never grows past the ladder's own quantity. The order does not finish on its own, so cancel it with `cancel()` when you are done. By default UBI holds each rung in its virtual order book until the other side of the book reaches its price, and holds it again once its profit has been taken, answering HTTP 202 with nothing placed, while every profit-taker rests at the broker as soon as its rung fills; give `hold_limits` False to rest the rungs at the broker.

Typical usage example:

  order = scale_with_profit_taker.ScaleWithProfitTakerOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=30,
      price=1000.0,
      from_price=1000.0,
      to_price=990.0,
      steps=3,
      profit_points=4.0,
      most_cycles=5,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class ScaleWithProfitTakerOrder(synthetic_order.SyntheticOrder):
    """A ladder whose every filled rung gets its own profit-taker, and is placed again once that profit is taken.

    This is the Atlas's G15, what Interactive Brokers sells as ScaleTrader. The rungs are placed as a `LadderOrder` places them. Once a rung has filled completely, a limit for the same quantity goes out `profit_points` better, a sell above a filled buy or a buy below a filled sell, and once that fills the rung is placed again at its own price, up to `most_cycles` times per rung. A rung is placed again only after its profit-taker has closed it, so the position never grows past the ladder's own quantity. The order does not finish on its own, so cancel it with `cancel()` when you are done. By default UBI holds each rung in its virtual order book until the other side of the book reaches its price, and holds it again once its profit has been taken, answering HTTP 202 with nothing placed, while every profit-taker rests at the broker as soon as its rung fills; give `hold_limits` False to rest the rungs at the broker.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        from_price: The float price of the first rung in rupees. Above zero.
        to_price: The float price of the last rung in rupees. Above zero, and different from `from_price`.
        steps: The int number of rungs, from 2 to 20. The quantity must be at least this.
        profit_points: The float distance in rupees past a filled rung's price at which its profit-taker is placed. Above zero.
        most_cycles: The int number of times each rung may go round, at least 1, or None to let a rung cycle until the order is cancelled.
    """

    SYNTHETIC_TYPE = "scale_with_profit_taker"

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
        profit_points: float,
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
        most_cycles: int | None = None,
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
            profit_points: The float distance in rupees past a filled rung's price at which its profit-taker is placed. Above zero.
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
            most_cycles: The int number of times each rung may go round, at least 1, or None to let a rung cycle until the order is cancelled.

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
        self.profit_points = profit_points
        self.most_cycles = most_cycles

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
            "profit_points": self.profit_points,
            "most_cycles": self.most_cycles,
        }
