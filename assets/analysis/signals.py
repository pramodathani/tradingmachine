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

        Args:
            data: The pandas.DataFrame holding both columns, which is not changed.
            first_column: The str name of the column that crosses.
            second_column: The str name of the column that is crossed.

        Returns:
            A pandas.DataFrame copy of data with a fresh index and an added bool `cross_over` column.

        Raises:
            KeyError: data has no column named first_column or second_column.
        """
        data = data.copy()
        columns = data.columns.tolist()
        data.reset_index(inplace=True, drop=True)
        data["shifted_column1"] = data[first_column].shift()
        crossed = (data["shifted_column1"] <= data[second_column]) & (
            data[second_column] < data[first_column]
        )
        data["cross_over"] = np.where(crossed, True, False)
        columns.append("cross_over")
        return data[columns]

    def is_cross_under(
        self,
        data: pd.DataFrame,
        first_column: str,
        second_column: str,
    ) -> pd.DataFrame:
        """Marks the rows where the first column falls below the second.

        Args:
            data: The pandas.DataFrame holding both columns, which is not changed.
            first_column: The str name of the column that crosses.
            second_column: The str name of the column that is crossed.

        Returns:
            A pandas.DataFrame copy of data with a fresh index and an added bool `cross_under` column.

        Raises:
            KeyError: data has no column named first_column or second_column.
        """
        data = data.copy()
        columns = data.columns.tolist()
        data.reset_index(inplace=True, drop=True)
        data["shifted_column1"] = data[first_column].shift()
        crossed = (data["shifted_column1"] >= data[second_column]) & (
            data[second_column] > data[first_column]
        )
        data["cross_under"] = np.where(crossed, True, False)
        columns.append("cross_under")
        return data[columns]
