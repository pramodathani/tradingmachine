"""Preview a plain market sell and a marketable limit sell with a wider buffer, and compare the plans UBI would run.

The program asks UBI for two dry runs of selling one Vodafone Idea share intraday. The first is an ordinary `sell_at_market_price`, which UBI's order engine turns into a `marketable_limit` order with its default buffer of two ticks and its default thirty seconds. The second names the type itself with a buffer of five ticks and a minute to fill. It prints the pricing and lifetime of each plan. A dry run records and sends nothing.

Typical usage example:

  .venv/bin/python examples/orders/marketable_limit/marketable_limit_order/preview_plain_market_sell_and_wide_buffer.py
"""

from tradingmachine.assets import equities
from tradingmachine.orders import marketable_limit


class MarketSellPreviews:
    """Two previews of a one-share market sell, one plain and one with its own buffer and time.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
    """

    def __init__(self):
        """Looks up the share the program previews.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def plain_market_sell(self) -> dict:
        """Asks UBI for a dry run of an ordinary market sell.

        Returns:
            The dict dry run answer, holding the `request` as written and the `plan` UBI would run.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or could not be reached.
        """
        return self.share.place_order(
            transaction_type="sell",
            order_type="market",
            quantity=1,
            product="mis",
            dry_run=True,
        )

    def wide_buffer_sell(self) -> dict:
        """Asks UBI for a dry run of a marketable limit sell five ticks through the bid that works for a minute.

        Returns:
            The dict dry run answer, holding the `request` as written and the `plan` UBI would run.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or could not be reached.
        """
        order = marketable_limit.MarketableLimitOrder(
            self.share,
            transaction_type="sell",
            product="mis",
            order_type="market",
            quantity=1,
            buffer_ticks=5,
            fill_within_seconds=60,
            dry_run=True,
        )
        return order.place()

    def print_plan(self, title: str, answer: dict) -> None:
        """Prints the order type the request was written as, and the presets, pricing and lifetime of the plan UBI would run.

        Args:
            title: The str heading to print above the plan.
            answer: The dict dry run answer.

        Returns:
            None.

        Raises:
            Nothing.
        """
        order = answer["plan"]["order"]
        slots = order["slots"]
        print(title)
        print(f"  written as: {answer['request']['form'].get('prctyp')}")
        print(f"  presets: {order.get('presets')}")
        print(f"  pricing: {slots['pricing']}")
        print(f"  lifetime: {slots['lifetime']}")

    def run(self) -> None:
        """Previews both sells and prints their plans.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused an order or could not be reached.
        """
        self.print_plan("A plain market sell:", self.plain_market_sell())
        self.print_plan(
            "A marketable limit sell named in full:", self.wide_buffer_sell()
        )


if __name__ == "__main__":
    MarketSellPreviews().run()
