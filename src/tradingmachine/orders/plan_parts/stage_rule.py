"""One milestone of a `stages` stop: a gain that, once reached, moves the stop or hands it to a trail.

The `gain` is measured from the stop's entry price in the position's favour. A rule with `stop_at_gain` moves the stop to that gain measured the same way, so 0 is breakeven, and a rule with `trail_points` hands the rest of the trade to an ordinary trail that many rupees behind. A rule takes exactly one of the two, and a trailing rule must be the last one.

Typical usage example:

  rule = stage_rule.StageRule(gain=10.0, stop_at_gain=0.0)
  entry = rule.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class StageRule(plan_part.PlanPart):
    """One milestone of a stepped stop, an entry of the `rules` list of `StagesPricing`.

    Attributes:
        gain: The float gain in rupees, from the entry price in the position's favour, that applies the rule.
        stop_at_gain: The float gain in rupees where the stop goes, below `gain`, with 0 for breakeven, or None when `trail_points` is given.
        trail_points: The float distance in rupees the stop trails from here on, or None when `stop_at_gain` is given.
    """

    def __init__(
        self,
        *,
        gain: float,
        stop_at_gain: float | None = None,
        trail_points: float | None = None,
    ):
        """Initialises the milestone with its gain and what happens there.

        Args:
            gain: The float gain in rupees, above zero, from the entry price in the position's favour, that applies the rule.
            stop_at_gain: The float gain in rupees where the stop goes, below `gain`, with 0 for breakeven and a negative value for a smaller loss, or None when `trail_points` is given.
            trail_points: The float distance in rupees the stop trails behind the market from here on, or None when `stop_at_gain` is given.

        Raises:
            Nothing.
        """
        self.gain = gain
        self.stop_at_gain = stop_at_gain
        self.trail_points = trail_points

    def document(self) -> dict:
        """Builds the milestone object UBI reads as one entry of a `stages` rule list.

        Returns:
            A dict holding `gain` and whichever of `stop_at_gain` and `trail_points` is set, directly rather than under a name, because it is an entry of a list.

        Raises:
            Nothing.

        Examples:
            Print a milestone that moves the stop to breakeven once the trade is ten rupees up:

            ```python
            from tradingmachine.orders.plan_parts import stage_rule

            rule = stage_rule.StageRule(gain=10.0, stop_at_gain=0.0)
            print(rule.document())
            ```

            Print a last milestone that starts a five-rupee trail once the trade is thirty rupees up:

            ```python
            from tradingmachine.orders.plan_parts import stage_rule

            rule = stage_rule.StageRule(gain=30.0, trail_points=5.0)
            print(rule.document())
            ```
        """
        settings = {
            "gain": self.gain,
        }
        if self.stop_at_gain is not None:
            settings["stop_at_gain"] = self.stop_at_gain
        if self.trail_points is not None:
            settings["trail_points"] = self.trail_points
        return settings
