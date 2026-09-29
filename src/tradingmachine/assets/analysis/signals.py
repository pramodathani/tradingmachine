"""Signals: where one column of a frame crosses another.

The methods work on a frame the caller already has, such as the result of `simple_moving_average`, so they do not fetch candles. The class is inherited by `tradingmachine.assets.instruments.Instrument`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.simple_moving_average(window=20, days=365)
  crossings = infosys.is_cross_over(frame, "close", "sma_20")
"""

import numpy as np
import pandas as pd

from tradingmachine.assets.analysis import price_analysis


class Signals(price_analysis.PriceAnalysis):
    """Crossover and crossunder detection between two columns of a frame."""

    def is_cross_over(
        self,
        data: pd.DataFrame,
        first_column: str,
        second_column: str,
    ) -> pd.DataFrame:
        """Marks the rows where the first column rises above the second.

        A row is marked when, on the previous row, the first column was at or below the second, and on this row it is above the second. The first row is never marked.

        Args:
            data: The pandas.DataFrame holding both columns, which is not changed.
            first_column: The str name of the column that crosses.
            second_column: The str name of the column that is crossed.

        Returns:
            A pandas.DataFrame copy of data with a fresh index and an added bool `cross_over` column.

        Raises:
            KeyError: data has no column named first_column or second_column.

        Examples:
            Print the days in the last three years when the 50-day average of Infosys crossed above its 200-day average, the golden cross:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            fast_frame = infosys.simple_moving_average(window=50, days=1095)
            slow_frame = infosys.simple_moving_average(window=200, days=1095)
            fast_frame["sma_200"] = slow_frame["sma_200"]
            crossings = infosys.is_cross_over(fast_frame, "sma_50", "sma_200")
            golden_crosses = crossings[crossings["cross_over"]]
            if golden_crosses.empty:
                print("No golden cross in the last three years.")
            for crossing_date in golden_crosses["datetime"]:
                print(crossing_date.date())
            ```

            Count how often the Nifty close rose above its 20-day average in the last year:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            average_frame = nifty.simple_moving_average(window=20, days=365)
            crossings = nifty.is_cross_over(average_frame, "close", "sma_20")
            crossing_count = int(crossings["cross_over"].sum())
            print(f"Crossings above the 20-day average: {crossing_count}")
            ```

            Find the latest day the MACD line of Reliance Industries rose above its signal line:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            macd_frame = reliance.moving_average_convergence_divergence(
                days=365,
            )
            crossings = reliance.is_cross_over(
                macd_frame,
                "macd_12_26_9",
                "macd_12_26_9_signal",
            )
            bullish_crossings = crossings[crossings["cross_over"]]
            if bullish_crossings.empty:
                print("The MACD line did not cross above its signal line.")
            else:
                latest_date = bullish_crossings["datetime"].iloc[-1].date()
                print(f"Latest bullish MACD crossing: {latest_date}")
            ```
        """
        data = data.reset_index(drop=True)
        previous_first = data[first_column].shift()
        previous_second = data[second_column].shift()
        was_at_or_below = previous_first <= previous_second
        is_above = data[first_column] > data[second_column]
        data["cross_over"] = np.where(was_at_or_below & is_above, True, False)
        return data

    def is_cross_under(
        self,
        data: pd.DataFrame,
        first_column: str,
        second_column: str,
    ) -> pd.DataFrame:
        """Marks the rows where the first column falls below the second.

        A row is marked when, on the previous row, the first column was at or above the second, and on this row it is below the second. The first row is never marked.

        Args:
            data: The pandas.DataFrame holding both columns, which is not changed.
            first_column: The str name of the column that crosses.
            second_column: The str name of the column that is crossed.

        Returns:
            A pandas.DataFrame copy of data with a fresh index and an added bool `cross_under` column.

        Raises:
            KeyError: data has no column named first_column or second_column.

        Examples:
            Print the days in the last six months when Infosys closed below its 20-day exponential average:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            average_frame = infosys.exponential_moving_average(
                window=20,
                days=180,
            )
            crossings = infosys.is_cross_under(average_frame, "close", "ema_20")
            falls = crossings[crossings["cross_under"]]
            if falls.empty:
                print("Infosys did not close below its 20-day average.")
            for crossing_date in falls["datetime"]:
                print(crossing_date.date())
            ```

            Find the days Tata Consultancy Services left overbought ground, with its 14-day RSI falling below 70:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            strength_frame = tcs.relative_strength_index(window=14, days=730)
            strength_frame["overbought_level"] = 70
            crossings = tcs.is_cross_under(
                strength_frame,
                "rsi_14",
                "overbought_level",
            )
            exits = crossings[crossings["cross_under"]]
            print(f"RSI fell below 70 on {len(exits)} days in two years.")
            print(exits[["datetime", "close", "rsi_14"]].tail())
            ```

            Count the death crosses of the Nifty over five years, where the 50-day average falls below the 200-day one:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            fast_frame = nifty.simple_moving_average(window=50, days=1825)
            slow_frame = nifty.simple_moving_average(window=200, days=1825)
            fast_frame["sma_200"] = slow_frame["sma_200"]
            crossings = nifty.is_cross_under(fast_frame, "sma_50", "sma_200")
            death_cross_count = int(crossings["cross_under"].sum())
            print(f"Death crosses in five years: {death_cross_count}")
            ```
        """
        data = data.reset_index(drop=True)
        previous_first = data[first_column].shift()
        previous_second = data[second_column].shift()
        was_at_or_above = previous_first >= previous_second
        is_below = data[first_column] < data[second_column]
        data["cross_under"] = np.where(was_at_or_above & is_below, True, False)
        return data
