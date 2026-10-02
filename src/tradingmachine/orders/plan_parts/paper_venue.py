"""The `paper` venue of a plan: an order that is never sent and is filled on paper instead.

UBI fills a paper order from the virtual book's queue estimate, as a resting order at its limit would have filled, records each fill as a `paper_filled` event and completes the plan once the whole quantity has filled. Because the fills come from that estimate, the order must wait on a `limit_marketable` trigger alone (`paper_needs_limit_marketable`), which also means it takes no pricing of its own and is held at the body's own limit price, and it must be the whole plan (`paper_is_the_whole_plan`), since it cannot be joined with orders that trade for real. Unlike most parts, a venue is an entry of the order's `venue` list rather than a one-key object.

Typical usage example:

  part = order_part.OrderPart(
      trigger=limit_marketable.LimitMarketable(),
      venue=paper_venue.PaperVenue(),
  )
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class PaperVenue(plan_part.PlanPart):
    """Paper trading, where an order is filled from the queue estimate and nothing reaches a broker."""

    def document(self) -> dict:
        """Builds the venue entry UBI reads.

        Returns:
            A dict holding `session` set to `paper`. `OrderPart` puts it in a list of one under `venue`.

        Raises:
            Nothing.

        Examples:
            Print the venue entry:

            ```python
            from tradingmachine.orders.plan_parts import paper_venue

            print(paper_venue.PaperVenue().document())
            ```

            Print a limit order held until the other side reaches its price and then filled on paper:

            ```python
            from tradingmachine.orders.plan_parts import limit_marketable
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import paper_venue

            part = order_part.OrderPart(
                trigger=limit_marketable.LimitMarketable(),
                venue=paper_venue.PaperVenue(),
            )
            print(part.document())
            ```
        """
        return {
            "session": "paper",
        }
