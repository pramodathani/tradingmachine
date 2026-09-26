"""The `square_off` synthetic order type: the day's positions closed at a time of your choosing, before the broker closes them on its terms.

Every broker squares off intraday positions automatically shortly before the close, with a market order and a fee. At `at_time`, UBI instead cancels every resting order on each instrument it is closing, and only then closes the positions with limit orders. Cancelling first is what stops a stop or a target from filling after its position is closed and opening a new position the other way. It closes every position on `product`, or only those in `only_instruments`, and leaves overnight positions alone, which is the difference from `Account.flatten`.

Typical usage example:

  order = square_off.SquareOffOrder(
      share,
      at_time="15:05",
      product="mis",
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class SquareOffOrder(synthetic_order.SyntheticOrder):
    """The day's positions on one product, closed with limit orders at a time of day after their resting orders are cancelled.

    UBI decides the side, the order type and the quantity of every closing order from the positions, so the template carries placeholders for them. The instrument only anchors the request; it does not limit what is closed. It answers HTTP 202 with an `outcome` of `scheduled` and sends nothing until `at_time`, so keep the `parent_id` from the answer.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        at_time: The str time of day to square off, as `HH:MM` or `HH:MM:SS` India time.
        only_instruments: The list of instruments.TradeableInstrument to limit the square-off to, or None for every position on the product.
    """

    SYNTHETIC_TYPE = "square_off"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        at_time: str,
        product: str = "mis",
        only_instruments: list[instruments.TradeableInstrument] | None = None,
        validity: str | None = None,
        tag: str | None = None,
        closes_position: bool = True,
        dry_run: bool = False,
    ):
        """Initialises the square-off.

        Args:
            instrument: The instruments.TradeableInstrument that anchors the request, which does not limit what is closed.
            at_time: The str time of day to square off, as `HH:MM` or `HH:MM:SS` India time, later today and well before the broker's own square-off.
            product: The str order product of the positions to close and of the closing orders, `cnc`, `mis` or `nrml`.
            only_instruments: The list of instruments.TradeableInstrument to limit the square-off to, or None for every position on the product.
            validity: The str validity of the closing orders, `day` or `ioc`, or None to let UBI use `day`.
            tag: A str of up to twenty letters and digits to label the request with, or None.
            closes_position: A bool that is True to let the closing orders use the share of a broker's daily order cap kept for exits, which is what a square-off is.
            dry_run: A bool that is True to have UBI check the request and return it without recording or sending anything.

        Raises:
            Nothing.
        """
        super().__init__(
            instrument,
            transaction_type="sell",
            product=product,
            order_type="market",
            quantity=1,
            validity=validity,
            tag=tag,
            closes_position=closes_position,
            dry_run=dry_run,
        )
        self.at_time = at_time
        self.only_instruments = only_instruments

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        UBI filters positions by their product as the positions route spells it, so the order product is translated: `mis` becomes `intraday`, `cnc` becomes `delivery` and `nrml` becomes `carry`. A product with no translation is sent as given.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        position_product = instruments.POSITION_PRODUCT_FOR_ORDER_PRODUCT.get(
            self.product.lower()
        )
        if position_product is None:
            position_product = self.product
        instrument_ids = None
        if self.only_instruments:
            instrument_ids = []
            for chosen_instrument in self.only_instruments:
                instrument_ids.append(chosen_instrument.instrument_id)
        return {
            "at_time": self.at_time,
            "product": position_product,
            "instrument_ids": instrument_ids,
        }
