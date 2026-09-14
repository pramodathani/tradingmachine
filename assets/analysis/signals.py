"""Signals: where one column of a frame crosses another.

The methods work on a frame the caller already has, such as the result of `simple_moving_average`, so they do not fetch candles. The class is inherited by `assets.instruments.Instrument`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.simple_moving_average(window=20, days=365)
  crossings = infosys.is_cross_over(frame, "close", "sma_20")
"""

import numpy as np
import pandas as pd

from assets.analysis import price_analysis


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
        """
        data = data.reset_index(drop=True)
        previous_first = data[first_column].shift()
        previous_second = data[second_column].shift()
        was_at_or_above = previous_first >= previous_second
        is_below = data[first_column] < data[second_column]
        data["cross_under"] = np.where(was_at_or_above & is_below, True, False)
        return data
