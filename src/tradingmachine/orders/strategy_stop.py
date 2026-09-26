"""The `strategy_stop` synthetic order type: a basket whose every leg is closed when the whole strategy's profit or loss crosses a line.

It places its candidates the way a basket does, then watches their combined profit and loss and closes every leg when it falls to `loss_limit` or rises to `profit_target`. Give at least one of the two. UBI never resolves references for this type. The first candidate's instrument anchors the request.

Typical usage example:

  order = strategy_stop.StrategyStopOrder(
      candidates=[
          order_candidate.OrderCandidate(reliance, price=1450.0),
          order_candidate.OrderCandidate(infosys, price=1500.0),
      ],
      transaction_type="buy",
      product="cnc",
      order_type="limit",
      quantity=1,
      loss_limit=-5000.0,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.orders import order_candidate
from tradingmachine.orders import synthetic_order


class StrategyStopOrder(synthetic_order.SyntheticOrder):
    """A basket whose every leg is closed when the whole strategy's profit or loss crosses a line.

    It places its candidates the way a basket does, then watches their combined profit and loss and closes every leg when it falls to `loss_limit` or rises to `profit_target`. Give at least one of the two. UBI never resolves references for this type. The first candidate's instrument anchors the request.

    The order template's attributes are described on `SyntheticOrder`, where `instrument` is the first candidate's.

    Attributes:
        candidates: The list of order_candidate.OrderCandidate, one per instrument.
        loss_limit: The float loss in rupees for the whole strategy at which every leg is closed, below zero, or None.
        profit_target: The float profit in rupees for the whole strategy at which every leg is closed, above zero, or None.
    """

    SYNTHETIC_TYPE = "strategy_stop"

    def __init__(
        self,
        *,
        candidates: list[order_candidate.OrderCandidate],
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int,
        price: float | None = None,
        trigger_price: float | None = None,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
        closes_position: bool = False,
        dry_run: bool = False,
        loss_limit: float | None = None,
        profit_target: float | None = None,
    ):
        """Initialises the candidates, the template they default to and this type's own settings.

        Args:
            candidates: The list of order_candidate.OrderCandidate, from 1 to 25, each on a different instrument.
            transaction_type: The str default side for every candidate, `buy` or `sell`.
            product: The str default product for every candidate, `cnc`, `mis` or `nrml`.
            order_type: The str default kind of order for every candidate, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int default quantity in underlying units for every candidate.
            price: The float default limit price in rupees for every candidate, or None. It is carried into a candidate that sets `order_type` to `market` unless that candidate sets its own price.
            trigger_price: The float default trigger price in rupees for every candidate, or None.
            validity: The str default validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the orders as after-market orders.
            tag: A str default label of up to twenty letters and digits, or None.
            closes_position: A bool that is True when every order this type sends closes a position, so it may use the share of a broker's daily order cap kept for exits.
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
            loss_limit: The float loss in rupees for the whole strategy at which every leg is closed, below zero, or None.
            profit_target: The float profit in rupees for the whole strategy at which every leg is closed, above zero, or None.

        Raises:
            ValueError: No candidate was given, so there is no instrument to anchor the request.
        """
        if not candidates:
            raise ValueError(
                "A strategy_stop order needs at least one candidate to anchor the request"
            )
        super().__init__(
            candidates[0].instrument,
            transaction_type=transaction_type,
            product=product,
            order_type=order_type,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            validity=validity,
            after_market=after_market,
            tag=tag,
            closes_position=closes_position,
            dry_run=dry_run,
        )
        self.candidates = list(candidates)
        self.loss_limit = loss_limit
        self.profit_target = profit_target

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, holding the candidates as UBI reads them, where a value of None means the field is left out.

        Raises:
            Nothing.
        """
        documents = []
        for candidate in self.candidates:
            documents.append(candidate.document())
        return {
            "candidates": documents,
            "loss_limit": self.loss_limit,
            "profit_target": self.profit_target,
        }
