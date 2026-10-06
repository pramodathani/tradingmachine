"""The `legged_spread` synthetic order type: two legs worked one after the other so that together they reach a net price.

UBI rests the first leg passively and, as it fills, takes the second leg at whatever price makes the pair come to `net_price`. The second leg follows every fill of the first with a new order, in whole lots of its own instrument rounded to the nearest lot, so a first leg of 75 Nifty units is matched by 80 Sensex units. Each new order is priced so that the second leg's orders together average the price the net needs, rounded to the second leg's tick in your favour, down for a buy and up for a sell, and the second leg's own `quantity`, `price` and `order_type` are not used. UBI reads the second leg's instrument when the order arrives, so one that is not mapped is refused with HTTP 404 before anything is sent. When the second leg is refused, UBI cancels the rest of the first and the parent ends `failed`, because what filled is left one-legged. Only an exchange's own multi-leg order can guarantee a net price, so between the two fills the position is one-legged, and a market that moves in that moment leaves the second leg unfilled at the price wanted. UBI never resolves price or quantity references for this type.

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

    The template's fields are the defaults each leg may override, and the first leg's instrument anchors the request. The second leg follows every fill of the first with a new order, in whole lots of its own instrument rounded to the nearest lot, so a first leg of 75 Nifty units is matched by 80 Sensex units. Each new order is priced so that the second leg's orders together average the price the net needs, rounded to the second leg's tick in your favour, down for a buy and up for a sell, and the second leg's own `quantity`, `price` and `order_type` are not used. UBI reads the second leg's instrument when the order arrives, so one that is not mapped is refused with HTTP 404 before anything is sent. When the second leg is refused, UBI cancels the rest of the first and the parent ends `failed`, because what filled is left one-legged.

    The order template's attributes are described on `SyntheticOrder`, where `instrument` is the first leg's.

    Attributes:
        first_leg: The order_candidate.OrderCandidate worked passively first.
        second_leg: The order_candidate.OrderCandidate taken as the first fills, whose own quantity, price and order type are not used.
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
        reduce_only: bool = False,
        hold_limits: bool | None = None,
        dry_run: bool = False,
    ):
        """Initialises the two legs, the template they default to and the net price.

        Args:
            first_leg: The order_candidate.OrderCandidate worked passively first.
            second_leg: The order_candidate.OrderCandidate taken as the first fills, on a different instrument, whose own quantity, price and order type are not used.
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
            reduce_only: A bool that is True to have UBI refuse, with HTTP 409, any leg that is not on the closing side of the net position held when it is sent or is bigger than that position.
            hold_limits: A bool that is True to have UBI hold each order that would rest at the broker at a fixed limit price until the other side of the book reaches it, False to send them as they come, or None to let UBI use the type's default.
            dry_run: A bool that is True to have UBI check the order and answer with the `plan` it would run, without recording or sending anything; the answer's `request` is the template as a broker would receive it, which for a stop is not the stop.

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
            reduce_only=reduce_only,
            hold_limits=hold_limits,
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

        Examples:
            Print the settings of a pair bought in one share and sold in another for a net debit:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import legged_spread
            from tradingmachine.orders import order_candidate

            share = equities.Equity(exchange="nse", symbol="IDEA")
            second_share = equities.Equity(exchange="nse", symbol="YESBANK")
            order = legged_spread.LeggedSpreadOrder(
                first_leg=order_candidate.OrderCandidate(share, price=13.0),
                second_leg=order_candidate.OrderCandidate(
                    second_share,
                    transaction_type="sell",
                ),
                net_price=-6.0,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
            )
            print(order.synthetic_fields())
            ```

            Print which leg is worked first and which is taken as it fills:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import legged_spread
            from tradingmachine.orders import order_candidate

            share = equities.Equity(exchange="nse", symbol="IDEA")
            second_share = equities.Equity(exchange="nse", symbol="YESBANK")
            order = legged_spread.LeggedSpreadOrder(
                first_leg=order_candidate.OrderCandidate(second_share, price=19.0),
                second_leg=order_candidate.OrderCandidate(
                    share,
                    transaction_type="sell",
                ),
                net_price=5.0,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
            )
            fields = order.synthetic_fields()
            for leg in fields["candidates"]:
                print(leg)
            print(f"net price {fields['net_price']}")
            ```
        """
        return {
            "candidates": [
                self.first_leg.document(),
                self.second_leg.document(),
            ],
            "net_price": self.net_price,
        }
