"""The `opening_auction` synthetic order type: an order placed during the pre-open session, so it fills at the price the opening call auction discovers.

This is market-on-open or limit-on-open, the Atlas's G1. UBI places it at `at_time` while the pre-open is collecting orders, or on its next clock tick when collection is already open. Only NSE and BSE equities and exchange traded funds, until 09:10 for a limit and 09:05 for a market order, and NSE stock and index futures, until 09:07 and 09:05, have a pre-open; UBI refuses anything else with HTTP 400 rather than send it into continuous trading, and refuses stop orders and `ioc` too. It does not check that a future is the current month's, the only one with a pre-open. Times follow the instrument's exchange trading calendar, so on a weekend or an exchange holiday the order waits for the next trading day's pre-open. It answers HTTP 202 with an `outcome` of `scheduled` and sends nothing to a broker until then, so keep the `parent_id` from the answer.

Typical usage example:

  order = opening_auction.OpeningAuctionOrder(
      share,
      transaction_type="buy",
      product="cnc",
      order_type="limit",
      quantity=10,
      price=1000.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class OpeningAuctionOrder(synthetic_order.SyntheticOrder):
    """An order placed during the pre-open session, so it fills at the price the opening call auction discovers.

    This is market-on-open or limit-on-open, the Atlas's G1. UBI places it at `at_time` while the pre-open is collecting orders, or on its next clock tick when collection is already open. Only NSE and BSE equities and exchange traded funds, until 09:10 for a limit and 09:05 for a market order, and NSE stock and index futures, until 09:07 and 09:05, have a pre-open; UBI refuses anything else with HTTP 400 rather than send it into continuous trading, and refuses stop orders and `ioc` too. It does not check that a future is the current month's, the only one with a pre-open. Times follow the instrument's exchange trading calendar, so on a weekend or an exchange holiday the order waits for the next trading day's pre-open. It answers HTTP 202 with an `outcome` of `scheduled` and sends nothing to a broker until then, so keep the `parent_id` from the answer.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        at_time: The str time to place the order, as `HH:MM` or `HH:MM:SS` India time, from 09:00 and before the pre-open stops collecting this order, or None to let UBI use `09:00:30`.
    """

    SYNTHETIC_TYPE = "opening_auction"

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
        dry_run: bool = False,
        at_time: str | None = None,
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
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
            at_time: The str time to place the order, as `HH:MM` or `HH:MM:SS` India time, from 09:00 and before the pre-open stops collecting this order, or None to let UBI use `09:00:30`.

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
            dry_run=dry_run,
        )
        self.at_time = at_time

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "at_time": self.at_time,
        }
