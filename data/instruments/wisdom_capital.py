"""
Wisdom Capital instrument master ingestion.

Wisdom Capital serves its master through a public POST endpoint, one call per exchange segment. The response is JSON whose 'result' field holds pipe-delimited text with no header line, and the number of fields depends on whether the row is an equity, an option or a future, so the three shapes carry their own column names.
"""

import pandas
import requests

from data.instruments.base import BrokerInstruments

INSTRUMENTS_URL = "https://developers.symphonyfintech.in/apibinarymarketdata/instruments/master"

EXCHANGE_SEGMENTS = [
    "NSECM",
    "NSEFO",
    "NSECD",
    "NSECO",
    "BSECM",
    "BSEFO",
    "BSECD",
    "MCXFO",
    "NCDEX",
]

EQUITY_COLUMN_NAMES = [
    "ExchangeSegment",
    "ExchangeInstrumentID",
    "InstrumentType",
    "Name",
    "Description",
    "Series",
    "NameWithSeries",
    "InstrumentID",
    "PriceBand.High",
    "PriceBand.Low",
    "FreezeQty",
    "TickSize",
    "LotSize",
    "Multiplier",
    "DisplayName",
    "ISIN",
    "PriceNumerator",
    "PriceDenominator",
    "DetailedDescription",
    "ExtendedSurvIndicator",
    "CautionIndicator",
    "GSMIndicator",
]

OPTION_COLUMN_NAMES = [
    "ExchangeSegment",
    "ExchangeInstrumentID",
    "InstrumentType",
    "Name",
    "Description",
    "Series",
    "NameWithSeries",
    "InstrumentID",
    "PriceBand.High",
    "PriceBand.Low",
    "FreezeQty",
    "TickSize",
    "LotSize",
    "Multiplier",
    "UnderlyingInstrumentId",
    "UnderlyingIndexName",
    "ContractExpiration",
    "StrikePrice",
    "OptionType",
    "DisplayName",
    "PriceNumerator",
    "PriceDenominator",
    "DetailedDescription",
]

FUTURE_COLUMN_NAMES = [
    "ExchangeSegment",
    "ExchangeInstrumentID",
    "InstrumentType",
    "Name",
    "Description",
    "Series",
    "NameWithSeries",
    "InstrumentID",
    "PriceBand.High",
    "PriceBand.Low",
    "FreezeQty",
    "TickSize",
    "LotSize",
    "Multiplier",
    "UnderlyingInstrumentId",
    "UnderlyingIndexName",
    "ContractExpiration",
    "DisplayName",
    "PriceNumerator",
    "PriceDenominator",
    "DetailedDescription",
]

DOWNLOAD_TIMEOUT_SECONDS = 120


class WisdomCapitalInstruments(BrokerInstruments):
    """
    Downloads Wisdom Capital's daily instrument master.

    Attributes:
        BROKER_NAME (str): Always "wisdom_capital".
        DEDUPE_KEY_COLUMNS (list[str]): Exchange segment and exchange instrument identifier together.
        DEDUPE_SORT_COLUMN (str | None): Series, so the kept row is predictable.
    """

    BROKER_NAME = "wisdom_capital"
    DEDUPE_KEY_COLUMNS = [
        "exchangesegment",
        "exchangeinstrumentid",
    ]
    DEDUPE_SORT_COLUMN = "series"

    def pad_or_join_fields(self, fields, expected_count):
        """
        Force one split line to the number of fields its shape expects.

        A description containing a pipe character splits into too many fields, so the surplus is joined back into the last one. A short line is padded with empty strings.

        Args:
            fields (list[str]): The pipe-split values of one line.
            expected_count (int): How many values that row shape declares.

        Returns:
            list[str]: Exactly expected_count values.
        """
        if len(fields) > expected_count:
            return fields[: expected_count - 1] + ["|".join(fields[expected_count - 1:])]
        return fields + [""] * (expected_count - len(fields))

    def download(self):
        """
        Fetch Wisdom Capital's master for every exchange segment and stack the three row shapes.

        Returns:
            pandas.DataFrame: Every row Wisdom Capital published, read as text, with a data_category column recording which shape each row was parsed as.

        Raises:
            requests.HTTPError: If any segment request fails.
            ValueError: If no segment returned any instrument data.
        """
        frames = []
        for exchange_segment in EXCHANGE_SEGMENTS:
            response = requests.post(
                INSTRUMENTS_URL,
                headers={"Content-Type": "application/json"},
                json={"exchangeSegmentList": [exchange_segment]},
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            result_text = response.json().get("result", "")
            if not result_text:
                continue

            rows_by_category = {
                "equities": [],
                "options": [],
                "futures": [],
            }
            for line in result_text.splitlines():
                line = line.strip()
                if not line or line.lower().startswith("exchangesegment|"):
                    continue
                fields = [field.strip() for field in line.split("|")]
                if len(fields) < 3:
                    continue
                instrument_type = fields[2]
                series = fields[5] if len(fields) > 5 else ""
                if instrument_type == "8":
                    rows_by_category["equities"].append(self.pad_or_join_fields(fields, len(EQUITY_COLUMN_NAMES)))
                elif instrument_type == "2" or str(series).upper().startswith("OPT"):
                    rows_by_category["options"].append(self.pad_or_join_fields(fields, len(OPTION_COLUMN_NAMES)))
                else:
                    rows_by_category["futures"].append(self.pad_or_join_fields(fields, len(FUTURE_COLUMN_NAMES)))

            for category, column_names in [
                ("equities", EQUITY_COLUMN_NAMES),
                ("options", OPTION_COLUMN_NAMES),
                ("futures", FUTURE_COLUMN_NAMES),
            ]:
                if not rows_by_category[category]:
                    continue
                frame = pandas.DataFrame(rows_by_category[category], columns=column_names, dtype=str)
                frame["data_category"] = category
                frames.append(frame)

        if not frames:
            raise ValueError("Wisdom Capital returned no instrument data for any exchange segment.")
        return pandas.concat(frames, ignore_index=True)
