"""The `using` join of a plan: an order split into the pieces its execution would send, each piece run as a whole plan of its own.

The `order` must be an `OrderPart` with exactly one execution whose pieces are known in advance, `ladder`, `twap` or `front_loaded`, and a timed execution must give `over_minutes` rather than `until`. UBI makes one copy of the order per piece, writes `each_piece`'s presets and slot values onto it, and gives each copy its piece's share: a ladder's copies their rung's price, and a timed execution's copies their slice's turn. So `each_piece` naming the `bracket` preset gives every rung of a ladder its own bracket. `each_piece` takes no execution, a slot given in both is refused, though presets are joined, and with a ladder neither side takes a pricing. A using join is never resized, so it cannot be a `then` join's child.

Typical usage example:

  part = using_part.UsingPart(
      order=order_part.OrderPart(
          execution=twap_execution.TwapExecution(slices=4, over_minutes=60),
      ),
      each_piece=order_part.OrderPart(
          presets=[
              preset.Preset("bracket", stop_price=990.0, stop_limit_price=988.0, target_price=1020.0),
          ],
      ),
  )
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class UsingPart(plan_part.PlanPart):
    """An order whose execution's pieces each become a whole plan with the same extra presets and slot values.

    Attributes:
        order: The plan_part.PlanPart `OrderPart` that is split, carrying one `ladder`, `twap` or `front_loaded` execution.
        each_piece: The plan_part.PlanPart `OrderPart` whose presets and slot values are written onto every piece.
    """

    def __init__(
        self,
        *,
        order: plan_part.PlanPart,
        each_piece: plan_part.PlanPart,
    ):
        """Initialises the join with the order to split and what each piece is given.

        Args:
            order: The plan_part.PlanPart to split, which must be an `OrderPart` with exactly one execution, a `LadderExecution`, a `TwapExecution` or a `FrontLoadedExecution`, and no `inner_execution`.
            each_piece: The plan_part.PlanPart `OrderPart` holding the presets and slot values every piece is given; it takes no execution and must not repeat a slot `order` gives, though its presets are added after the order's.

        Raises:
            Nothing.
        """
        self.order = order
        self.each_piece = each_piece

    def document(self) -> dict:
        """Builds the `using` node UBI reads.

        UBI takes the contents of the two orders rather than order nodes, so the `order` key of each part's document is unwrapped.

        Returns:
            A dict with the single key `using`, whose value holds `order` and `each_piece`, each the settings of its `OrderPart`.

        Raises:
            Nothing.

        Examples:
            Print a buy sent as four TWAP slices over an hour, every slice protected by its own bracket:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import preset
            from tradingmachine.orders.plan_parts import twap_execution
            from tradingmachine.orders.plan_parts import using_part

            part = using_part.UsingPart(
                order=order_part.OrderPart(
                    execution=twap_execution.TwapExecution(slices=4, over_minutes=60),
                ),
                each_piece=order_part.OrderPart(
                    presets=[
                        preset.Preset("bracket", stop_price=990.0, stop_limit_price=988.0, target_price=1020.0),
                    ],
                ),
            )
            print(part.document())
            ```

            Print a buy sent as three slices over half an hour, each slice taking what is on offer two ticks through the touch:

            ```python
            from tradingmachine.orders.plan_parts import marketable_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import twap_execution
            from tradingmachine.orders.plan_parts import using_part

            part = using_part.UsingPart(
                order=order_part.OrderPart(
                    execution=twap_execution.TwapExecution(slices=3, over_minutes=30),
                ),
                each_piece=order_part.OrderPart(
                    pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
                ),
            )
            print(part.document())
            ```

            Print a buy laddered across five rungs from 1000 down to 980, every rung protected by its own bracket and no pricing given, because a ladder prices each rung itself:

            ```python
            from tradingmachine.orders.plan_parts import ladder_execution
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import preset
            from tradingmachine.orders.plan_parts import using_part

            part = using_part.UsingPart(
                order=order_part.OrderPart(
                    execution=ladder_execution.LadderExecution(
                        from_price=1000.0,
                        to_price=980.0,
                        steps=5,
                    ),
                ),
                each_piece=order_part.OrderPart(
                    presets=[
                        preset.Preset("bracket", stop_price=970.0, stop_limit_price=968.0, target_price=1020.0),
                    ],
                ),
            )
            print(part.document())
            ```
        """
        return {
            "using": {
                "order": self.order.document()["order"],
                "each_piece": self.each_piece.document()["order"],
            },
        }
