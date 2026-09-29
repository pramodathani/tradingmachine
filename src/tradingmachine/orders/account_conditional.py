"""The `account_conditional` synthetic order type: an order sent, or cancelled, when the account's free margin, day's profit or open position count reaches a level.

This is the Atlas's G17, which waits on the account rather than on a price. About once a second, UBI compares `account_field` with `account_level` in `trigger_direction`: `available_balance` is the free margin across every broker, `day_pnl` is realized plus unrealized profit across every broker as the daily loss lockout reads it, and `open_positions` is how many net positions are open. With `action` set to `place`, nothing is sent until the condition holds, and the answer is HTTP 202 with an `outcome` of `armed`, so keep the `parent_id` from the answer. With `cancel`, the order is sent at once and cancelled when the condition holds, such as pulling a resting bid when the day's loss reaches a limit. `trigger_direction` is required, because the side of the order says nothing about which way the account has to move.

Typical usage example:

  order = account_conditional.AccountConditionalOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=995.0,
      account_field="day_pnl",
      account_level=-5000.0,
      trigger_direction="at_or_below",
      action="cancel",
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class AccountConditionalOrder(synthetic_order.SyntheticOrder):
    """An order sent, or cancelled, when the account's free margin, day's profit or open position count reaches a level.

    This is the Atlas's G17, which waits on the account rather than on a price. About once a second, UBI compares `account_field` with `account_level` in `trigger_direction`: `available_balance` is the free margin across every broker, `day_pnl` is realized plus unrealized profit across every broker as the daily loss lockout reads it, and `open_positions` is how many net positions are open. With `action` set to `place`, nothing is sent until the condition holds, and the answer is HTTP 202 with an `outcome` of `armed`, so keep the `parent_id` from the answer. With `cancel`, the order is sent at once and cancelled when the condition holds, such as pulling a resting bid when the day's loss reaches a limit. `trigger_direction` is required, because the side of the order says nothing about which way the account has to move.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        account_field: The str figure watched, `available_balance`, `day_pnl` or `open_positions`.
        account_level: The float level the figure is compared with, in rupees or in positions, which may be negative for a loss.
        trigger_direction: The str direction, `at_or_above` or `at_or_below`.
        action: The str action when the condition holds, `place` to send the order then or `cancel` to send it at once and cancel it then, or None to let UBI use `place`.
    """

    SYNTHETIC_TYPE = "account_conditional"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        account_field: str,
        account_level: float,
        trigger_direction: str,
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
        action: str | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            account_field: The str figure watched, `available_balance`, `day_pnl` or `open_positions`.
            account_level: The float level the figure is compared with, in rupees or in positions, which may be negative for a loss.
            trigger_direction: The str direction, `at_or_above` or `at_or_below`.
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
            action: The str action when the condition holds, `place` to send the order then or `cancel` to send it at once and cancel it then, or None to let UBI use `place`.

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
        self.account_field = account_field
        self.account_level = account_level
        self.trigger_direction = trigger_direction
        self.action = action

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.

        Examples:
            Print the settings of a buy that is sent only once five positions are open:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import account_conditional

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = account_conditional.AccountConditionalOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
                account_field="open_positions",
                account_level=5,
                trigger_direction="at_or_above",
            )
            print(order.synthetic_fields())
            ```

            Show the synthetic object of a bid that is pulled when the day's loss reaches 2,000 rupees:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import account_conditional

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = account_conditional.AccountConditionalOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
                account_field="day_pnl",
                account_level=-2000.0,
                trigger_direction="at_or_below",
                action="cancel",
            )
            print(order.synthetic)
            ```
        """
        return {
            "account_field": self.account_field,
            "account_level": self.account_level,
            "trigger_direction": self.trigger_direction,
            "action": self.action,
        }
