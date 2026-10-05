"""The `liquidity_seeking` synthetic order type: an order that shows nothing and strikes only when enough size appears at an acceptable price.

It is the closest thing to a minimum-quantity order that anyone can build: it waits until the visible book covers `minimum_quantity` at `limit_price` or better, and then sends an order for it. It answers HTTP 202 with an `outcome` of `armed` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer.

Typical usage example:

  order = liquidity_seeking.LiquiditySeekingOrder(
      share,
      transaction_type="buy",
      product="cnc",
      order_type="limit",
      quantity=500,
      price=1000.0,
      limit_price=1001.0,
      minimum_quantity=200,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order


class LiquiditySeekingOrder(synthetic_order.SyntheticOrder):
    """An order that shows nothing and strikes only when enough size appears at an acceptable price.

    It is the closest thing to a minimum-quantity order that anyone can build: it waits until the visible book covers `minimum_quantity` at `limit_price` or better, and then sends an order for it. It answers HTTP 202 with an `outcome` of `armed` and sends nothing to a broker until it fires, so keep the `parent_id` from the answer.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        limit_price: The float worst price in rupees it will trade at. Above zero.
        minimum_quantity: The int smallest size worth striking for, at least 1.
    """

    SYNTHETIC_TYPE = "liquidity_seeking"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        limit_price: float,
        minimum_quantity: int,
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
    ):
        """Initialises the order template and this type's own settings.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            limit_price: The float worst price in rupees it will trade at. Above zero.
            minimum_quantity: The int smallest size worth striking for, at least 1.
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
        self.limit_price = limit_price
        self.minimum_quantity = minimum_quantity

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out.

        Raises:
            Nothing.

        Examples:
            Print the settings of a buy that waits for at least 5,000 shares on offer at 13 rupees or less:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import liquidity_seeking

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = liquidity_seeking.LiquiditySeekingOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                limit_price=13.0,
                minimum_quantity=5000,
            )
            print(order.synthetic_fields())
            ```

            Show the synthetic object of a sell that strikes only when enough bids appear at 14 rupees:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import liquidity_seeking

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = liquidity_seeking.LiquiditySeekingOrder(
                share,
                transaction_type="sell",
                product="mis",
                order_type="limit",
                quantity=1,
                limit_price=14.0,
                minimum_quantity=1000,
            )
            print(order.synthetic)
            ```
        """
        return {
            "limit_price": self.limit_price,
            "minimum_quantity": self.minimum_quantity,
        }
