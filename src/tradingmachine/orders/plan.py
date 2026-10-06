"""The `plan` synthetic order type: an order described as a tree of parts rather than one fixed type.

A plan combines the existing synthetic order types and their building blocks in one order. Its orders can wait for a trigger, protect or close a position, be priced and capped, be sent in pieces over time, end on their own and trade other instruments, set either by presets named after the existing types or by slot values, and they are joined with `ThenPart`, `EitherPart`, `TogetherPart`, `SequencePart`, `RepeatPart` and `UsingPart`. The parts live in `tradingmachine.orders.plan_parts`, and the order template, the instrument, side, quantity, product and validity, is the same as every other type's.

UBI checks the whole plan before recording or sending anything and refuses a plan with any problem with HTTP 400, listing every problem with the `path` where the caller wrote the value it is about, its `rule` and a `message`. A problem inside something UBI builds from what the caller wrote, a preset that stands for a join such as a `bracket`, a repeat's copies or a using's pieces, also gives `part`, the part as it runs: a bad stop price in a bracket preset is reported at `root.presets.0` with a `part` such as `root.each_fill.children.0`, and the message may still name the setting the preset becomes, such as `trigger_price` for the bracket's `stop_price`. A dry run makes the checks placing makes, so it can be refused with HTTP 409 and the rule `protect_needs_position`, or with HTTP 400 for a price off the tick, just as placing would. A plan that places nothing at once answers HTTP 202 with an `outcome` of `armed`. UBI holds each order that would rest at the broker at a fixed limit price in its virtual order book until the other side of the book reaches it, while UBI's `UNIFIED_BROKER_INTERFACE_API_ORDER_HOLD_LIMITS` switch is on and the plan does not say otherwise; follow-on orders in a Then join's child, such as exits, and orders on the `protect` side rest at the broker unless their own `OrderPart` asks to be held. When a plan is refused after some of its orders have reached a broker, the refused order is listed in the answer's `legs` with its reason and the others stay watched.

Typical usage example:

  order = plan.PlanOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=1000.0,
      plan=then_part.ThenPart(
          first=order_part.OrderPart(),
          each_fill=order_part.OrderPart(
              side="protect",
              pricing=trail_pricing.TrailPricing(points=5.0, limit_offset=1.0),
          ),
      ),
      dry_run=True,
  )
  answer = order.place()
"""

import pandas as pd

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order
from tradingmachine.orders.plan_parts import plan_part


class PlanOrder(synthetic_order.SyntheticOrder):
    """An order described as a tree of parts, which can combine the other synthetic order types.

    A plan combines the existing synthetic order types and their building blocks in one order. Its orders can wait for a trigger, protect or close a position, be priced and capped, be sent in pieces over time, end on their own and trade other instruments, and they are joined with `ThenPart`, `EitherPart`, `TogetherPart`, `SequencePart`, `RepeatPart` and `UsingPart` from `tradingmachine.orders.plan_parts`. An order inside a join is sized by the join, and only the plan's main order carries the template's `tag`.

    A plan that traded but whose order meant to follow the trade was refused, such as a hedge, a spread's second leg or a strategy stop's close, ends `failed` rather than `completed`, because a position may be left without it, and the parent's message names the part.

    After `place()`, each part of the plan is named by its path, such as `root.first` for a bracket's entry or `root.each_fill.children.0` for its stop. `parts` lists them, and `cancel_part` and `modify_part` act on one part while the rest of the plan carries on.

    The order template's attributes are described on `SyntheticOrder`.

    Attributes:
        plan: The plan_part.PlanPart at the root of the tree, an `OrderPart`, a `ThenPart` or an `EitherPart`.
    """

    SYNTHETIC_TYPE = "plan"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        plan: plan_part.PlanPart,
        price: float | None = None,
        trigger_price: float | None = None,
        validity: str | None = None,
        disclosed_quantity: int | None = None,
        after_market: bool = False,
        tag: str | None = None,
        price_reference: dict | None = None,
        quantity_reference: dict | None = None,
        closes_position: bool = False,
        reduce_only: bool = False,
        hold_limits: bool | None = None,
        dry_run: bool = False,
    ):
        """Initialises the order template and the plan.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`, which is also the side a `protect` order trades against.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            plan: The plan_part.PlanPart at the root of the tree, an `OrderPart`, a `ThenPart` or an `EitherPart`.
            price: The float limit price in rupees, or None for an order type that takes no price or when a price reference supplies it.
            trigger_price: The float trigger price in rupees of the order itself, or None for an order type that takes no trigger.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            disclosed_quantity: The int quantity to show on the exchange, or None to disclose the whole order.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the plan's main order with, or None.
            price_reference: A dict describing the price for UBI to work out, such as `{"kind": "mid"}`, or None.
            quantity_reference: A dict describing the quantity for UBI to work out, such as `{"kind": "liquidate_position"}`, or None.
            closes_position: A bool that is True when every order this plan sends closes a position, so it may use the share of a broker's daily order cap kept for exits.
            reduce_only: A bool that is True to have UBI refuse, with HTTP 409, any leg that is not on the closing side of the net position held when it is sent or is bigger than that position.
            hold_limits: A bool that is True to have UBI hold each order of the plan that would rest at the broker at a fixed limit price until the other side of the book reaches it, False to send them as they come, or None to follow UBI's `UNIFIED_BROKER_INTERFACE_API_ORDER_HOLD_LIMITS` switch. An `OrderPart`'s own `hold_limits` decides for that order.
            dry_run: A bool that is True to have UBI build the first broker request and return it, with the plan as it would run, without recording or sending anything. UBI makes the checks placing makes, so a dry run is refused with HTTP 409 or 400 wherever placing would be, and in the plan each order shows `own_values`, the values it gives over the template's such as another `instrument_id` or `transaction_type`, its own side, and where its quantity comes from.

        Raises:
            Nothing.
        """
        super().__init__(
            instrument,
            transaction_type=transaction_type,
            product=product,
            order_type=order_type,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            validity=validity,
            disclosed_quantity=disclosed_quantity,
            after_market=after_market,
            tag=tag,
            price_reference=price_reference,
            quantity_reference=quantity_reference,
            closes_position=closes_position,
            reduce_only=reduce_only,
            hold_limits=hold_limits,
            dry_run=dry_run,
        )
        self.plan = plan

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict with the single key `plan`, whose value is the object the plan's root part builds.

        Raises:
            Nothing.

        Examples:
            Print the plan of a limit buy followed by a trailing stop sized to each fill:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import plan
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import then_part
            from tradingmachine.orders.plan_parts import trail_pricing

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = plan.PlanOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
                plan=then_part.ThenPart(
                    first=order_part.OrderPart(),
                    each_fill=order_part.OrderPart(
                        side="protect",
                        pricing=trail_pricing.TrailPricing(points=0.3, limit_offset=0.05),
                    ),
                ),
            )
            print(order.synthetic_fields())
            ```

            Print the whole synthetic object of a bracket whose entry waits for a touch, two existing types combined as presets:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import plan
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import preset

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = plan.PlanOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=12.9,
                plan=order_part.OrderPart(
                    presets=[
                        preset.Preset("market_if_touched", trigger_price=12.9),
                        preset.Preset(
                            "bracket",
                            stop_price=12.5,
                            stop_limit_price=12.45,
                            target_price=13.6,
                        ),
                    ],
                ),
            )
            print(order.synthetic)
            ```
        """
        return {
            "plan": self.plan.document(),
        }

    @property
    def parts(self) -> pd.DataFrame | None:
        """The parts of the placed plan as UBI's order engine holds them now, one row per part, read from UBI on every access.

        Each row has the part's `path`, such as `root.each_fill.children.0`, and the fields of UBI's record for it: `state`, which is `pending`, `waiting`, `working` or `done`, and, when UBI has set them, `reason`, `target`, `memory`, `fired_at` and others. A done part's `reason` is `filled`, `partly_filled`, `refused` or `cancelled`, or `expired` when a lifetime or a pre-open ended it, `closed` when a lifetime's end closed what it traded, and `nothing_held` when a close found nothing to close. The rows are sorted by path.

        The parent ends once every part is done: `failed` when something traded but an order meant to follow it was refused, `completed` when anything traded, `rejected` when a broker refused an order and nothing traded, and `cancelled` otherwise. A parent cancelled whole with `cancel()` ends `cancelled` with every part marked done.

        Raises:
            ValueError: The order has not been placed, so there is no parent to read.
            NotFoundError: The engine holds no parent with this id.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Place a buy 3% below the market with a stop behind each fill, and print the state of each part:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import plan
            from tradingmachine.orders.plan_parts import native_stop_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import then_part

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = plan.PlanOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
                plan=then_part.ThenPart(
                    first=order_part.OrderPart(),
                    each_fill=order_part.OrderPart(
                        side="protect",
                        pricing=native_stop_pricing.NativeStopPricing(
                            trigger_price=round(limit_price * 0.97, 2),
                            limit_price=round(limit_price * 0.96, 2),
                        ),
                    ),
                ),
            )
            order.place()
            try:
                print(order.parts[["path", "state"]])
            finally:
                order.cancel()
            ```

            Find the parts that are still waiting for their turn:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import plan
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import price_crosses

            share = equities.Equity(exchange="nse", symbol="IDEA")
            level = round(share.last_price * 0.95, 2)
            order = plan.PlanOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="market",
                quantity=1,
                plan=order_part.OrderPart(
                    trigger=price_crosses.PriceCrosses(level=level),
                ),
            )
            order.place()
            try:
                parts = order.parts
                waiting = parts[parts["state"] == "waiting"]
                print(waiting["path"].tolist())
            finally:
                order.cancel()
            ```
        """
        records = self.parent.get("parameters", {}).get("parts") or {}
        rows = []
        for path in sorted(records):
            row = {
                "path": path,
            }
            row.update(records[path])
            rows.append(row)
        if not rows:
            return None
        return pd.DataFrame(rows)

    def cancel_part(self, part: str, dry_run: bool = False) -> dict:
        """Cancels one part of the placed plan, leaving the rest of it running.

        A part whose turn has not come is never sent, a part waiting on its trigger is ended at once, and a part that has sent orders sends no more pieces and has each of its resting orders cancelled. The plan then reacts as it does to that part finishing, so a bracket whose entry is cancelled before it fills drops its exits.

        Cancelling one of the plan's broker orders by its `order_id` through `TradeableInstrument.cancel_order` instead cancels that order alone, and the plan does not send it again: for an order sent whole, its unfilled quantity comes off what its part trades, so a later fill of the entry is still protected for the new quantity only, and a bracket's stop cancelled this way stays cancelled.

        Args:
            part: The str path of the part, such as `root.each_fill.children.0`, as `parts` lists it.
            dry_run: A bool that is True to have UBI list the part's resting `orders` without cancelling anything.

        Returns:
            The dict `TradeableInstrument.cancel_parent` returns for a part, with `parent_id`, `synthetic_type`, `part`, its `state`, `outcome`, `status_message`, `intent_id` and `orders`, where each order's `cancel_accepted` says whether its broker accepted the cancel. HTTP 207 with an `outcome` of `partial` or `rejected` is returned rather than raised.

        Raises:
            ValueError: The order has not been placed, so there is no parent to act on.
            BadRequestError: The part path is malformed.
            NotFoundError: The engine holds no parent with this id, or the plan has no part at this path.
            ConflictError: The part has already finished, or is kept whole and has not started, or the plan has finished.
            ServiceUnavailableError: The order engine is not running.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Place a buy below the market with a stop and a target behind it, then drop the target before the entry fills, leaving the stop:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import plan
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import preset

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = plan.PlanOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
                plan=order_part.OrderPart(
                    presets=[
                        preset.Preset(
                            "bracket",
                            stop_price=round(limit_price * 0.97, 2),
                            stop_limit_price=round(limit_price * 0.96, 2),
                            target_price=round(limit_price * 1.05, 2),
                        ),
                    ],
                ),
            )
            order.place()
            try:
                answer = order.cancel_part("root.each_fill.children.1")
                print(answer["state"], answer["status_message"])
                print(order.parts[["path", "state"]])
            finally:
                order.cancel()
            ```

            Ask what cancelling the entry would do, without cancelling it:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import plan
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import preset

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = plan.PlanOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
                plan=order_part.OrderPart(
                    presets=[
                        preset.Preset(
                            "cover",
                            stop_price=round(limit_price * 0.97, 2),
                            stop_limit_price=round(limit_price * 0.96, 2),
                        ),
                    ],
                ),
            )
            order.place()
            try:
                print(order.cancel_part("root.first", dry_run=True))
            finally:
                order.cancel()
            ```
        """
        return self.instrument.cancel_parent(
            self._placed_parent_id(),
            part=part,
            dry_run=dry_run,
        )

    def modify_part(
        self,
        part: str,
        price: float | None = None,
        trigger_price: float | None = None,
        quantity: int | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Changes one part of the placed plan that has not sent anything yet, such as a bracket's stop before the entry fills.

        The part keeps the new values and sends them when its turn comes, and nothing is sent to a broker now. Only a part with a fixed price, a plain limit or a native stop, takes a price, and only a stop takes a trigger price. A part that has already sent its order is changed through `TradeableInstrument.modify_order` with that order's id instead.

        Args:
            part: The str path of the part, such as `root.each_fill.children.0`, as `parts` lists it.
            price: The float new limit price in rupees, or None to leave it.
            trigger_price: The float new trigger price in rupees of a stop, or None to leave it.
            quantity: The int new total quantity, or None to leave it. An order that closes a position can only be reduced.
            dry_run: A bool that is True to have UBI check the change without making it.

        Returns:
            The dict `TradeableInstrument.modify_order` returns for a part, with `parent_id`, `synthetic_type`, `part`, its `state`, the new `price`, `trigger_price` and `quantity`, `outcome`, `status_message` and `intent_id`.

        Raises:
            ValueError: The order has not been placed, so there is no parent to act on.
            BadRequestError: No value was given, the part works its price out from the market, the part is not a stop and was given a trigger price, or a value is off the tick or lot.
            NotFoundError: The engine holds no parent with this id, or the plan has no part at this path.
            ConflictError: The part has already sent its order, when the detail lists its `orders`; it is sized by an earlier part's fills; it is kept whole; it closes a position and was asked to grow; or the plan has finished.
            ServiceUnavailableError: The order engine is not running.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Place a buy below the market with a bracket behind it, then lower the stop before the entry fills:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import plan
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import preset

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = plan.PlanOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
                plan=order_part.OrderPart(
                    presets=[
                        preset.Preset(
                            "bracket",
                            stop_price=round(limit_price * 0.97, 2),
                            stop_limit_price=round(limit_price * 0.96, 2),
                            target_price=round(limit_price * 1.05, 2),
                        ),
                    ],
                ),
            )
            order.place()
            try:
                answer = order.modify_part(
                    "root.each_fill.children.0",
                    trigger_price=round(limit_price * 0.95, 2),
                    price=round(limit_price * 0.94, 2),
                )
                print(answer["trigger_price"], answer["price"], answer["status_message"])
            finally:
                order.cancel()
            ```

            Check a change to the target with a dry run, which changes nothing:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import plan
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import preset

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = plan.PlanOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
                plan=order_part.OrderPart(
                    presets=[
                        preset.Preset(
                            "bracket",
                            stop_price=round(limit_price * 0.97, 2),
                            stop_limit_price=round(limit_price * 0.96, 2),
                            target_price=round(limit_price * 1.05, 2),
                        ),
                    ],
                ),
            )
            order.place()
            try:
                answer = order.modify_part(
                    "root.each_fill.children.1",
                    price=round(limit_price * 1.08, 2),
                    dry_run=True,
                )
                print(answer)
            finally:
                order.cancel()
            ```
        """
        return self.instrument.modify_order(
            parent_id=self._placed_parent_id(),
            part=part,
            price=price,
            trigger_price=trigger_price,
            quantity=quantity,
            dry_run=dry_run,
        )
