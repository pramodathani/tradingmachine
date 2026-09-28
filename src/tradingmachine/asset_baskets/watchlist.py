"""A watchlist: instruments followed together, with no weights or quantities.

`Watchlist` weights every member equally, so its day move is the plain average of its members' and its candles are an equal-weighted index of them. It exists to be looked at: `rank_by` sorts the members by any column of `ohlc`, and the inherited `top_gainers`, `top_losers` and `breadth` say what moved.

Typical usage example:

  followed = watchlist.Watchlist(name="banks", instruments=[hdfc_bank, icici_bank, axis_bank])
  table = followed.rank_by("change_percent")
  movers = followed.top_gainers(count=2)
"""

import pandas as pd

from tradingmachine.asset_baskets import asset_basket
from tradingmachine.asset_baskets import basket_member
from tradingmachine.assets import instruments
from tradingmachine.unified_broker_interface import client


class Watchlist(asset_basket.AssetBasket):
    """A group of instruments followed together, each counting equally."""

    KIND = "watchlist"

    def __init__(
        self,
        name: str,
        instruments: list[instruments.Instrument],
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Initialises the watchlist with its instruments.

        Args:
            name: The str name of the watchlist.
            instruments: A list of at least one tradingmachine.assets.instruments.Instrument, each different.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share the one every instrument uses.

        Raises:
            BasketMemberError: instruments is empty or names an instrument twice.
        """
        members = []
        for instrument in instruments:
            members.append(basket_member.BasketMember(instrument))
        super().__init__(
            name=name,
            members=members,
            unified_broker_interface=unified_broker_interface,
        )

    def add(self, instrument: instruments.Instrument) -> None:
        """Adds an instrument to the watchlist in memory, which `BasketStore.save` then stores.

        Args:
            instrument: The tradingmachine.assets.instruments.Instrument to add.

        Returns:
            None.

        Raises:
            BasketMemberError: The instrument is already in the watchlist.
        """
        self.add_member(basket_member.BasketMember(instrument))

    def rank_by(
        self, column: str = "change_percent", ascending: bool = False
    ) -> pd.DataFrame:
        """Sorts the members by a column of their day's prices.

        Args:
            column: The str name of an `ohlc` column, such as `change_percent` or `last_price`.
            ascending: A bool that is True to put the smallest value first.

        Returns:
            A pandas.DataFrame of `ohlc` rows in the chosen order, with members that have no value for the column last.

        Raises:
            KeyError: column is not a column of `ohlc`.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        frame = self.ohlc
        return frame.sort_values(
            column, ascending=ascending, na_position="last"
        ).reset_index(drop=True)
