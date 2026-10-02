"""One order inside a plan, which may wait for a trigger, protect or close a position, be priced, be sent in pieces and end on its own.

By default the order's instrument, side, quantity, product and validity come from the `PlanOrder` it belongs to, and an order inside a join is sized by the join. An order can also give its own instrument, quantity, side, product, validity and tag, which is how one plan trades several instruments. An order with no presets and no settings is the template as it stands, run as a `simple` order.

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

from tradingmachine.assets import instruments
from tradingmachine.orders.plan_parts import plan_part


class OrderPart(plan_part.PlanPart):
    """One order of a plan, with the presets and slot values that shape it.

    Attributes:
        presets: The list of plan_part.PlanPart presets merged into the order first, in order, or None for none.
        trigger: The plan_part.PlanPart condition the order waits for, or None to place it at once.
        side: The str side, `buy`, `sell`, `protect`, `close` or `against_delta`, or None to use the template's side.
        pricing: The plan_part.PlanPart pricing rule that sets the price, or None to use the template's own order type and price.
        cap: The plan_part.PlanPart `CapModifier` that bounds the price the rule sets, or None for no bound.
        discretion: The plan_part.PlanPart `DiscretionModifier` that lets part of the order trade a little past its price, or None.
        execution: The plan_part.PlanPart execution that sends the order, such as `TwapExecution`, or None to send it all at once.
        inner_execution: The plan_part.PlanPart execution that sends each piece of `execution`, such as `IcebergExecution`, or None.
        guard: The plan_part.PlanPart `PostOnlyGuard` that keeps the order from trading at once, or None.
        lifetime: The plan_part.PlanPart `Lifetime` that ends the order, or None to let it run until it is done.
        venue: The plan_part.PlanPart venue, `PreOpenVenue` or `PaperVenue`, or None for the normal market.
        quantity: The int quantity, or a plan_part.PlanPart quantity such as `PositionQuantity`, or None to use the template's or the join's quantity.
        instrument: The instruments.TradeableInstrument this order trades, or None for the plan's own instrument.
        transaction_type: The str side of the order's own body, `buy` or `sell`, or None for the template's.
        product: The str product of the order's own body, such as `mis`, or None for the template's.
        validity: The str validity of the order's own body, `day` or `ioc`, or None for the template's.
        tag: The str tag of the order's own body, or None for the template's.
    """

    def __init__(
        self,
        *,
        presets: Sequence[plan_part.PlanPart] | None = None,
        trigger: plan_part.PlanPart | None = None,
        side: str | None = None,
        pricing: plan_part.PlanPart | None = None,
        cap: plan_part.PlanPart | None = None,
        discretion: plan_part.PlanPart | None = None,
        execution: plan_part.PlanPart | None = None,
        inner_execution: plan_part.PlanPart | None = None,
        guard: plan_part.PlanPart | None = None,
        lifetime: plan_part.PlanPart | None = None,
        venue: plan_part.PlanPart | None = None,
        quantity: int | plan_part.PlanPart | None = None,
        instrument: instruments.TradeableInstrument | None = None,
        transaction_type: str | None = None,
        product: str | None = None,
        validity: str | None = None,
        tag: str | None = None,
    ):
        """Initialises the order with its presets and its own slot values.

        UBI merges the presets first and the order's own values after them. Triggers from several sources are joined so that all of them must hold, a later pricing rule, cap, execution, guard or lifetime replaces an earlier one with a warning, and two different sides are refused.

        Args:
            presets: A sequence of plan_part.PlanPart presets, usually `Preset` objects, or None for none.
            trigger: A plan_part.PlanPart condition, such as `PriceCrosses` or `AllConditions`, or None to place the order at once.
            side: The str side, `buy`, `sell`, `protect` to trade against the position the template's side opened, `close` to close the position a `PositionQuantity` names, or `against_delta` to hedge the delta of an option the plan traded, or None to use the template's side.
            pricing: A plan_part.PlanPart pricing rule that sets the price, such as `FixedPricing`, `PegPricing` or `TrailPricing`, or None to use the template's own order type and price.
            cap: A plan_part.PlanPart `CapModifier`, the worst price the rule may set, or None.
            discretion: A plan_part.PlanPart `DiscretionModifier`, or None.
            execution: A plan_part.PlanPart execution, such as `TwapExecution` or `IcebergExecution`, or None to send the order all at once.
            inner_execution: A plan_part.PlanPart execution that works each piece `execution` releases, such as an `IcebergExecution` inside a `TwapExecution`, or None. It needs `execution`.
            guard: A plan_part.PlanPart `PostOnlyGuard`, or None.
            lifetime: A plan_part.PlanPart `Lifetime`, or None.
            venue: A plan_part.PlanPart `PreOpenVenue` or `PaperVenue`, or None.
            quantity: An int quantity, a plan_part.PlanPart quantity such as `PositionQuantity` or `ParentFillQuantity`, or None.
            instrument: The instruments.TradeableInstrument this order trades instead of the plan's, or None.
            transaction_type: The str side of this order's own body, `buy` or `sell`, or None.
            product: The str product of this order's own body, `cnc`, `mis` or `nrml`, or None.
            validity: The str validity of this order's own body, `day` or `ioc`, or None.
            tag: The str tag of this order's own body, or None.

        Raises:
            Nothing.
        """
        self.presets = None
        if presets is not None:
            self.presets = list(presets)
        self.trigger = trigger
        self.side = side
        self.pricing = pricing
        self.cap = cap
        self.discretion = discretion
        self.execution = execution
        self.inner_execution = inner_execution
        self.guard = guard
        self.lifetime = lifetime
        self.venue = venue
        self.quantity = quantity
        self.instrument = instrument
        self.transaction_type = transaction_type
        self.product = product
        self.validity = validity
        self.tag = tag

    def document(self) -> dict:
        """Builds the `order` node UBI reads, holding every setting that is not None.

        Returns:
            A dict with the single key `order`, whose value holds each setting that is set. UBI takes `pricing`, `execution`, `guards`, `lifetime` and `venue` as lists: the pricing rule, cap and discretion go in one `pricing` list, the execution and inner execution in one `execution` list, and the guard, lifetime and venue each in a list of one. An instrument is sent as its `instrument_id`.

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

            Print an order pegged to the bid but never above 1010, sent as a TWAP of icebergs that ends at 14:30:

            ```python
            from tradingmachine.orders.plan_parts import cap_modifier
            from tradingmachine.orders.plan_parts import iceberg_execution
            from tradingmachine.orders.plan_parts import lifetime
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import peg_pricing
            from tradingmachine.orders.plan_parts import twap_execution

            part = order_part.OrderPart(
                pricing=peg_pricing.PegPricing(reference="own_touch"),
                cap=cap_modifier.CapModifier(worst_price=1010.0),
                execution=twap_execution.TwapExecution(
                    slices=6,
                    over_minutes=60,
                ),
                inner_execution=iceberg_execution.IcebergExecution(
                    visible_quantity=10,
                ),
                lifetime=lifetime.Lifetime(at_time="14:30"),
            )
            print(part.document())
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
        pricing_documents = []
        if self.pricing is not None:
            pricing_documents.append(self.pricing.document())
        if self.cap is not None:
            pricing_documents.append(self.cap.document())
        if self.discretion is not None:
            pricing_documents.append(self.discretion.document())
        if pricing_documents:
            settings["pricing"] = pricing_documents
        execution_documents = []
        if self.execution is not None:
            execution_documents.append(self.execution.document())
        if self.inner_execution is not None:
            execution_documents.append(self.inner_execution.document())
        if execution_documents:
            settings["execution"] = execution_documents
        if self.guard is not None:
            settings["guards"] = [
                self.guard.document(),
            ]
        if self.lifetime is not None:
            settings["lifetime"] = [
                self.lifetime.document(),
            ]
        if self.venue is not None:
            settings["venue"] = [
                self.venue.document(),
            ]
        if isinstance(self.quantity, plan_part.PlanPart):
            settings["quantity"] = self.quantity.document()
        elif self.quantity is not None:
            settings["quantity"] = self.quantity
        if self.instrument is not None:
            settings["instrument_id"] = self.instrument.instrument_id
        if self.transaction_type is not None:
            settings["transaction_type"] = self.transaction_type
        if self.product is not None:
            settings["product"] = self.product
        if self.validity is not None:
            settings["validity"] = self.validity
        if self.tag is not None:
            settings["tag"] = self.tag
        return {
            "order": settings,
        }
