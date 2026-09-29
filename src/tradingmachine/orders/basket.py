"""The `basket` synthetic order type: orders on several instruments placed in one request, each reported on its own.

Each candidate is one order on its own instrument, and the template's fields are the defaults each candidate may override. UBI places every candidate and does nothing afterwards. It never resolves price or quantity references for a basket, so give real numbers. The first candidate's instrument anchors the request, and a dry run prepares only that first candidate.

Typical usage example:

  order = basket.BasketOrder(
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


class BasketOrder(synthetic_order.SyntheticOrder):
    """Orders on several instruments placed in one request, each reported on its own.

    Each candidate is one order on its own instrument, and the template's fields are the defaults each candidate may override. UBI places every candidate and does nothing afterwards. It never resolves price or quantity references for a basket, so give real numbers. The first candidate's instrument anchors the request, and a dry run prepares only that first candidate.

    The order template's attributes are described on `SyntheticOrder`, where `instrument` is the first candidate's.

    Attributes:
        candidates: The list of order_candidate.OrderCandidate, one per instrument.
    """

    SYNTHETIC_TYPE = "basket"

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
        reduce_only: bool = False,
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
            reduce_only: A bool that is True to have UBI refuse, with HTTP 409, any leg that is not on the closing side of the net position held when it is sent or is bigger than that position.
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.

        Raises:
            ValueError: No candidate was given, so there is no instrument to anchor the request.
        """
        if not candidates:
            raise ValueError(
                "A basket order needs at least one candidate to anchor the request"
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
            reduce_only=reduce_only,
            dry_run=dry_run,
        )
        self.candidates = list(candidates)

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, holding the candidates as UBI reads them, where a value of None means the field is left out.

        Raises:
            Nothing.

        Examples:
            Print the candidate objects of a basket buying one share of each of two companies:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import basket
            from tradingmachine.orders import order_candidate

            share = equities.Equity(exchange="nse", symbol="IDEA")
            second_share = equities.Equity(exchange="nse", symbol="YESBANK")
            order = basket.BasketOrder(
                candidates=[
                    order_candidate.OrderCandidate(share, price=13.0),
                    order_candidate.OrderCandidate(second_share, price=19.0),
                ],
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
            )
            print(order.synthetic_fields())
            ```

            Count the legs of a basket in which one candidate overrides the side and the quantity:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import basket
            from tradingmachine.orders import order_candidate

            share = equities.Equity(exchange="nse", symbol="IDEA")
            second_share = equities.Equity(exchange="nse", symbol="YESBANK")
            order = basket.BasketOrder(
                candidates=[
                    order_candidate.OrderCandidate(share, price=13.0),
                    order_candidate.OrderCandidate(
                        second_share,
                        transaction_type="sell",
                        quantity=2,
                        price=21.0,
                    ),
                ],
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
            )
            candidates = order.synthetic_fields()["candidates"]
            print(f"{len(candidates)} legs")
            for candidate in candidates:
                print(candidate)
            ```
        """
        documents = []
        for candidate in self.candidates:
            documents.append(candidate.document())
        return {
            "candidates": documents,
        }
