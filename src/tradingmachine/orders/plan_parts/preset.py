"""A preset in a plan: one of the existing synthetic order types used as an ingredient of an order.

A preset stands for slot values, or for a whole join, and takes the settings of the type it is named after, so `Preset("bracket", stop_price=990.0, stop_limit_price=988.0, target_price=1010.0)` makes an order a bracket. The preset names and their settings are UBI's, and UBI refuses a name it does not offer yet, so new presets work here as soon as UBI adds them.

Typical usage example:

  part = preset.Preset("market_if_touched", trigger_price=995.0)
  document = part.document()
"""

from typing import Any

from tradingmachine.orders.plan_parts import plan_part


class Preset(plan_part.PlanPart):
    """One named preset and its settings.

    Attributes:
        name: The str name of the preset, such as `bracket`, `trailing_stop` or `scheduled`.
        settings: The dict of the preset's settings, keyed by UBI's field names.
    """

    def __init__(
        self,
        name: str,
        **settings: Any,
    ):
        """Initialises the preset with its name and settings.

        Args:
            name: The str name of the preset, as UBI names the synthetic order type, such as `bracket`, `oto` or `hidden_stop`.
            **settings: The preset's settings by UBI's field names, such as `trigger_price=995.0`.

        Raises:
            Nothing.
        """
        self.name = name
        self.settings = settings

    def document(self) -> dict:
        """Builds the preset object UBI reads.

        Returns:
            A dict with the single key `name`, whose value is the dict of settings.

        Raises:
            Nothing.

        Examples:
            Print a preset that makes an order wait for the price to touch 995:

            ```python
            from tradingmachine.orders.plan_parts import preset

            part = preset.Preset("market_if_touched", trigger_price=995.0)
            print(part.document())
            ```

            Print a bracket preset, which stands for a whole then join around the order:

            ```python
            from tradingmachine.orders.plan_parts import preset

            part = preset.Preset(
                "bracket",
                stop_price=990.0,
                stop_limit_price=988.0,
                target_price=1010.0,
            )
            print(part.document())
            ```

            Print a preset that takes no settings:

            ```python
            from tradingmachine.orders.plan_parts import preset

            print(preset.Preset("simple").document())
            ```
        """
        return {
            self.name: dict(self.settings),
        }
