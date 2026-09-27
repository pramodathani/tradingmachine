"""The `closing_price` synthetic order type: an order sliced by volume through the half hour the day's closing price is computed from.

This is market-on-close or limit-on-close, the Atlas's G2. NSE and BSE compute an equity's closing price as the volume weighted average of the trades from 15:00 to 15:30, so this is a volume weighted order spread across that window, which is the nearest there is for futures, options and intraday orders; only the cash segment's post-closing session fills at the closing price exactly, and it takes only delivery orders. The length is worked out from the window, so there is no `over_minutes`. An order sent before the window answers HTTP 202 with an `outcome` of `scheduled` and sends its first slice when the window opens, one sent inside the window sends its first slice at once and spreads the rest over what is left, and one sent after 15:30 is refused with HTTP 400. The window follows the instrument's exchange trading calendar.

Typical usage example:

  order = closing_price.ClosingPriceOrder(
      share,
      transaction_type="buy",
      product="cnc",
      order_type="limit",
      quantity=600,
      price=1000.0,
      slices=6,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class ClosingPriceOrder(synthetic_order.SyntheticOrder):
    """An order sliced by volume through the half hour the day's closing price is computed from.

    This is market-on-close or limit-on-close, the Atlas's G2. NSE and BSE compute an equity's closing price as the volume weighted average of the trades from 15:00 to 15:30, so this is a volume weighted order spread across that window, which is the nearest there is for futures, options and intraday orders; only the cash segment's post-closing session fills at the closing price exactly, and it takes only delivery orders. The length is worked out from the window, so there is no `over_minutes`. An order sent before the window answers HTTP 202 with an `outcome` of `scheduled` and sends its first slice when the window opens, one sent inside the window sends its first slice at once and spreads the rest over what is left, and one sent after 15:30 is refused with HTTP 400. The window follows the instrument's exchange trading calendar.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        slices: The int number of slices, from 2 to 60, or None to let UBI use 6, one every five minutes across the default window. The quantity must be at least this.
        window_start: The str time the window opens, as `HH:MM` or `HH:MM:SS` India time, from 09:15 and before 15:30, or None to let UBI use `15:00`.
        volume_profile: The list of float relative weights, one per half hour from the open, none negative and adding up to more than zero, or None to let UBI use its own.
    """

    SYNTHETIC_TYPE = "closing_price"

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
        slices: int | None = None,
        window_start: str | None = None,
        volume_profile: list[float] | None = None,
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
            slices: The int number of slices, from 2 to 60, or None to let UBI use 6, one every five minutes across the default window. The quantity must be at least this.
            window_start: The str time the window opens, as `HH:MM` or `HH:MM:SS` India time, from 09:15 and before 15:30, or None to let UBI use `15:00`.
            volume_profile: The list of float relative weights, one per half hour from the open, none negative and adding up to more than zero, or None to let UBI use its own.

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
        self.slices = slices
        self.window_start = window_start
        self.volume_profile = volume_profile

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "slices": self.slices,
            "window_start": self.window_start,
            "volume_profile": self.volume_profile,
        }
