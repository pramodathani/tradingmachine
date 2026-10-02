"""The `ladder` execution of a plan: the order spread over several limit orders at evenly spaced prices.

Every rung is sent at once, `steps` of them, from 2 to 20, as limits evenly spaced from `from_price` to `to_price`, which must differ. Each rung is rounded to the tick on the passive side, so a range that does not divide evenly into ticks gives rungs that rest rather than cross. The quantity is shared as evenly as whole units allow, the first rungs taking the remainder, so 100 over three rungs is 34, 33 and 33, and a quantity smaller than `steps` is refused.

The rung prices replace whatever the order's pricing set, so a ladder needs no pricing. It does not nest, and cannot carry a resting stop.

Typical usage example:

  execution = ladder_execution.LadderExecution(
      from_price=1000.0,
      to_price=990.0,
      steps=5,
  )
  part = order_part.OrderPart(execution=execution)
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class LadderExecution(plan_part.PlanPart):
    """An execution that sends the order as several limit orders at evenly spaced prices, all at once.

    Attributes:
        from_price: The float price in rupees of the first rung.
        to_price: The float price in rupees of the last rung, different from `from_price`.
        steps: The int number of rungs, from 2 to 20.
    """

    def __init__(
        self,
        *,
        from_price: float,
        to_price: float,
        steps: int,
    ):
        """Initialises the execution with its range and its number of rungs.

        Args:
            from_price: The float price in rupees of the first rung.
            to_price: The float price in rupees of the last rung, different from `from_price`.
            steps: The int number of rungs, from 2 to 20.

        Raises:
            Nothing.
        """
        self.from_price = from_price
        self.to_price = to_price
        self.steps = steps

    def document(self) -> dict:
        """Builds the `ladder` execution object UBI reads.

        Returns:
            A dict with the single key `ladder`, whose value holds `from_price`, `to_price` and `steps`.

        Raises:
            Nothing.

        Examples:
            Print a buy spread over five rungs from 1000 down to 990:

            ```python
            from tradingmachine.orders.plan_parts import ladder_execution

            execution = ladder_execution.LadderExecution(
                from_price=1000.0,
                to_price=990.0,
                steps=5,
            )
            print(execution.document())
            ```

            Print an exit that sells the position on three rungs above the market, with no pricing because the rungs set the prices:

            ```python
            from tradingmachine.orders.plan_parts import ladder_execution
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                side="protect",
                execution=ladder_execution.LadderExecution(
                    from_price=1010.0,
                    to_price=1030.0,
                    steps=3,
                ),
            )
            print(part.document())
            ```
        """
        return {
            "ladder": {
                "from_price": self.from_price,
                "to_price": self.to_price,
                "steps": self.steps,
            },
        }
