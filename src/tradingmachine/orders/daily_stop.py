"""The `daily_stop` synthetic order type: a native stop placed afresh every morning for a position held overnight.

Native Indian stops expire at the end of the day. This re-places one each trading morning at `arm_at`, after the opening auction has settled, never on a weekend or an exchange holiday, and an order sent after that day's `arm_at` first arms on the next trading day, which the answer names as `first_arm_on`. When the market has already opened past the stop, it closes the position with a limit instead of placing a stop that would fire at whatever the gap left. UBI never works out references for this type, so give real numbers. `valid_days` counts calendar days. It answers HTTP 202 with an `outcome` of `armed` or `scheduled` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer.

Typical usage example:

  order = daily_stop.DailyStopOrder(
      share,
      transaction_type="buy",
      product="cnc",
      order_type="sl",
      quantity=10,
      price=948.0,
      trigger_price=950.0,
      stop_price=950.0,
      stop_limit_price=948.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class DailyStopOrder(synthetic_order.SyntheticOrder):
    """A native stop placed afresh every morning for a position held overnight.

    Native Indian stops expire at the end of the day. This re-places one each trading morning at `arm_at`, after the opening auction has settled, never on a weekend or an exchange holiday, and an order sent after that day's `arm_at` first arms on the next trading day, which the answer names as `first_arm_on`. When the market has already opened past the stop, it closes the position with a limit instead of placing a stop that would fire at whatever the gap left. UBI never works out references for this type, so give real numbers. `valid_days` counts calendar days. It answers HTTP 202 with an `outcome` of `armed` or `scheduled` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        stop_price: The float trigger of the stop in rupees. Above zero.
        stop_limit_price: The float limit of the stop in rupees. Above zero.
        arm_at: The str time of day to place the stop, as `HH:MM` or `HH:MM:SS` India time, or None to let UBI use `09:20`.
        valid_days: The int number of days to keep re-placing it, from 1 to 365, or None to let UBI use 30.
    """

    SYNTHETIC_TYPE = "daily_stop"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
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
        reduce_only: bool = False,
        dry_run: bool = False,
        arm_at: str | None = None,
        valid_days: int | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            stop_price: The float trigger of the stop in rupees. Above zero.
            stop_limit_price: The float limit of the stop in rupees. Above zero.
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
            arm_at: The str time of day to place the stop, as `HH:MM` or `HH:MM:SS` India time, or None to let UBI use `09:20`.
            valid_days: The int number of days to keep re-placing it, from 1 to 365, or None to let UBI use 30.

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
        self.stop_price = stop_price
        self.stop_limit_price = stop_limit_price
        self.arm_at = arm_at
        self.valid_days = valid_days

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.

        Examples:
            Print the settings of a stop placed afresh every morning at 09:30 for ten days:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import daily_stop

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = daily_stop.DailyStopOrder(
                share,
                transaction_type="buy",
                product="cnc",
                order_type="sl",
                quantity=1,
                stop_price=12.0,
                stop_limit_price=11.95,
                arm_at="09:30",
                valid_days=10,
            )
            print(order.synthetic_fields())
            ```

            Show that a daily stop left to UBI's defaults sends only its stop prices:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import daily_stop

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = daily_stop.DailyStopOrder(
                share,
                transaction_type="buy",
                product="cnc",
                order_type="sl",
                quantity=1,
                stop_price=12.0,
                stop_limit_price=11.95,
            )
            print(order.synthetic)
            ```
        """
        return {
            "stop_price": self.stop_price,
            "stop_limit_price": self.stop_limit_price,
            "arm_at": self.arm_at,
            "valid_days": self.valid_days,
        }
