"""The `peg` synthetic order type: a limit order kept re-priced to the bid, the offer or the midpoint as the book moves.

Every re-price is a real modification that counts against the broker's order limits, so UBI throttles them and never sends one that changes nothing. A modification that changes the price loses the order's place in the queue.

Typical usage example:

  order = peg.PegOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=1000.0,
      reference="mid",
      cap_price=1005.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class PegOrder(synthetic_order.SyntheticOrder):
    """A limit order kept re-priced to the bid, the offer or the midpoint as the book moves.

    Every re-price is a real modification that counts against the broker's order limits, so UBI throttles them and never sends one that changes nothing. A modification that changes the price loses the order's place in the queue.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        reference: The str price to follow, `own_touch` for your own side's best price, `mid` or `opposite_touch`, or None to let UBI use `own_touch`.
        offset_ticks: The int number of ticks away from filling, where a negative number moves towards the market, or None to let UBI use 0.
        cap_price: The float price in rupees it never goes past, or None.
    """

    SYNTHETIC_TYPE = "peg"

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
        dry_run: bool = False,
        reference: str | None = None,
        offset_ticks: int | None = None,
        cap_price: float | None = None,
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
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
            reference: The str price to follow, `own_touch` for your own side's best price, `mid` or `opposite_touch`, or None to let UBI use `own_touch`.
            offset_ticks: The int number of ticks away from filling, where a negative number moves towards the market, or None to let UBI use 0.
            cap_price: The float price in rupees it never goes past, or None.

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
        self.reference = reference
        self.offset_ticks = offset_ticks
        self.cap_price = cap_price

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "reference": self.reference,
            "offset_ticks": self.offset_ticks,
            "cap_price": self.cap_price,
        }
