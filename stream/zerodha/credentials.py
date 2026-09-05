"""
Reads the two pieces of credential a Zerodha websocket connection needs.

The websocket URL takes an API key and an access token. They live in two different MongoDB collections and have two different lifetimes: the API key is a permanent property of the Kite Connect application and sits in the settings collection alongside the login credentials, while the access token is issued fresh every day by the login job that cron runs at seven in the morning and is written to the last_login collection.

Reading the token is written out here rather than shared with data/instruments/indmoney.py, which does the same thing for a different broker. The two are similar enough to invite a common helper and different enough that one would grow arguments for every broker's quirks, so each broker keeps its own copy.
"""

from datetime import datetime

import pymongo

from utilities.configuration import mongodb_configuration

BROKER_NAME = "zerodha"


class ZerodhaCredentialsError(Exception):
    """
    Raised when the credentials a websocket connection needs are missing or out of date.
    """


def open_mongodb_database():
    """
    Open the MongoDB database holding broker settings and login results.

    Returns:
        tuple: A (client, database) pair. The caller closes the client when finished, which is why it is returned rather than hidden.

    Raises:
        pymongo.errors.PyMongoError: If MongoDB cannot be reached.
    """
    client = pymongo.MongoClient(mongodb_configuration["connection_string"])
    return (client, client[mongodb_configuration["database"]])


def stored_access_token():
    """
    Read today's Zerodha access token from the last_login collection.

    A token issued on an earlier day is not returned. Zerodha's tokens expire daily, and sending an expired one produces a rejected websocket handshake whose status code says nothing about the cause, so it is better to report that there is no usable token than to try one that cannot work.

    Returns:
        str | None: The token issued today, or None when there is no document, no token in it, or the token was issued on an earlier date.

    Raises:
        pymongo.errors.PyMongoError: If MongoDB cannot be reached.
    """
    client, database = open_mongodb_database()
    try:
        document = database["last_login"].find_one({"broker_name": BROKER_NAME})
    finally:
        client.close()

    if document is None:
        return None
    last_login = document.get("last_login")
    if not last_login:
        return None
    if last_login[:10] != datetime.now().strftime("%Y-%m-%d"):
        return None
    return document.get("access_token")


def stored_api_key():
    """
    Read the Zerodha API key from the settings collection.

    Returns:
        str | None: The API key, or None when Zerodha has no settings document or the document carries no key.

    Raises:
        pymongo.errors.PyMongoError: If MongoDB cannot be reached.
    """
    client, database = open_mongodb_database()
    try:
        settings = database["settings"].find_one({"broker_name": BROKER_NAME}, {"_id": 0})
    finally:
        client.close()

    if settings is None:
        return None
    return settings.get("api_key")


def websocket_credentials():
    """
    Read both credentials a websocket connection needs, failing clearly when either is unusable.

    Returns:
        tuple: An (api_key, access_token) pair, both strings.

    Raises:
        ZerodhaCredentialsError: If the API key is missing, or the access token is missing or was not issued today.
        pymongo.errors.PyMongoError: If MongoDB cannot be reached.
    """
    api_key = stored_api_key()
    if not api_key:
        raise ZerodhaCredentialsError("Zerodha has no api_key in the MongoDB settings collection.")

    access_token = stored_access_token()
    if not access_token:
        raise ZerodhaCredentialsError(
            "Zerodha has no access token issued today in the MongoDB last_login collection. The broker login job runs at 07:00 on weekdays; run 'python3 -m utilities.broker_login --brokers zerodha' to obtain one now."
        )

    return (api_key, access_token)
