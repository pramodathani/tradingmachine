"""The `volatility` synthetic order type: an option order stated as an implied volatility, priced with the Black-76 model and re-priced as the underlying and time move.

This is the Atlas's G7, an order such as "buy this call at 12.5 volatility". UBI works out the premium from the volatility, the option's strike, expiry and type, the watched instrument's last price as the forward, grown by `interest_rate` to expiry unless it is a future, and the time to 15:30 on the expiry date, in years of 365 days. It follows the watched instrument through the same step and throttle as an `UnderlyingPegOrder`. The template must be a `limit` order, and its `price` is the worst it accepts, the most a buy pays or the least a sell takes; the model's premium is used whenever it is better. Changing the order's price yourself makes it take the volatility your price implies and carry on at that. `lowest_price` and `highest_price` never push the order past that worst price, and an option that has already expired is refused with HTTP 400.

Typical usage example:

  order = volatility.VolatilityOrder(
      nifty_call,
      transaction_type="buy",
      product="nrml",
      order_type="limit",
      quantity=75,
      price=180.0,
      watch_instrument=nifty_future,
      volatility=12.5,
      step_ticks=4,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class VolatilityOrder(synthetic_order.SyntheticOrder):
    """An option order stated as an implied volatility, priced with the Black-76 model and re-priced as the underlying and time move.

    This is the Atlas's G7, an order such as "buy this call at 12.5 volatility". UBI works out the premium from the volatility, the option's strike, expiry and type, the watched instrument's last price as the forward, grown by `interest_rate` to expiry unless it is a future, and the time to 15:30 on the expiry date, in years of 365 days. It follows the watched instrument through the same step and throttle as an `UnderlyingPegOrder`. The template must be a `limit` order, and its `price` is the worst it accepts, the most a buy pays or the least a sell takes; the model's premium is used whenever it is better. Changing the order's price yourself makes it take the volatility your price implies and carry on at that. `lowest_price` and `highest_price` never push the order past that worst price, and an option that has already expired is refused with HTTP 400.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        watch_instrument: The instruments.Instrument that gives the forward price: the future of the same expiry for a true Black-76 forward, or the index.
        volatility: The float implied volatility as a percentage, above zero and at most 500, such as 12.5.
        interest_rate: The float interest rate as a percentage, used to grow a watched index to expiry, or None to let UBI use 0.
        lowest_price: The float lowest price in rupees the order is moved to, above zero, or None for no floor.
        highest_price: The float highest price in rupees the order is moved to, above zero and not below `lowest_price`, or None for no ceiling.
        step_ticks: The int smallest move in ticks worth a modification, at least 1, or None to let UBI use 1.
    """

    SYNTHETIC_TYPE = "volatility"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        watch_instrument: instruments.Instrument,
        volatility: float,
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
        hold_limits: bool | None = None,
        dry_run: bool = False,
        interest_rate: float | None = None,
        lowest_price: float | None = None,
        highest_price: float | None = None,
        step_ticks: int | None = None,
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            watch_instrument: The instruments.Instrument that gives the forward price: the future of the same expiry for a true Black-76 forward, or the index.
            volatility: The float implied volatility as a percentage, above zero and at most 500, such as 12.5.
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
            hold_limits: A bool that is True to have UBI hold each order that would rest at the broker at a fixed limit price until the other side of the book reaches it, False to send them as they come, or None to let UBI use the type's default.
            dry_run: A bool that is True to have UBI check the order and answer with the `plan` it would run, without recording or sending anything; the answer's `request` is the template as a broker would receive it, which for a stop is not the stop.
            interest_rate: The float interest rate as a percentage, used to grow a watched index to expiry, or None to let UBI use 0.
            lowest_price: The float lowest price in rupees the order is moved to, above zero, or None for no floor.
            highest_price: The float highest price in rupees the order is moved to, above zero and not below `lowest_price`, or None for no ceiling.
            step_ticks: The int smallest move in ticks worth a modification, at least 1, or None to let UBI use 1.

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
            hold_limits=hold_limits,
            dry_run=dry_run,
        )
        self.watch_instrument = watch_instrument
        self.volatility = volatility
        self.interest_rate = interest_rate
        self.lowest_price = lowest_price
        self.highest_price = highest_price
        self.step_ticks = step_ticks

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        return {
            "watch_instrument_id": self.watch_instrument.instrument_id,
            "volatility": self.volatility,
            "interest_rate": self.interest_rate,
            "lowest_price": self.lowest_price,
            "highest_price": self.highest_price,
            "step_ticks": self.step_ticks,
        }
