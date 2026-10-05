"""The `post_only` synthetic order type: a limit order checked to rest rather than trade before it is sent.

Indian exchanges have no post-only flag, so this can only check the book before sending; the book can still move while the order is in flight. When the order would cross, `on_crossing` decides: `refuse` answers HTTP 409 and sends nothing, and `rest` moves the price back to your own side's best price. A buy counts as passive anywhere below the best offer and a sell anywhere above the best bid, so a price inside the spread is sent as it is. UBI refuses a `market` template with `post_only_crosses` and a stop with `post_only_needs_limit`, both with HTTP 400, and with no readable book on arrival it answers HTTP 202 with an `outcome` of `armed` and checks the book on the first tick that has one.

Typical usage example:

  order = post_only.PostOnlyOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=999.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class PostOnlyOrder(synthetic_order.SyntheticOrder):
    """A limit order checked to rest rather than trade before it is sent.

    Indian exchanges have no post-only flag, so this can only check the book before sending; the book can still move while the order is in flight. When the order would cross, `on_crossing` decides: `refuse` answers HTTP 409 and sends nothing, and `rest` moves the price back to your own side's best price. A buy counts as passive anywhere below the best offer and a sell anywhere above the best bid, so a price inside the spread is sent as it is. UBI refuses a `market` template with `post_only_crosses` and a stop with `post_only_needs_limit`, both with HTTP 400, and with no readable book on arrival it answers HTTP 202 with an `outcome` of `armed` and checks the book on the first tick that has one.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        on_crossing: The str action when the order would cross, `refuse` or `rest`, or None to let UBI use `refuse`.
    """

    SYNTHETIC_TYPE = "post_only"

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
        on_crossing: str | None = None,
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
            on_crossing: The str action when the order would cross, `refuse` or `rest`, or None to let UBI use `refuse`.

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
        self.on_crossing = on_crossing

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "on_crossing": self.on_crossing,
        }
