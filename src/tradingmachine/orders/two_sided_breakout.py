"""The `two_sided_breakout` synthetic order type: a buy stop above a range and a sell stop below it, where the first to fire cancels the other.

Both entries are native stop orders at the exchange, so they fire at exchange speed whether or not UBI is running; UBI only notices which went and cancels the other, rather than reducing it, because the two are opposite trades. A spike through both levels inside one tick fills both. After the break, the optional stop and target are armed as for a `OneCancelsOtherOrder`. UBI never works out references for this type, so give real numbers.

Typical usage example:

  order = two_sided_breakout.TwoSidedBreakoutOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="sl",
      quantity=10,
      price=1012.0,
      trigger_price=1010.0,
      buy_trigger=1010.0,
      buy_limit=1012.0,
      sell_trigger=990.0,
      sell_limit=988.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class TwoSidedBreakoutOrder(synthetic_order.SyntheticOrder):
    """A buy stop above a range and a sell stop below it, where the first to fire cancels the other.

    Both entries are native stop orders at the exchange, so they fire at exchange speed whether or not UBI is running; UBI only notices which went and cancels the other, rather than reducing it, because the two are opposite trades. A spike through both levels inside one tick fills both. After the break, the optional stop and target are armed as for a `OneCancelsOtherOrder`. UBI never works out references for this type, so give real numbers.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        buy_trigger: The float trigger of the buy stop in rupees, above `sell_trigger`.
        buy_limit: The float limit of the buy stop in rupees.
        sell_trigger: The float trigger of the sell stop in rupees, below `buy_trigger`.
        sell_limit: The float limit of the sell stop in rupees.
        stop_price: The float trigger of the stop armed after the break, or None.
        stop_limit_price: The float limit of that stop, required with `stop_price`, or None.
        target_price: The float limit of the target armed after the break, or None.
    """

    SYNTHETIC_TYPE = "two_sided_breakout"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        buy_trigger: float,
        buy_limit: float,
        sell_trigger: float,
        sell_limit: float,
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
        stop_price: float | None = None,
        stop_limit_price: float | None = None,
        target_price: float | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            buy_trigger: The float trigger of the buy stop in rupees, above `sell_trigger`.
            buy_limit: The float limit of the buy stop in rupees.
            sell_trigger: The float trigger of the sell stop in rupees, below `buy_trigger`.
            sell_limit: The float limit of the sell stop in rupees.
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
            stop_price: The float trigger of the stop armed after the break, or None.
            stop_limit_price: The float limit of that stop, required with `stop_price`, or None.
            target_price: The float limit of the target armed after the break, or None.

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
        self.buy_trigger = buy_trigger
        self.buy_limit = buy_limit
        self.sell_trigger = sell_trigger
        self.sell_limit = sell_limit
        self.stop_price = stop_price
        self.stop_limit_price = stop_limit_price
        self.target_price = target_price

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "buy_trigger": self.buy_trigger,
            "buy_limit": self.buy_limit,
            "sell_trigger": self.sell_trigger,
            "sell_limit": self.sell_limit,
            "stop_price": self.stop_price,
            "stop_limit_price": self.stop_limit_price,
            "target_price": self.target_price,
        }
