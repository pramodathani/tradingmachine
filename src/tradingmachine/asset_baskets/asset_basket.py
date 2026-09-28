"""The shared base of every basket of instruments.

`AssetBasket` holds a list of `tradingmachine.asset_baskets.basket_member.BasketMember` and reads what it needs about all of them in one list request to UBI: `POST /api/instruments/ltp`, `/ohlc`, `/quote` and `/prices` each take the whole basket at once and answer one entry per member. The live members report the basket as it stands now, such as its weights, its day move, its breadth and its biggest movers. The history members line up the members' candles and measure how they move together, such as the correlation matrix and each member's share of the risk.

`prices` gives candles for the basket as a whole, the sum over members of a fixed quantity times each member's candle, so the basket inherits every analysis class an instrument does, from moving averages to `sharpe_ratio` and `run_backtest`. A weighted basket turns its weights into quantities at the first candle of the range, starting from `base_value`, which is how a price index moves between rebalances. The open and close are exact. The high and low are the sums of the members' highs and lows, an approximation, because the members do not all reach their highs at the same moment. Volume and open interest have no meaning for a basket and are left empty.

Typical usage example:

  basket = index.Index(name="IT", members=members)
  weights = basket.weights
  movers = basket.top_gainers(count=3)
  matrix = basket.correlation_matrix(days=365)
  ratio = basket.sharpe_ratio(risk_free_rate=0.065, days=365)
"""

import datetime
import math

import pandas as pd

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import exceptions
from tradingmachine.assets import instruments as asset_instruments
from tradingmachine.assets.analysis import candlestick_patterns
from tradingmachine.assets.analysis import cycle_indicators
from tradingmachine.assets.analysis import math_operators
from tradingmachine.assets.analysis import math_transforms
from tradingmachine.assets.analysis import momentum_indicators
from tradingmachine.assets.analysis import overlap_studies
from tradingmachine.assets.analysis import performance_measures
from tradingmachine.assets.analysis import price_statistics
from tradingmachine.assets.analysis import price_transforms
from tradingmachine.assets.analysis import signals
from tradingmachine.assets.analysis import statistic_functions
from tradingmachine.assets.analysis import strategy_backtests
from tradingmachine.assets.analysis import volatility_indicators
from tradingmachine.assets.analysis import volume_indicators
from tradingmachine.unified_broker_interface import client

LAST_PRICE_PATH = "/api/instruments/ltp"

OHLC_PATH = "/api/instruments/ohlc"

QUOTE_PATH = "/api/instruments/quote"

PRICES_PATH = "/api/instruments/prices"

SUCCESS_STATUS = 200

DEFAULT_BASE_VALUE = 100.0

CANDLE_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
]

IDENTITY_COLUMNS = [
    "instrument_id",
    "exchange",
    "segment",
    "symbol",
    "underlying_symbol",
    "expiry_date",
    "strike_price",
    "option_type",
]


class AssetBasket(
    price_statistics.PriceStatistics,
    overlap_studies.OverlapStudies,
    momentum_indicators.MomentumIndicators,
    volume_indicators.VolumeIndicators,
    cycle_indicators.CycleIndicators,
    price_transforms.PriceTransforms,
    volatility_indicators.VolatilityIndicators,
    statistic_functions.StatisticFunctions,
    math_transforms.MathTransforms,
    math_operators.MathOperators,
    candlestick_patterns.CandlestickPatterns,
    signals.Signals,
    strategy_backtests.StrategyBacktests,
    performance_measures.PerformanceMeasures,
):
    """A named group of instruments that is priced, analysed and stored as one.

    Attributes:
        KIND: The str kind of basket a subclass is, such as `index`, stored with the basket so that it is rebuilt as the same class.
        name: The str name of the basket, such as `NIFTY` or `my long-term portfolio`.
        members: The list of basket_member.BasketMember the basket holds, in order.
        linked_instrument: The tradingmachine.assets.instruments.Instrument the basket describes the contents of, such as the NIFTY index or an exchange traded fund, or None when it describes no single instrument.
        unmapped_weight: The float share of the whole, between 0 and 1, held in things UBI cannot price, such as a fund's cash, which the members' weights leave out.
        base_value: The float value the basket's candles start from at the first candle of a range when its members are weighted rather than counted.
    """

    KIND = "basket"

    def __init__(
        self,
        name: str,
        members: list[basket_member.BasketMember],
        linked_instrument: asset_instruments.Instrument | None = None,
        unmapped_weight: float = 0.0,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Initialises the basket and checks its members.

        Args:
            name: The str name of the basket.
            members: A list of basket_member.BasketMember with at least one member, each a different instrument, and either every member or no member given a weight.
            linked_instrument: The tradingmachine.assets.instruments.Instrument whose contents the basket describes, or None.
            unmapped_weight: The float share of the whole, between 0 and 1, held outside the members.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share the one every instrument uses.

        Raises:
            BasketMemberError: members is empty, names an instrument twice, or gives weights to only some members.
            ValueError: unmapped_weight is not between 0 and 1, or no client was given and the shared client is not configured.
        """
        if not 0 <= unmapped_weight < 1:
            raise ValueError(f"Not a share between 0 and 1: {unmapped_weight=}")
        if unified_broker_interface is None:
            unified_broker_interface = (
                asset_instruments.Instrument.shared_unified_broker_interface()
            )
        self._unified_broker_interface = unified_broker_interface
        self.name = name
        self.members = list(members)
        self.linked_instrument = linked_instrument
        self.unmapped_weight = unmapped_weight
        self.base_value = DEFAULT_BASE_VALUE
        self._check_members(self.members)

    @staticmethod
    def _check_members(members: list[basket_member.BasketMember]) -> None:
        """Checks that members can form a basket.

        Args:
            members: The list of basket_member.BasketMember to check.

        Returns:
            None.

        Raises:
            BasketMemberError: members is empty, names an instrument twice, or gives weights to only some members.
        """
        if not members:
            raise exceptions.BasketMemberError("A basket needs at least one member")
        seen_instrument_ids = set()
        weighted_count = 0
        for member in members:
            instrument_id = member.instrument.instrument_id
            if instrument_id in seen_instrument_ids:
                raise exceptions.BasketMemberError(
                    f"An instrument is named twice in the basket: {member.label}"
                )
            seen_instrument_ids.add(instrument_id)
            if member.weight is not None:
                weighted_count += 1
        if 0 < weighted_count < len(members):
            raise exceptions.BasketMemberError(
                f"Only {weighted_count} of {len(members)} members have a weight; give every member a weight or none"
            )

    def __repr__(self) -> str:
        """Describes the basket by its class, name and size.

        Returns:
            A str such as `Index(name='NIFTY', size=50)`.

        Raises:
            Nothing.
        """
        return f"{type(self).__name__}(name={self.name!r}, size={self.size})"

    @property
    def instruments(self) -> list[asset_instruments.Instrument]:
        """The list of tradingmachine.assets.instruments.Instrument the basket holds, in member order."""
        held = []
        for member in self.members:
            held.append(member.instrument)
        return held

    @property
    def size(self) -> int:
        """The int number of members in the basket."""
        return len(self.members)

    @property
    def labels(self) -> list[str]:
        """The list of str member labels, such as `nse:INFY`, in member order."""
        member_labels = []
        for member in self.members:
            member_labels.append(member.label)
        return member_labels

    @property
    def weights(self) -> pd.Series:
        """A pandas.Series of float weights indexed by member label, normalised to sum to 1, or equal weights when no member has a weight."""
        stated = []
        for member in self.members:
            stated.append(member.weight)
        if stated[0] is None:
            equal_weight = 1 / self.size
            return pd.Series(equal_weight, index=self.labels, dtype=float)
        weights = pd.Series(stated, index=self.labels, dtype=float)
        return weights / weights.sum()

    @property
    def last_prices(self) -> pd.DataFrame:
        """A pandas.DataFrame with one row per member, holding `label`, `instrument_id`, `last_price`, `last_trade_time` and an `error` that is None unless UBI had no price for the member, read from UBI in one request on every access."""
        rows = []
        results = self._post_for_every_member(LAST_PRICE_PATH)
        for member, result in zip(self.members, results):
            data = result.get("data") or {}
            rows.append(
                {
                    "label": member.label,
                    "instrument_id": member.instrument.instrument_id,
                    "last_price": data.get("last_price"),
                    "last_trade_time": data.get("last_trade_time"),
                    "error": self._error_of(result),
                }
            )
        return pd.DataFrame(rows)

    @property
    def ohlc(self) -> pd.DataFrame:
        """A pandas.DataFrame with one row per member, holding `label`, `instrument_id`, `open`, `high`, `low`, `last_price`, `previous_close`, `change_percent` and an `error` that is None unless UBI had no quote for the member, read from UBI in one request on every access."""
        rows = []
        results = self._post_for_every_member(OHLC_PATH)
        for member, result in zip(self.members, results):
            data = result.get("data") or {}
            day = data.get("ohlc") or {}
            rows.append(
                {
                    "label": member.label,
                    "instrument_id": member.instrument.instrument_id,
                    "open": day.get("open"),
                    "high": day.get("high"),
                    "low": day.get("low"),
                    "last_price": data.get("last_price"),
                    "previous_close": data.get("previous_close"),
                    "change_percent": data.get("change_percent"),
                    "error": self._error_of(result),
                }
            )
        return pd.DataFrame(rows)

    @property
    def quotes(self) -> pd.DataFrame:
        """A pandas.DataFrame with one row per member, holding `label`, every field of UBI's unified quote such as `last_price`, `volume`, `oi` and `depth`, and an `error` that is None unless UBI had no quote for the member, read from UBI in one request on every access."""
        rows = []
        results = self._post_for_every_member(QUOTE_PATH)
        for member, result in zip(self.members, results):
            row = {
                "label": member.label,
                "instrument_id": member.instrument.instrument_id,
            }
            data = result.get("data") or {}
            for field, value in data.items():
                if field not in row:
                    row[field] = value
            row["error"] = self._error_of(result)
            rows.append(row)
        return pd.DataFrame(rows)

    @property
    def day_change_percent(self) -> float | None:
        """The float weighted move of the basket since the previous close, in percent, such as 0.8, or None when any member has no quote."""
        frame = self.ohlc
        if frame["change_percent"].isna().any():
            return None
        changes = pd.Series(
            frame["change_percent"].to_numpy(dtype=float), index=self.labels
        )
        return float((changes * self.weights).sum())

    @property
    def advancers(self) -> int:
        """The int number of members trading above their previous close, read from UBI on every access."""
        return self.breadth["advancers"]

    @property
    def decliners(self) -> int:
        """The int number of members trading below their previous close, read from UBI on every access."""
        return self.breadth["decliners"]

    @property
    def breadth(self) -> dict:
        """A dict counting the members that are `advancers`, `decliners`, `unchanged` and `unavailable` since the previous close, with the `advance_decline_ratio` of advancers to decliners or None when nothing declined, read from UBI on every access."""
        changes = self.ohlc["change_percent"]
        advancers = int((changes > 0).sum())
        decliners = int((changes < 0).sum())
        unchanged = int((changes == 0).sum())
        unavailable = int(changes.isna().sum())
        ratio = None
        if decliners > 0:
            ratio = advancers / decliners
        return {
            "advancers": advancers,
            "decliners": decliners,
            "unchanged": unchanged,
            "unavailable": unavailable,
            "advance_decline_ratio": ratio,
        }

    @property
    def exposure_by_segment(self) -> pd.Series:
        """A pandas.Series of the float total weight in each segment, such as `nse_equities`, largest first."""
        return self._weights_grouped_by("segment")

    @property
    def exposure_by_exchange(self) -> pd.Series:
        """A pandas.Series of the float total weight on each exchange, such as `nse`, largest first."""
        return self._weights_grouped_by("exchange")

    @property
    def concentration(self) -> float:
        """The float Herfindahl index of the weights, the sum of their squares, which is 1 for a single holding and 1 divided by the size for equal weights."""
        weights = self.weights
        return float((weights**2).sum())

    @property
    def effective_number_of_members(self) -> float:
        """The float number of equal-weighted members that would be as concentrated as this basket, which is 1 divided by the Herfindahl index."""
        return 1 / self.concentration

    @property
    def largest_weight(self) -> float:
        """The float weight of the basket's biggest member."""
        return float(self.weights.max())

    def member_prices(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Fetches every member's candles for a range in one request.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame with one row per member and candle, holding `label`, `instrument_id`, `exchange`, `segment`, `interval`, `datetime` in India time, `open`, `high`, `low`, `close`, `volume` and `oi`, or None when no member has a candle in the range. A member with no candles has no rows.

        Raises:
            BasketMemberError: UBI answered an error for one or more members, all of which the message lists.
            BadRequestError: The range or interval is invalid.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        shared_parameters = {
            "interval": interval,
            "adjusted": bool(adjusted),
        }
        if from_date is not None:
            shared_parameters["from"] = self._date_text(from_date)
        if to_date is not None:
            shared_parameters["to"] = self._date_text(to_date)
        if days is not None:
            shared_parameters["days"] = days
        results = self._post_for_every_member(PRICES_PATH, shared_parameters)
        self._raise_for_failed_members(results)
        frames = []
        for member, result in zip(self.members, results):
            data = result["data"]
            if not data["candles"]:
                continue
            frame = pd.DataFrame(data["candles"], columns=data["columns"])
            frame = frame.rename(columns={"time": "datetime"})
            frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.tz_convert(
                asset_instruments.INDIA_TIME_ZONE
            )
            frame.insert(0, "interval", interval)
            frame.insert(0, "segment", member.instrument.segment)
            frame.insert(0, "exchange", member.instrument.exchange)
            frame.insert(0, "instrument_id", member.instrument.instrument_id)
            frame.insert(0, "label", member.label)
            frames.append(frame)
        if not frames:
            return None
        combined = pd.concat(frames, ignore_index=True)
        return combined.sort_values(
            [
                "label",
                "datetime",
            ]
        ).reset_index(drop=True)

    def member_closes(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Lines up every member's closing prices by time.

        Only the candles every member has are kept, so a member listed during the range shortens it.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame indexed by `datetime` with one float column per member label, or None when any member has no candles in the range or no candle is shared by all.

        Raises:
            BasketMemberError: UBI answered an error for one or more members.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        aligned = self._aligned_candles(interval, from_date, to_date, days, adjusted)
        if aligned is None:
            return None
        return aligned["close"]

    def member_returns(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Calculates every member's return from each shared candle to the next.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame indexed by `datetime` with one float column of fractional returns per member label, or None when there are fewer than two shared candles.

        Raises:
            BasketMemberError: UBI answered an error for one or more members.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        closes = self.member_closes(interval, from_date, to_date, days, adjusted)
        if closes is None or len(closes) < 2:
            return None
        return closes.pct_change().iloc[1:]

    def covariance_matrix(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Calculates the covariance of every pair of members' returns over one candle.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A square pandas.DataFrame indexed and headed by member label, or None when there are fewer than three shared candles.

        Raises:
            BasketMemberError: UBI answered an error for one or more members.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        returns = self.member_returns(interval, from_date, to_date, days, adjusted)
        if returns is None or len(returns) < 2:
            return None
        return returns.cov()

    def correlation_matrix(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Calculates the Pearson correlation of every pair of members' returns.

        A value near 1 means two members rise and fall together and add little diversification to each other.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A square pandas.DataFrame of values between -1 and 1, indexed and headed by member label, or None when there are fewer than three shared candles.

        Raises:
            BasketMemberError: UBI answered an error for one or more members.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        returns = self.member_returns(interval, from_date, to_date, days, adjusted)
        if returns is None or len(returns) < 2:
            return None
        return returns.corr()

    def risk_contributions(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Splits the basket's volatility into each member's share of it, at today's weights.

        A member's share is its weight times its covariance with the whole basket, divided by the basket's variance, so the shares add up to 1. A member whose share is far above its weight is where the basket's risk really sits.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame indexed by member label with float `weight` and `risk_contribution` columns, largest contribution first, or None when there are fewer than three shared candles or the basket never moved.

        Raises:
            BasketMemberError: UBI answered an error for one or more members.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        covariance = self.covariance_matrix(
            interval, from_date, to_date, days, adjusted
        )
        if covariance is None:
            return None
        weights = self.weights.reindex(covariance.columns)
        covariance_with_basket = covariance.dot(weights)
        basket_variance = float(weights.dot(covariance_with_basket))
        if basket_variance == 0:
            return None
        frame = pd.DataFrame(
            {
                "weight": weights,
                "risk_contribution": weights * covariance_with_basket / basket_variance,
            }
        )
        return frame.sort_values("risk_contribution", ascending=False)

    def diversification_ratio(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Divides the weighted average of the members' volatilities by the basket's own volatility, at today's weights.

        It is 1 when every member moves in lockstep, and the further above 1 it is, the more the members' moves cancel out.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float diversification ratio, or None when there are fewer than three shared candles or the basket never moved.

        Raises:
            BasketMemberError: UBI answered an error for one or more members.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        covariance = self.covariance_matrix(
            interval, from_date, to_date, days, adjusted
        )
        if covariance is None:
            return None
        weights = self.weights.reindex(covariance.columns)
        member_volatilities = pd.Series(
            [math.sqrt(covariance.loc[label, label]) for label in covariance.columns],
            index=covariance.columns,
        )
        basket_variance = float(weights.dot(covariance.dot(weights)))
        if basket_variance <= 0:
            return None
        return float(weights.dot(member_volatilities) / math.sqrt(basket_variance))

    def return_contributions(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Splits the basket's return over the range into what each member added.

        Each member's contribution is its share of the basket's value at the first candle times its own return, so the contributions add up to the basket's `cumulative_return` over the same range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame indexed by member label with float `starting_weight`, `member_return` and `contribution` columns, largest contribution first, or None when there are fewer than two shared candles.

        Raises:
            BasketMemberError: UBI answered an error for one or more members.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        closes = self.member_closes(interval, from_date, to_date, days, adjusted)
        if closes is None or len(closes) < 2:
            return None
        first_closes = closes.iloc[0]
        quantities = self._candle_quantities(first_closes)
        starting_values = quantities * first_closes
        starting_weights = starting_values / starting_values.sum()
        member_return = closes.iloc[-1] / first_closes - 1
        frame = pd.DataFrame(
            {
                "starting_weight": starting_weights,
                "member_return": member_return,
                "contribution": starting_weights * member_return,
            }
        )
        return frame.sort_values("contribution", ascending=False)

    def top_gainers(self, count: int = 5) -> pd.DataFrame:
        """Finds the members that have risen most since the previous close.

        Args:
            count: The int most members to return.

        Returns:
            A pandas.DataFrame of `ohlc` rows, biggest rise first, leaving out members with no quote.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        frame = self.ohlc.dropna(subset=["change_percent"])
        frame = frame.sort_values("change_percent", ascending=False)
        return frame.head(count).reset_index(drop=True)

    def top_losers(self, count: int = 5) -> pd.DataFrame:
        """Finds the members that have fallen most since the previous close.

        Args:
            count: The int most members to return.

        Returns:
            A pandas.DataFrame of `ohlc` rows, biggest fall first, leaving out members with no quote.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        frame = self.ohlc.dropna(subset=["change_percent"])
        frame = frame.sort_values("change_percent", ascending=True)
        return frame.head(count).reset_index(drop=True)

    def overlap_with(self, other: "AssetBasket") -> float:
        """Measures how much of this basket's weight another basket also holds.

        The overlap is the sum, over the instruments both hold, of the smaller of the two weights. It is 1 for two identical baskets and 0 for two with nothing in common, and it is the usual way to tell whether two funds are really different.

        Args:
            other: The AssetBasket to compare with.

        Returns:
            The float overlap between 0 and 1.

        Raises:
            UnifiedBrokerInterfaceError: A basket whose weights come from live prices, such as a Portfolio, could not read them.
        """
        own_weights = self._weights_by_instrument_id()
        other_weights = other._weights_by_instrument_id()
        overlap = 0.0
        for instrument_id, weight in own_weights.items():
            if instrument_id in other_weights:
                overlap += min(weight, other_weights[instrument_id])
        return overlap

    def add_member(self, member: basket_member.BasketMember) -> None:
        """Adds a member to the basket in memory, which `BasketStore.save` then stores.

        Args:
            member: The basket_member.BasketMember to add, weighted if and only if the other members are.

        Returns:
            None.

        Raises:
            BasketMemberError: The instrument is already in the basket, or the member's weight does not match the others'.
        """
        candidate_members = self.members + [
            member,
        ]
        self._check_members(candidate_members)
        self.members = candidate_members

    def remove_member(self, instrument: asset_instruments.Instrument) -> None:
        """Removes an instrument from the basket in memory, which `BasketStore.save` then stores.

        Args:
            instrument: The tradingmachine.assets.instruments.Instrument to remove.

        Returns:
            None.

        Raises:
            BasketMemberError: The instrument is not in the basket, or it is the only member.
        """
        remaining = []
        for member in self.members:
            if member.instrument.instrument_id != instrument.instrument_id:
                remaining.append(member)
        if len(remaining) == len(self.members):
            raise exceptions.BasketMemberError(
                f"The instrument is not in the basket: {instrument!r}"
            )
        self._check_members(remaining)
        self.members = remaining

    def document(self, effective_date: datetime.date | str | None = None) -> dict:
        """Describes the basket as a dict for storing in MongoDB.

        Subclasses add their own settings to the dict.

        Args:
            effective_date: The first day the basket is in effect as a datetime.date or a `YYYY-MM-DD` str, or None for today.

        Returns:
            A dict with `name`, `kind`, `effective_date`, `linked_instrument_id`, `unmapped_weight`, `base_value` and a `members` list.

        Raises:
            Nothing.
        """
        if effective_date is None:
            effective_date = datetime.date.today()
        linked_instrument_id = None
        if self.linked_instrument is not None:
            linked_instrument_id = self.linked_instrument.instrument_id
        member_documents = []
        for member in self.members:
            member_documents.append(member.document())
        return {
            "name": self.name,
            "kind": self.KIND,
            "effective_date": self._date_text(effective_date),
            "linked_instrument_id": linked_instrument_id,
            "unmapped_weight": self.unmapped_weight,
            "base_value": self.base_value,
            "members": member_documents,
        }

    def prices(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Builds candles for the basket as a whole from its members' candles.

        Each candle is the sum over members of a fixed quantity times the member's candle. A weighted basket takes its quantities from its weights at the first candle of the range, so the first close equals `base_value`; a Portfolio uses the quantities it holds. The open and close are exact; the high and low are an approximation, because the members do not all reach their highs and lows at the same moment. `volume` and `oi` are empty.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame sorted by time with `exchange` set to None, `segment` set to the basket's KIND, `interval`, `datetime`, `open`, `high`, `low`, `close`, `volume` and `oi` columns, or None when any member has no candles in the range or no candle is shared by all.

        Raises:
            BasketMemberError: UBI answered an error for one or more members.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        aligned = self._aligned_candles(interval, from_date, to_date, days, adjusted)
        if aligned is None:
            return None
        closes = aligned["close"]
        quantities = self._candle_quantities(closes.iloc[0])
        frame = pd.DataFrame(index=closes.index)
        for column in CANDLE_COLUMNS:
            frame[column] = (
                aligned[column].mul(quantities, axis="columns").sum(axis="columns")
            )
        frame["volume"] = float("nan")
        frame["oi"] = float("nan")
        frame = frame.reset_index()
        frame.insert(0, "interval", interval)
        frame.insert(0, "segment", self.KIND)
        frame.insert(0, "exchange", None)
        return frame

    def _candle_quantities(self, first_closes: pd.Series) -> pd.Series:
        """Works out the fixed quantity of each member that the basket's candles are built from.

        This base version spreads `base_value` across the members by weight at the first candle's closes. A Portfolio replaces it with the quantities it holds.

        Args:
            first_closes: A pandas.Series of each member's float close at the first shared candle, indexed by member label.

        Returns:
            A pandas.Series of float quantities indexed by member label.

        Raises:
            Nothing.
        """
        weights = self.weights.reindex(first_closes.index)
        return self.base_value * weights / first_closes

    def _aligned_candles(
        self,
        interval: str,
        from_date: datetime.date | str | None,
        to_date: datetime.date | str | None,
        days: int | None,
        adjusted: bool,
    ) -> dict | None:
        """Lines up the members' open, high, low and close by time, keeping only candles every member has.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A dict mapping each of `open`, `high`, `low` and `close` to a pandas.DataFrame indexed by `datetime` with one float column per member label in member order, or None when any member has no candles or no candle is shared by all.

        Raises:
            BasketMemberError: UBI answered an error for one or more members.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        frame = self.member_prices(interval, from_date, to_date, days, adjusted)
        if frame is None:
            return None
        if frame["label"].nunique() < self.size:
            return None
        aligned = {}
        for column in CANDLE_COLUMNS:
            wide = frame.pivot(index="datetime", columns="label", values=column)
            aligned[column] = wide.reindex(columns=self.labels).astype(float)
        shared_times = aligned["close"].dropna().index
        if shared_times.empty:
            return None
        for column in CANDLE_COLUMNS:
            aligned[column] = aligned[column].loc[shared_times]
        return aligned

    def _post_for_every_member(
        self,
        path: str,
        shared_parameters: dict | None = None,
    ) -> list[dict]:
        """Sends one list request naming every member and returns its entries in member order.

        Args:
            path: The str path of a UBI route that takes a list of instruments, such as `/api/instruments/ltp`.
            shared_parameters: A dict of parameters that apply to every member, such as the interval and range for `/api/instruments/prices`, or None.

        Returns:
            A list of dicts, one per member, each with `request_index`, `status` and either `data` or `error`.

        Raises:
            UnifiedBrokerInterfaceError: The whole request was refused by, or failed on the way to, UBI.
        """
        return self._post_for_instruments(path, self.instruments, shared_parameters)

    def _post_for_instruments(
        self,
        path: str,
        listed_instruments: list[asset_instruments.Instrument],
        shared_parameters: dict | None = None,
    ) -> list[dict]:
        """Sends one list request naming the given instruments and returns its entries in the same order.

        Args:
            path: The str path of a UBI route that takes a list of instruments.
            listed_instruments: The list of tradingmachine.assets.instruments.Instrument to name, in order.
            shared_parameters: A dict of parameters that apply to every instrument, or None.

        Returns:
            A list of dicts, one per instrument, each with `request_index`, `status` and either `data` or `error`.

        Raises:
            UnifiedBrokerInterfaceError: The whole request was refused by, or failed on the way to, UBI.
        """
        named_instruments = []
        for instrument in listed_instruments:
            named_instruments.append(
                {
                    "instrument_id": instrument.instrument_id,
                }
            )
        body = {
            "instruments": named_instruments,
        }
        if shared_parameters is not None:
            body.update(shared_parameters)
        response = self._unified_broker_interface.post(path, body=body)
        results = sorted(
            response["results"], key=lambda result: result["request_index"]
        )
        return results

    def _last_prices_by_instrument_id(
        self,
        listed_instruments: list[asset_instruments.Instrument],
    ) -> dict:
        """Reads the last price of each of the given instruments in one request.

        Args:
            listed_instruments: The list of tradingmachine.assets.instruments.Instrument to price.

        Returns:
            A dict mapping each str instrument_id to its float last price.

        Raises:
            BasketMemberError: UBI had no price for one or more of the instruments, all of which the message lists.
            UnifiedBrokerInterfaceError: The whole request was refused by, or failed on the way to, UBI.
        """
        results = self._post_for_instruments(LAST_PRICE_PATH, listed_instruments)
        failures = []
        prices = {}
        for instrument, result in zip(listed_instruments, results):
            data = result.get("data") or {}
            last_price = data.get("last_price")
            if result["status"] != SUCCESS_STATUS or last_price is None:
                failures.append(f"{instrument!r}: {self._error_of(result)}")
                continue
            prices[instrument.instrument_id] = float(last_price)
        if failures:
            raise exceptions.BasketMemberError(
                f"UBI has no last price for {len(failures)} instruments: {'; '.join(failures)}"
            )
        return prices

    def _raise_for_failed_members(self, results: list[dict]) -> None:
        """Raises when any entry of a list answer is an error.

        Args:
            results: The list of entry dicts from a list answer, in member order.

        Returns:
            None.

        Raises:
            BasketMemberError: One or more entries are errors, all of which the message lists.
        """
        failures = []
        for member, result in zip(self.members, results):
            if result["status"] != SUCCESS_STATUS:
                failures.append(f"{member.label}: {result.get('error')}")
        if failures:
            raise exceptions.BasketMemberError(
                f"UBI answered an error for {len(failures)} of {self.size} members: {'; '.join(failures)}"
            )

    def _weights_grouped_by(self, attribute: str) -> pd.Series:
        """Adds up the weights of the members sharing each value of an instrument attribute.

        Args:
            attribute: The str name of the instrument attribute to group by, `segment` or `exchange`.

        Returns:
            A pandas.Series of float total weights indexed by attribute value, largest first.

        Raises:
            Nothing.
        """
        weights = self.weights
        totals = {}
        for member in self.members:
            if attribute == "segment":
                key = member.instrument.segment
            else:
                key = member.instrument.exchange
            totals[key] = totals.get(key, 0.0) + float(weights[member.label])
        return pd.Series(totals, dtype=float).sort_values(ascending=False)

    def _weights_by_instrument_id(self) -> dict:
        """Maps each member's instrument id to its weight.

        Returns:
            A dict mapping each str instrument_id to its float weight.

        Raises:
            UnifiedBrokerInterfaceError: A basket whose weights come from live prices could not read them.
        """
        weights = self.weights
        by_instrument_id = {}
        for member in self.members:
            by_instrument_id[member.instrument.instrument_id] = float(
                weights[member.label]
            )
        return by_instrument_id

    @staticmethod
    def _error_of(result: dict) -> str | None:
        """Reads the error message of one entry of a list answer.

        Args:
            result: One entry dict of a list answer.

        Returns:
            The str error message, or None when the entry succeeded.

        Raises:
            Nothing.
        """
        if result["status"] == SUCCESS_STATUS:
            return None
        return result.get("error") or f"HTTP {result['status']}"

    @staticmethod
    def _date_text(value: datetime.date | str) -> str:
        """Turns a date or a date string into the `YYYY-MM-DD` form UBI and MongoDB use.

        Args:
            value: A datetime.date or a `YYYY-MM-DD` str.

        Returns:
            The str date in `YYYY-MM-DD` form.

        Raises:
            Nothing.
        """
        if isinstance(value, datetime.date):
            return value.isoformat()
        return value
