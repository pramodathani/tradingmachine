"""The `freeze_slicer` synthetic order type: an order above the exchange's freeze quantity, split into even orders that each fit.

An exchange refuses any single futures or options order above its freeze quantity. UBI reads the limit that the broker it is sending to publishes, in that broker's own units, and splits the order evenly, so 250 against a limit of 100 goes as 84, 83 and 83. When the broker publishes no limit, the order goes whole. The answer carries a list of `order_ids`, one per slice.

Typical usage example:

  order = freeze_slicer.FreezeSlicerOrder(
      share,
      transaction_type="buy",
      product="nrml",
      order_type="limit",
      quantity=2500,
      price=120.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class FreezeSlicerOrder(synthetic_order.SyntheticOrder):
    """An order above the exchange's freeze quantity, split into even orders that each fit.

    An exchange refuses any single futures or options order above its freeze quantity. UBI reads the limit that the broker it is sending to publishes, in that broker's own units, and splits the order evenly, so 250 against a limit of 100 goes as 84, 83 and 83. When the broker publishes no limit, the order goes whole. The answer carries a list of `order_ids`, one per slice.

    The order template's attributes are described on `SyntheticOrder`, and this type adds none of its own.
    """

    SYNTHETIC_TYPE = "freeze_slicer"

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

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            An empty dict, because this type has no settings of its own.

        Raises:
            Nothing.
        """
        return {}
