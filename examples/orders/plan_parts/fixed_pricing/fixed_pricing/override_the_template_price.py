"""Show what each fixed pricing setting takes from the template and what it overrides.

An empty `FixedPricing` keeps the template's own order type and price, giving only a price keeps the template's order type, and giving both overrides it completely. The program prints the three objects with a note on what each sends, so a plan's last order can reuse the template or depart from it. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/fixed_pricing/fixed_pricing/override_the_template_price.py
"""

from tradingmachine.orders.plan_parts import fixed_pricing


class TemplateOverrides:
    """Three fixed pricing rules that override more and more of the template.

    Attributes:
        rules: The list of tuples (note, rule), where note is a str and rule is a tradingmachine.orders.plan_parts.fixed_pricing.FixedPricing.
    """

    def __init__(self):
        """Builds the rules.

        Raises:
            Nothing.
        """
        self.rules = [
            (
                "the template's order type and price",
                fixed_pricing.FixedPricing(),
            ),
            (
                "the template's order type at 1005",
                fixed_pricing.FixedPricing(price=1005.0),
            ),
            (
                "a limit at 1005, whatever the template says",
                fixed_pricing.FixedPricing(price=1005.0, order_type="LIMIT"),
            ),
        ]

    def run(self) -> None:
        """Prints each rule's object and what it sends.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for note, rule in self.rules:
            print(f"{str(rule.document()):52} sends {note}")


if __name__ == "__main__":
    TemplateOverrides().run()
