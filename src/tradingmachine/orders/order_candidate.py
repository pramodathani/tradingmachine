"""One leg of a synthetic order that spans several instruments.

`BasketOrder`, `OneCancelsAllOrder`, `LeggedSpreadOrder` and `StrategyStopOrder` each place one real order per candidate. A candidate names its instrument and may override eight fields of the order template; every field left as None takes the template's value.

Typical usage example:

  first = order_candidate.OrderCandidate(nifty_call, price=120.0)
  second = order_candidate.OrderCandidate(nifty_put, transaction_type="sell", price=95.0)
  document = first.document()
"""

from tradingmachine.assets import instruments


class OrderCandidate:
    """One instrument's order inside a multi-instrument synthetic order, with the template fields it overrides.

    Attributes:
        instrument: The instruments.TradeableInstrument this leg trades.
        transaction_type: The str side, `buy` or `sell`, or None to use the template's.
        product: The str product, `cnc`, `mis` or `nrml`, or None to use the template's.
        order_type: The str kind of order, or None to use the template's.
        validity: The str validity, `day` or `ioc`, or None to use the template's.
        quantity: The int quantity in underlying units, or None to use the template's.
        price: The float limit price in rupees, or None to use the template's.
        trigger_price: The float trigger price in rupees, or None to use the template's.
        tag: The str label, or None to use the template's.
    """

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str | None = None,
        product: str | None = None,
        order_type: str | None = None,
        validity: str | None = None,
        quantity: int | None = None,
        price: float | None = None,
        trigger_price: float | None = None,
        tag: str | None = None,
    ):
        """Initialises the leg with its instrument and the fields it overrides.

        A candidate is merged over the whole template, so a template price is carried into a candidate that sets `order_type` to `market` unless the candidate is priced differently, and UBI then refuses the market order that carries a price. Give such a template no price, or give each candidate its own.

        Args:
            instrument: The instruments.TradeableInstrument this leg trades.
            transaction_type: The str side, `buy` or `sell`, or None to use the template's.
            product: The str product, `cnc`, `mis` or `nrml`, or None to use the template's.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`, or None to use the template's.
            validity: The str validity, `day` or `ioc`, or None to use the template's.
            quantity: The int quantity in underlying units, or None to use the template's.
            price: The float limit price in rupees, or None to use the template's.
            trigger_price: The float trigger price in rupees, or None to use the template's.
            tag: A str of up to twenty letters and digits, or None to use the template's.

        Raises:
            Nothing.
        """
        self.instrument = instrument
        self.transaction_type = transaction_type
        self.product = product
        self.order_type = order_type
        self.validity = validity
        self.quantity = quantity
        self.price = price
        self.trigger_price = trigger_price
        self.tag = tag

    def document(self) -> dict:
        """Builds the candidate object UBI reads, naming the instrument and every field that is set.

        Returns:
            A dict with `instrument_id` and each overridden field that is not None.

        Raises:
            Nothing.
        """
        candidate = {
            "instrument_id": self.instrument.instrument_id,
        }
        overrides = {
            "transaction_type": self.transaction_type,
            "product": self.product,
            "order_type": self.order_type,
            "validity": self.validity,
            "quantity": self.quantity,
            "price": self.price,
            "trigger_price": self.trigger_price,
            "tag": self.tag,
        }
        for field, value in overrides.items():
            if value is not None:
                candidate[field] = value
        return candidate
