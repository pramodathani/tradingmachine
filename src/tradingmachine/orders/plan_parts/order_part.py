"""One order inside a plan, which may wait for a trigger, protect a position and be priced by one pricing rule.

The order's instrument, side, quantity, product and validity come from the `PlanOrder` it belongs to, and an order inside a join is sized by the join. An order with no presets and no settings is the template as it stands, run as a `simple` order.

Typical usage example:

  part = order_part.OrderPart(
      presets=[
          preset.Preset("scheduled", at_time="10:00"),
      ],
      trigger=price_crosses.PriceCrosses(level=995.0),
      pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
  )
  document = part.document()
"""

from collections.abc import Sequence

from tradingmachine.orders.plan_parts import plan_part


class OrderPart(plan_part.PlanPart):
    """One order of a plan, with the presets and slot values that shape it.

    Attributes:
        presets: The list of plan_part.PlanPart presets merged into the order first, in order, or None for none.
        trigger: The plan_part.PlanPart condition the order waits for, or None to place it at once.
        side: The str side, `buy`, `sell` or `protect`, or None to use the template's side.
        pricing: The plan_part.PlanPart pricing rule, or None to use the template's own order type and price.
    """

    def __init__(
        self,
        *,
        presets: Sequence[plan_part.PlanPart] | None = None,
        trigger: plan_part.PlanPart | None = None,
        side: str | None = None,
        pricing: plan_part.PlanPart | None = None,
    ):
        """Initialises the order with its presets and its own slot values.

        UBI merges the presets first and the order's own values after them. Triggers from several sources are joined so that all of them must hold, a later pricing rule replaces an earlier one, and two different sides are refused.

        Args:
            presets: A sequence of plan_part.PlanPart presets, usually `Preset` objects, or None for none.
            trigger: A plan_part.PlanPart condition, such as `PriceCrosses` or `AllConditions`, or None to place the order at once.
            side: The str side, `buy`, `sell`, or `protect` to trade against the position the template's side opened, or None to use the template's side.
            pricing: A plan_part.PlanPart pricing rule, such as `FixedPricing` or `TrailPricing`, or None to use the template's own order type and price.

        Raises:
            Nothing.
        """
        self.presets = None
        if presets is not None:
            self.presets = list(presets)
        self.trigger = trigger
        self.side = side
        self.pricing = pricing

    def document(self) -> dict:
        """Builds the `order` node UBI reads, holding every setting that is not None.

        Returns:
            A dict with the single key `order`, whose value holds `presets`, `trigger`, `side` and `pricing` when each is set. UBI takes `pricing` as a list, so the one rule is sent inside a list.

        Raises:
            Nothing.

        Examples:
            Print an order that waits for the price to fall to 995 and then takes what is there:

            ```python
            from tradingmachine.orders.plan_parts import marketable_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import price_crosses

            part = order_part.OrderPart(
                trigger=price_crosses.PriceCrosses(level=995.0),
                pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
            )
            print(part.document())
            ```

            Print an order built from two presets, a time and a touch, which UBI joins so both must hold:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import preset

            part = order_part.OrderPart(
                presets=[
                    preset.Preset("scheduled", at_time="10:00"),
                    preset.Preset("market_if_touched", trigger_price=995.0),
                ],
            )
            print(part.document())
            ```

            Print an empty order, which is the template run as a simple order:

            ```python
            from tradingmachine.orders.plan_parts import order_part

            print(order_part.OrderPart().document())
            ```
        """
        settings = {}
        if self.presets is not None:
            preset_documents = []
            for preset in self.presets:
                preset_documents.append(preset.document())
            settings["presets"] = preset_documents
        if self.trigger is not None:
            settings["trigger"] = self.trigger.document()
        if self.side is not None:
            settings["side"] = self.side
        if self.pricing is not None:
            settings["pricing"] = [
                self.pricing.document(),
            ]
        return {
            "order": settings,
        }
