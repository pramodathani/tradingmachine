"""The `scale_out` synthetic order type: a bracket with several targets that take the position off in tranches, and a stop that moves to breakeven.

The targets share the position between them, and only the stop shrinks as each one fills, because the remaining targets already add up to what is left. Once `breakeven_after` targets have filled, the stop is moved to the average entry price rather than cancelled and replaced, so there is never a moment without a stop at the exchange.

Typical usage example:

  order = scale_out.ScaleOutOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=9,
      price=1000.0,
      target_prices=[1010.0, 1020.0, 1030.0],
      stop_price=990.0,
      stop_limit_price=988.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class ScaleOutOrder(synthetic_order.SyntheticOrder):
    """A bracket with several targets that take the position off in tranches, and a stop that moves to breakeven.

    The targets share the position between them, and only the stop shrinks as each one fills, because the remaining targets already add up to what is left. Once `breakeven_after` targets have filled, the stop is moved to the average entry price rather than cancelled and replaced, so there is never a moment without a stop at the exchange.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        target_prices: The list of float target prices in rupees, at least two.
        stop_price: The float trigger of the stop in rupees.
        stop_limit_price: The float limit of the stop in rupees.
        breakeven_after: The int number of targets that must fill before the stop moves to breakeven, or None to let UBI use 1.
    """

    SYNTHETIC_TYPE = "scale_out"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        target_prices: list[float],
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
        dry_run: bool = False,
        breakeven_after: int | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            target_prices: The list of float target prices in rupees, at least two.
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
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
            breakeven_after: The int number of targets that must fill before the stop moves to breakeven, or None to let UBI use 1.

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
        self.target_prices = list(target_prices)
        self.stop_price = stop_price
        self.stop_limit_price = stop_limit_price
        self.breakeven_after = breakeven_after

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "target_prices": self.target_prices,
            "stop_price": self.stop_price,
            "stop_limit_price": self.stop_limit_price,
            "breakeven_after": self.breakeven_after,
        }
