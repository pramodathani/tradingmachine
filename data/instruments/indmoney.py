"""
IND Money instrument master ingestion.

IND Money is the only broker here whose master is not public. It serves three CSV files behind an Authorization header carrying an access token, which lasts twenty-four hours.

The token is read from the MongoDB ``last_login`` collection, where the daily broker login job records it, so this module needs no login flow of its own and no second copy of the token in the environment. A token issued on an earlier day is rejected rather than sent, because IND Money would only answer it with an authentication error that says nothing about the cause.
"""

from datetime import datetime
from io import StringIO

import pandas
import pymongo
import requests

from data.instruments.base import BrokerInstruments
from utilities.configuration import mongodb_configuration

INSTRUMENTS_URL = "https://api.indstocks.com/market/instruments"

SOURCES = [
    "equity",
    "fno",
    "index",
]

DOWNLOAD_TIMEOUT_SECONDS = 120


def stored_access_token():
    """
    Read today's IND Money access token from the MongoDB last_login collection.

    The daily broker login job writes one document per broker there, holding the token it received and the moment it received it. A token from an earlier day is not returned: IND Money's tokens last twenty-four hours, and sending a stale one produces an authentication error that says nothing about why.

    Returns:
        str | None: The token issued today, or None when there is no document, no token in it, or the token was issued on an earlier date.
    """
    client = pymongo.MongoClient(mongodb_configuration["connection_string"])
    try:
        database = client[mongodb_configuration["database"]]
        document = database["last_login"].find_one({"broker_name": "indmoney"})
    finally:
        client.close()

    if document is None:
        return None
    last_login = document.get("last_login")
    if not last_login or last_login[:10] != datetime.now().strftime("%Y-%m-%d"):
        return None
    return document.get("access_token")


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
            access_token (str | None): Token to authenticate with. When omitted, today's token is read from the MongoDB last_login collection.
        """
        super().__init__()
        self.access_token = access_token or stored_access_token()

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
                "No IND Money access token available. Run the daily broker login "
                "(python3 -m utilities.broker_login) to store today's token in the last_login "
                "collection, or pass --indmoney-access-token on the command line. "
                "IND Money's token lasts twenty-four hours."
            )

        frames = []
        for source in SOURCES:
            response = requests.get(
                INSTRUMENTS_URL,
                params={"source": source},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": self.access_token,
                },
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            frames.append(pandas.read_csv(StringIO(response.text), dtype=str))
        return pandas.concat(frames, ignore_index=True)
