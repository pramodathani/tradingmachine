"""
IND Money instrument master ingestion.

IND Money is the only broker here whose master is not public. It serves three CSV files behind an Authorization header carrying an access token, which is generated separately and lasts twenty-four hours. The token is read from configuration rather than generated here, so this module needs no login flow.
"""

from io import StringIO

import pandas
import requests

from data.instruments.base import BrokerInstruments
from utilities.configuration import indmoney_configuration

INSTRUMENTS_URL = "https://api.indstocks.com/market/instruments"

SOURCES = [
    "equity",
    "fno",
    "index",
]

DOWNLOAD_TIMEOUT_SECONDS = 120


class IndMoneyInstruments(BrokerInstruments):
    """
    Downloads IND Money's daily instrument master.

    Attributes:
        BROKER_NAME (str): Always "indmoney".
        DEDUPE_KEY_COLUMNS (list[str]): Exchange, segment and security identifier together.
        DEDUPE_SORT_COLUMN (str | None): Series, so the kept row is predictable.
    """

    BROKER_NAME = "indmoney"
    DEDUPE_KEY_COLUMNS = [
        "exch",
        "segment",
        "security_id",
    ]
    DEDUPE_SORT_COLUMN = "series"

    def __init__(self, access_token=None):
        """
        Build the IND Money ingester.

        Args:
            access_token (str | None): Token to authenticate with. When omitted, the token configured in the environment is used.
        """
        super().__init__()
        self.access_token = access_token or indmoney_configuration["access_token"]

    def download(self):
        """
        Fetch IND Money's three instrument master CSV files.

        Returns:
            pandas.DataFrame: Every row IND Money published, read as text.

        Raises:
            ValueError: If no access token is available, since the endpoint rejects an unauthenticated request.
            requests.HTTPError: If any of the three requests fails.
        """
        if not self.access_token:
            raise ValueError(
                "No IND Money access token available. Set BLACK_BOX_INDMONEY_ACCESS_TOKEN in .env, "
                "or pass --indmoney-access-token on the command line. "
                "A token is generated from https://api.indstocks.com/generate/token and lasts twenty-four hours."
            )

        frames = []
        for source in SOURCES:
            response = requests.get(
                INSTRUMENTS_URL,
                params={"source": source},
                headers={"Authorization": self.access_token},
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            frames.append(pandas.read_csv(StringIO(response.json()["data"]), dtype=str))
        return pandas.concat(frames, ignore_index=True)
