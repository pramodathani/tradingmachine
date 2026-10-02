"""The `stages` pricing rule of a plan: a stop-limit at the broker that profit milestones move in the position's favour.

The stop starts at `stop_price`, with its limit `limit_offset` past the trigger, and rests at the broker the whole time. Each `StageRule` names a gain from `entry_price`, and once the market reaches it the stop is modified to the rule's `stop_at_gain`, or handed to a trail of `trail_points`. The stop only ever moves in the position's favour, by at least `step_ticks`, so a rule that would loosen it is skipped. UBI takes 1 to 20 rules with rising gains, each with exactly one of `stop_at_gain` and `trail_points`, and only the last may trail. Like every stop, it cannot be split into pieces.

Typical usage example:

  pricing = stages_pricing.StagesPricing(
      entry_price=1000.0,
      stop_price=990.0,
      limit_offset=1.0,
      rules=[
          stage_rule.StageRule(gain=10.0, stop_at_gain=0.0),
          stage_rule.StageRule(gain=25.0, trail_points=8.0),
      ],
  )
  document = pricing.document()
"""

from collections.abc import Sequence

from tradingmachine.orders.plan_parts import plan_part


class StagesPricing(plan_part.PlanPart):
    """A pricing rule that rests a stop-limit at the broker and steps it through profit milestones.

    Attributes:
        entry_price: The float price in rupees the gains are measured from.
        stop_price: The float price in rupees where the stop starts.
        limit_offset: The float distance in rupees between the stop's trigger and its limit.
        rules: The list of plan_part.PlanPart milestones, `StageRule` objects, in order of rising gain.
        step_ticks: The int smallest move in ticks, or None for UBI's default of 1.
    """

    def __init__(
        self,
        *,
        entry_price: float,
        stop_price: float,
        limit_offset: float,
        rules: Sequence[plan_part.PlanPart],
        step_ticks: int | None = None,
    ):
        """Initialises the rule with its prices and milestones.

        Args:
            entry_price: The float price in rupees the gains are measured from, usually where the position was opened.
            stop_price: The float price in rupees where the stop starts.
            limit_offset: The float distance in rupees between the stop's trigger and its limit.
            rules: A sequence of 1 to 20 `StageRule` objects, each with a larger gain than the one before, of which only the last may trail.
            step_ticks: The int smallest move in ticks, or None for UBI's default of 1.

        Raises:
            Nothing.
        """
        self.entry_price = entry_price
        self.stop_price = stop_price
        self.limit_offset = limit_offset
        self.rules = list(rules)
        self.step_ticks = step_ticks

    def document(self) -> dict:
        """Builds the `stages` pricing object UBI reads.

        Returns:
            A dict with the single key `stages`, whose value holds `entry_price`, `stop_price`, `limit_offset`, `step_ticks` when it is set, and `rules` as a list of each milestone's object.

        Raises:
            Nothing.

        Examples:
            Print a stop that moves to breakeven ten rupees up and to a five-rupee gain twenty rupees up:

            ```python
            from tradingmachine.orders.plan_parts import stage_rule
            from tradingmachine.orders.plan_parts import stages_pricing

            pricing = stages_pricing.StagesPricing(
                entry_price=1000.0,
                stop_price=990.0,
                limit_offset=1.0,
                rules=[
                    stage_rule.StageRule(gain=10.0, stop_at_gain=0.0),
                    stage_rule.StageRule(gain=20.0, stop_at_gain=5.0),
                ],
            )
            print(pricing.document())
            ```

            Print a stop that moves to breakeven and then trails eight rupees behind, moving in steps of two ticks:

            ```python
            from tradingmachine.orders.plan_parts import stage_rule
            from tradingmachine.orders.plan_parts import stages_pricing

            pricing = stages_pricing.StagesPricing(
                entry_price=1000.0,
                stop_price=990.0,
                limit_offset=1.0,
                rules=[
                    stage_rule.StageRule(gain=10.0, stop_at_gain=0.0),
                    stage_rule.StageRule(gain=25.0, trail_points=8.0),
                ],
                step_ticks=2,
            )
            print(pricing.document())
            ```
        """
        rule_documents = []
        for rule in self.rules:
            rule_documents.append(rule.document())
        settings = {
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
            "limit_offset": self.limit_offset,
        }
        if self.step_ticks is not None:
            settings["step_ticks"] = self.step_ticks
        settings["rules"] = rule_documents
        return {
            "stages": settings,
        }
