"""The `plan` synthetic order type: an order described as a tree of parts rather than one fixed type.

A plan combines the existing synthetic order types and their building blocks in one order. Its orders can wait for a trigger, protect a position, trail the market and be priced by one pricing rule, set either by presets named after the existing types or by slot values, and they are joined with `ThenPart` and `EitherPart`. The parts live in `tradingmachine.orders.plan_parts`, and the order template, the instrument, side, quantity, product and validity, is the same as every other type's.

UBI checks the whole plan before recording or sending anything and refuses a plan with any problem with HTTP 400, listing every problem with the path of the part it is in. A plan that places nothing at once answers HTTP 202 with an `outcome` of `armed`. UBI has also built the joins `together`, `using`, `repeat` and `sequence`, which have no class here yet.

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

from tradingmachine.assets import instruments
from tradingmachine.orders import synthetic_order
from tradingmachine.orders.plan_parts import plan_part


class PlanOrder(synthetic_order.SyntheticOrder):
    """An order described as a tree of parts, which can combine the other synthetic order types.

    A plan combines the existing synthetic order types and their building blocks in one order. Its orders can wait for a trigger, protect a position, trail the market and be priced by one pricing rule, and they are joined with `ThenPart` and `EitherPart` from `tradingmachine.orders.plan_parts`. An order inside a join is sized by the join, and only the plan's main order carries the template's `tag`.

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
            dry_run: A bool that is True to have UBI build the first broker request and return it, with the plan as it would run, without recording or sending anything.

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
