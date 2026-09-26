"""The shared base of every synthetic order type UBI's order engine runs.

A synthetic order is one ordinary order body, the template, plus a `synthetic` object naming the type and holding that type's own settings. UBI's order engine then places, watches, changes and cancels the real orders the type is made of. `SyntheticOrder` holds the template and sends it through `TradeableInstrument.place_order`; each subclass in `tradingmachine.orders` adds its own settings.

Typical usage example:

  share = equities.Equity(exchange="nse", symbol="RELIANCE")
  order = bracket.BracketOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=1000.0,
      stop_price=990.0,
      stop_limit_price=988.0,
      target_price=1010.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.assets import instruments


class SyntheticOrder:
    """One order for UBI's order engine: an order template and the synthetic type that works it.

    The template is validated by UBI exactly as a plain order is, and most types use it for every real order they send, changing only what they must. Nothing is checked here before sending.

    Attributes:
        instrument: The instruments.TradeableInstrument the order is placed in.
        transaction_type: The str side of the order, `buy` or `sell`.
        product: The str product, `cnc`, `mis` or `nrml`.
        order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
        quantity: The int quantity in underlying units, or None when a quantity reference supplies it.
        price: The float limit price in rupees, or None.
        trigger_price: The float trigger price in rupees of the order itself, or None.
        validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
        disclosed_quantity: The int quantity to show on the exchange, or None.
        after_market: A bool that is True to send the order as an after-market order.
        tag: A str of up to twenty letters and digits to label the order with, or None.
        price_reference: A dict describing the price for UBI to work out, or None.
        quantity_reference: A dict describing the quantity for UBI to work out, or None.
        closes_position: A bool that is True when every order this type sends closes a position, so it may use the share of a broker's daily order cap kept for exits.
        dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
    """

    SYNTHETIC_TYPE = "simple"

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
        """Initialises the order template.

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
            closes_position: A bool that is True when every order this type sends closes a position.
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.

        Raises:
            Nothing.
        """
        self.instrument = instrument
        self.transaction_type = transaction_type
        self.product = product
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.trigger_price = trigger_price
        self.validity = validity
        self.disclosed_quantity = disclosed_quantity
        self.after_market = after_market
        self.tag = tag
        self.price_reference = price_reference
        self.quantity_reference = quantity_reference
        self.closes_position = closes_position
        self.dry_run = dry_run

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out. The base type has no settings, so this is empty.

        Raises:
            Nothing.
        """
        return {}

    @property
    def synthetic(self) -> dict:
        """The `synthetic` object sent with the order, holding `type`, this type's settings that are not None, and `closes_position` when it is True."""
        document = {
            "type": self.SYNTHETIC_TYPE,
        }
        for field, value in self.synthetic_fields().items():
            if value is not None:
                document[field] = value
        if self.closes_position:
            document["closes_position"] = True
        return document

    def place(self) -> dict:
        """Sends the order to UBI's order engine through `TradeableInstrument.place_order`.

        Returns:
            The dict `place_order` returns. A type that acts at once answers with the broker's answer and a `parent_id`; a type that waits for a price or a time answers with an `outcome` of `armed` or `scheduled`, a `broker` and `order_id` of None, and a `parent_id`, which is the only handle on the order until it reaches a broker.

        Raises:
            BadRequestError: A template field is invalid, or one of this type's own settings is missing or wrong.
            LossLockoutError: The day's loss is past UBI's daily loss limit.
            ConflictError: The engine refused to act on the account's state, such as a post-only order that would cross the book.
            RateLimitError: The broker's daily order cap has no room for this order.
            ServiceUnavailableError: No broker could take the order, or a price UBI needed could not be read.
            OrderOutcomeUnknownError: The engine did not answer in time, so the order may still be placed.
            DirectPlacementError: UBI is placing orders directly, so it would place the template as a plain order; nothing was sent.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.instrument.place_order(
            transaction_type=self.transaction_type,
            order_type=self.order_type,
            quantity=self.quantity,
            product=self.product,
            price=self.price,
            trigger_price=self.trigger_price,
            validity=self.validity,
            disclosed_quantity=self.disclosed_quantity,
            after_market=self.after_market,
            tag=self.tag,
            dry_run=self.dry_run,
            price_reference=self.price_reference,
            quantity_reference=self.quantity_reference,
            synthetic=self.synthetic,
        )
