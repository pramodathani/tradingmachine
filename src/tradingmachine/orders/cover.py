"""The `cover` synthetic order type: an entry with a compulsory stop and no target.

It behaves like a bracket without a target, except that the stop is required and a target is refused: the stop is armed on the first partial fill, grows as the entry fills, and is cancelled if the entry is cancelled with nothing filled. Brokers once sold this as a product, and Flattrade's API restricts it, which is why UBI rebuilds it. By default UBI holds a limit entry in its virtual order book until the other side of the book reaches its price, answering HTTP 202 with an `outcome` of `armed`, while the exits rest at the broker as the entry fills; give `hold_limits` False to send the entry at once. A stop the broker refuses cancels the rest of the entry, and the parent ends `failed`, because the position is left without its stop.

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

    It behaves like a bracket without a target, except that the stop is required and a target is refused: the stop is armed on the first partial fill, grows as the entry fills, and is cancelled if the entry is cancelled with nothing filled. Brokers once sold this as a product, and Flattrade's API restricts it, which is why UBI rebuilds it. By default UBI holds a limit entry in its virtual order book until the other side of the book reaches its price, answering HTTP 202 with an `outcome` of `armed`, while the exits rest at the broker as the entry fills; give `hold_limits` False to send the entry at once. A stop the broker refuses cancels the rest of the entry, and the parent ends `failed`, because the position is left without its stop.

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
        self.stop_price = stop_price
        self.stop_limit_price = stop_limit_price

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.

        Examples:
            Print the compulsory stop of a cover order:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import cover

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = cover.CoverOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
                stop_price=12.5,
                stop_limit_price=12.45,
            )
            print(order.synthetic_fields())
            ```

            Work out the most a cover order can lose per share on a short sale:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import cover

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = cover.CoverOrder(
                share,
                transaction_type="sell",
                product="mis",
                order_type="limit",
                quantity=1,
                price=14.0,
                stop_price=14.5,
                stop_limit_price=14.55,
            )
            fields = order.synthetic_fields()
            risk = fields["stop_limit_price"] - order.price
            print(f"At most {risk:.2f} rupees a share")
            ```
        """
        return {
            "stop_price": self.stop_price,
            "stop_limit_price": self.stop_limit_price,
        }
