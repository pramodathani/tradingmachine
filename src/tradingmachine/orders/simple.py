"""The `simple` synthetic order type: one plain order sent to one broker, with nothing watching it afterwards.

This is what UBI's order engine runs when an order carries no `synthetic` object at all, unless the order is a plain limit or market order that UBI holds or follows the book with. Asking for it by name is useful for four things: to send a `limit` order to the broker at once, since a plain limit order with a price is otherwise held inside UBI as a `virtual_limit` until the other side reaches its price; to send a real `market` order, since a plain market order is otherwise run as a `marketable_limit` that follows the other side of the book for 30 seconds and is refused with HTTP 409 when that side is empty; to mark the order as closing a position with `closes_position`, so it may use the share of a broker's daily order cap kept for exits; and to make it reduce-only with `reduce_only`.

Typical usage example:

  order = simple.SimpleOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=1000.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class SimpleOrder(synthetic_order.SyntheticOrder):
    """One plain order sent to one broker, with nothing watching it afterwards.

    This is what UBI's order engine runs when an order carries no `synthetic` object at all, unless the order is a plain limit or market order that UBI holds or follows the book with. Asking for it by name is useful for four things: to send a `limit` order to the broker at once, since a plain limit order with a price is otherwise held inside UBI as a `virtual_limit` until the other side reaches its price; to send a real `market` order, since a plain market order is otherwise run as a `marketable_limit` that follows the other side of the book for 30 seconds and is refused with HTTP 409 when that side is empty; to mark the order as closing a position with `closes_position`, so it may use the share of a broker's daily order cap kept for exits; and to make it reduce-only with `reduce_only`.

    The order template's attributes are described on `SyntheticOrder`, and this type adds none of its own.
    """

    SYNTHETIC_TYPE = "simple"

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
            reduce_only=reduce_only,
            hold_limits=hold_limits,
            dry_run=dry_run,
        )

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            An empty dict, because this type has no settings of its own.

        Raises:
            Nothing.
        """
        return {}
