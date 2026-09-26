"""The `legged_spread` synthetic order type: two legs worked one after the other so that together they reach a net price.

UBI rests the first leg passively and, as it fills, takes the second leg at whatever price makes the pair come to `net_price`. Only an exchange's own multi-leg order can guarantee a net price, so between the two fills the position is one-legged, and a market that moves in that moment leaves the second leg unfilled at the price wanted. UBI never resolves price or quantity references for this type.

Typical usage example:

  order = legged_spread.LeggedSpreadOrder(
      first_leg=order_candidate.OrderCandidate(nifty_call, transaction_type="buy", price=120.0),
      second_leg=order_candidate.OrderCandidate(nifty_higher_call, transaction_type="sell"),
      net_price=40.0,
      transaction_type="buy",
      product="nrml",
      order_type="limit",
      quantity=75,
      dry_run=True,
  )
  answer = order.place()
"""

from tradingmachine.orders import order_candidate
from tradingmachine.orders import synthetic_order


class LeggedSpreadOrder(synthetic_order.SyntheticOrder):
    """A two-legged spread worked passively on the first leg and completed on the second at the price that makes the net.

    The template's fields are the defaults each leg may override, and the first leg's instrument anchors the request.

    The order template's attributes are described on `SyntheticOrder`, where `instrument` is the first leg's.

    Attributes:
        first_leg: The order_candidate.OrderCandidate worked passively first.
        second_leg: The order_candidate.OrderCandidate taken as the first fills.
        net_price: The float net debit per unit in rupees, positive when the spread costs money and negative when it brings money in.
    """

    SYNTHETIC_TYPE = "legged_spread"

    def __init__(
        self,
        *,
        first_leg: order_candidate.OrderCandidate,
        second_leg: order_candidate.OrderCandidate,
        net_price: float,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int,
        price: float | None = None,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
        closes_position: bool = False,
        dry_run: bool = False,
    ):
        """Initialises the two legs, the template they default to and the net price.

        Args:
            first_leg: The order_candidate.OrderCandidate worked passively first.
            second_leg: The order_candidate.OrderCandidate taken as the first fills, on a different instrument.
            net_price: The float net debit per unit in rupees, positive when the spread costs money and negative when it brings money in.
            transaction_type: The str default side for both legs, `buy` or `sell`.
            product: The str default product for both legs, `cnc`, `mis` or `nrml`.
            order_type: The str default kind of order for both legs, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int default quantity in underlying units for both legs.
            price: The float default limit price in rupees for both legs, or None.
            validity: The str default validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the orders as after-market orders.
            tag: A str default label of up to twenty letters and digits, or None.
            closes_position: A bool that is True when both legs close positions, so they may use the share of a broker's daily order cap kept for exits.
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.

        Raises:
            Nothing.
        """
        super().__init__(
            first_leg.instrument,
            transaction_type=transaction_type,
            product=product,
            order_type=order_type,
            quantity=quantity,
            price=price,
            validity=validity,
            after_market=after_market,
            tag=tag,
            closes_position=closes_position,
            dry_run=dry_run,
        )
        self.first_leg = first_leg
        self.second_leg = second_leg
        self.net_price = net_price

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict holding the two legs as UBI's `candidates`, first leg first, and the `net_price`.

        Raises:
            Nothing.
        """
        return {
            "candidates": [
                self.first_leg.document(),
                self.second_leg.document(),
            ],
            "net_price": self.net_price,
        }
