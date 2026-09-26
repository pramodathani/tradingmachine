"""The `oto` synthetic order type: an order that places a second, described in advance, once the first one fills.

The second order is sized to what the first actually filled, and grown as more of it fills, so a partial fill never leaves the second order larger than the position it follows. UBI builds the second order by laying the `then_` settings over the whole template, so a template `price` is carried into a `then_order_type` of `market` and refused; give such a template no price, or give the second order its own. UBI checks the second order before sending the first, so a dry run catches that.

Typical usage example:

  order = one_triggers_other.OneTriggersOtherOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=100,
      price=1000.0,
      then_transaction_type="sell",
      then_order_type="limit",
      then_price=1010.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class OneTriggersOtherOrder(synthetic_order.SyntheticOrder):
    """An order that places a second, described in advance, once the first one fills.

    The second order is sized to what the first actually filled, and grown as more of it fills, so a partial fill never leaves the second order larger than the position it follows. UBI builds the second order by laying the `then_` settings over the whole template, so a template `price` is carried into a `then_order_type` of `market` and refused; give such a template no price, or give the second order its own. UBI checks the second order before sending the first, so a dry run catches that.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        then_transaction_type: The str side of the second order, `buy` or `sell`.
        then_order_type: The str kind of the second order, `market`, `limit`, `sl` or `sl-m`.
        then_price: The float limit price in rupees of the second order, or None to use the template's.
        then_trigger_price: The float trigger price in rupees of the second order, or None to use the template's.
        then_product: The str product of the second order, or None to use the template's.
        then_validity: The str validity of the second order, or None to use the template's.
    """

    SYNTHETIC_TYPE = "oto"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        then_transaction_type: str,
        then_order_type: str,
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
        then_price: float | None = None,
        then_trigger_price: float | None = None,
        then_product: str | None = None,
        then_validity: str | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            then_transaction_type: The str side of the second order, `buy` or `sell`.
            then_order_type: The str kind of the second order, `market`, `limit`, `sl` or `sl-m`.
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
            then_price: The float limit price in rupees of the second order, or None to use the template's.
            then_trigger_price: The float trigger price in rupees of the second order, or None to use the template's.
            then_product: The str product of the second order, or None to use the template's.
            then_validity: The str validity of the second order, or None to use the template's.

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
        self.then_transaction_type = then_transaction_type
        self.then_order_type = then_order_type
        self.then_price = then_price
        self.then_trigger_price = then_trigger_price
        self.then_product = then_product
        self.then_validity = then_validity

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        then = {
            "transaction_type": self.then_transaction_type,
            "order_type": self.then_order_type,
        }
        optional_fields = {
            "price": self.then_price,
            "trigger_price": self.then_trigger_price,
            "product": self.then_product,
            "validity": self.then_validity,
        }
        for field, value in optional_fields.items():
            if value is not None:
                then[field] = value
        return {
            "then": then,
        }
