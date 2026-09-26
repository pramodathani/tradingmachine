"""The `oca` synthetic order type: several candidate entries, each on its own instrument, where the first fill cancels all the rest.

It places its candidates the way a basket does, and cancels every other candidate the moment any of them reports a fill, including a partial one. The rest are cancelled rather than reduced, because they are separate trades rather than exits on one position. More candidates mean a higher chance that several fill before the cancels land, and no exchange offers an order that prevents it. UBI never resolves references for this type. The first candidate's instrument anchors the request.

Typical usage example:

  order = one_cancels_all.OneCancelsAllOrder(
      candidates=[
          order_candidate.OrderCandidate(reliance, price=1450.0),
          order_candidate.OrderCandidate(infosys, price=1500.0),
      ],
      transaction_type="buy",
      product="cnc",
      order_type="limit",
      quantity=1,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.orders import order_candidate
from tradingmachine.orders import synthetic_order


class OneCancelsAllOrder(synthetic_order.SyntheticOrder):
    """Several candidate entries, each on its own instrument, where the first fill cancels all the rest.

    It places its candidates the way a basket does, and cancels every other candidate the moment any of them reports a fill, including a partial one. The rest are cancelled rather than reduced, because they are separate trades rather than exits on one position. More candidates mean a higher chance that several fill before the cancels land, and no exchange offers an order that prevents it. UBI never resolves references for this type. The first candidate's instrument anchors the request.

    The order template's attributes are described on `SyntheticOrder`, where `instrument` is the first candidate's.

    Attributes:
        candidates: The list of order_candidate.OrderCandidate, one per instrument.
    """

    SYNTHETIC_TYPE = "oca"

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

        Raises:
            ValueError: No candidate was given, so there is no instrument to anchor the request.
        """
        if not candidates:
            raise ValueError(
                "A oca order needs at least one candidate to anchor the request"
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
        }
