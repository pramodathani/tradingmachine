"""The `virtual_limit` synthetic order type: a limit order held inside UBI and sent only when the other side of the book reaches its price.

Nothing rests at the exchange, so the order is invisible until it is sent, and UBI estimates where it would have stood in the queue. The template must be a `limit` order with a price. With `paper` set, nothing is ever sent and the order is filled on paper from that estimate. UBI now runs every plain `limit` order with a price, `day` validity and no `synthetic` object as this type by default, so this class is needed only for `paper`. While it is held, its price and quantity are changed with `TradeableInstrument.modify_order(parent_id=...)` and it is cancelled with `TradeableInstrument.cancel_parent` or `cancel()`; once sent, it is changed by its broker order id like any other order. It answers HTTP 202 with an `outcome` of `armed` and sends nothing to a broker until it fires, a price that is not a whole number of ticks is refused with HTTP 400 when it is placed, and a limit the market never reaches costs no order message at all, so keep the `parent_id` from the answer.

Typical usage example:

  order = virtual_limit.VirtualLimitOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=999.0,
      paper=True,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class VirtualLimitOrder(synthetic_order.SyntheticOrder):
    """A limit order held inside UBI and sent only when the other side of the book reaches its price.

    Nothing rests at the exchange, so the order is invisible until it is sent, and UBI estimates where it would have stood in the queue. The template must be a `limit` order with a price. With `paper` set, nothing is ever sent and the order is filled on paper from that estimate. UBI now runs every plain `limit` order with a price, `day` validity and no `synthetic` object as this type by default, so this class is needed only for `paper`. While it is held, its price and quantity are changed with `TradeableInstrument.modify_order(parent_id=...)` and it is cancelled with `TradeableInstrument.cancel_parent` or `cancel()`; once sent, it is changed by its broker order id like any other order. It answers HTTP 202 with an `outcome` of `armed` and sends nothing to a broker until it fires, a price that is not a whole number of ticks is refused with HTTP 400 when it is placed, and a limit the market never reaches costs no order message at all, so keep the `parent_id` from the answer.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        paper: A bool that is True to fill the order on paper and never send anything.
    """

    SYNTHETIC_TYPE = "virtual_limit"

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
        paper: bool = False,
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
            dry_run: A bool that is True to have UBI check the order and answer with the `plan` it would run, without recording or sending anything; the answer's `request` is the template as a broker would receive it, which for a stop is not the stop.
            paper: A bool that is True to fill the order on paper and never send anything.

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
        self.paper = paper

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        fields = {}
        if self.paper:
            fields["paper"] = True
        return fields
