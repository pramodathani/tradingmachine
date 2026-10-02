"""The `book_depth` execution of a plan: nothing shown until enough size is displayed at an acceptable price, then a strike for what is there.

It adds up the displayed quantity at every level of the other side of the book that is no worse than `limit_price`, and when that reaches `minimum_quantity` it sends the smaller of what is shown and what is left of the order. A strike that partly fills rests at its price, and later strikes are only for what is neither traded nor resting. A strike the broker rejects stops the order. The order starts watching the book as soon as its trigger holds.

The strike's price comes from the order's pricing, so the `liquidity_seeking` preset pairs this execution with a `FixedPricing` at the same `limit_price`, and that is the usual way to write it out. It does not nest, and cannot carry a resting stop.

Typical usage example:

  execution = book_depth_execution.BookDepthExecution(
      limit_price=1000.0,
      minimum_quantity=500,
  )
  part = order_part.OrderPart(execution=execution)
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class BookDepthExecution(plan_part.PlanPart):
    """An execution that waits for enough displayed size at or inside a price and then strikes.

    Attributes:
        limit_price: The float worst price in rupees the order will trade at.
        minimum_quantity: The int displayed size, at least 1, that makes a strike worthwhile.
    """

    def __init__(
        self,
        *,
        limit_price: float,
        minimum_quantity: int,
    ):
        """Initialises the execution with its price and its minimum size.

        Args:
            limit_price: The float worst price in rupees the order will trade at.
            minimum_quantity: The int displayed size, at least 1, that makes a strike worthwhile.

        Raises:
            Nothing.
        """
        self.limit_price = limit_price
        self.minimum_quantity = minimum_quantity

    def document(self) -> dict:
        """Builds the `book_depth` execution object UBI reads.

        Returns:
            A dict with the single key `book_depth`, whose value holds `limit_price` and `minimum_quantity`.

        Raises:
            Nothing.

        Examples:
            Print an execution that strikes once 500 are offered at 1000 or better:

            ```python
            from tradingmachine.orders.plan_parts import book_depth_execution

            execution = book_depth_execution.BookDepthExecution(
                limit_price=1000.0,
                minimum_quantity=500,
            )
            print(execution.document())
            ```

            Print the liquidity-seeking order written out, priced at the same limit so a strike that does not fill rests there:

            ```python
            from tradingmachine.orders.plan_parts import book_depth_execution
            from tradingmachine.orders.plan_parts import fixed_pricing
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                pricing=fixed_pricing.FixedPricing(
                    price=1000.0,
                    order_type="LIMIT",
                ),
                execution=book_depth_execution.BookDepthExecution(
                    limit_price=1000.0,
                    minimum_quantity=500,
                ),
            )
            print(part.document())
            ```
        """
        return {
            "book_depth": {
                "limit_price": self.limit_price,
                "minimum_quantity": self.minimum_quantity,
            },
        }
