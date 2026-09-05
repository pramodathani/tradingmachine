"""
Reads the two pieces of credential a Dhan websocket connection needs.

The websocket URL takes a client identifier and an access token, both passed as query parameters. They live in two different MongoDB collections and have two different lifetimes: the client identifier is a permanent property of the Dhan account and sits in the settings collection alongside the login credentials, while the access token is issued by the login job that cron runs at seven in the morning and is written to the last_login collection.

Reading the token is written out here rather than shared with the other brokers' modules, which do the same thing for different brokers. The copies are similar enough to invite a common helper and different enough that one would grow arguments for every broker's quirks, so each broker keeps its own.
"""

from datetime import datetime

import pymongo

from utilities.configuration import mongodb_configuration

BROKER_NAME = "dhan"


class DhanCredentialsError(Exception):
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
    Read today's Dhan access token from the last_login collection.

    A token issued on an earlier day is not returned. Dhan's tokens last roughly twenty four hours from the moment they are issued rather than expiring at midnight, so a token issued yesterday morning may still technically work for a few minutes. Reporting no token in that window is the conservative reading, because it cannot mistake a token expiry for any other kind of refusal.

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


def stored_client_id():
    """
    Read the Dhan client identifier from the settings collection.

    The client identifier plays the role the API key plays for Zerodha: it is permanent, it is required by the websocket URL, and the login job sends it as dhanClientId when it obtains the access token. It lives among the login credentials rather than in a broker application, because a Dhan account has no separate market data application to belong to.

    Returns:
        str | None: The client identifier, or None when Dhan has no settings document or the document carries none.

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
    return settings.get("client_id")


def websocket_credentials():
    """
    Read both credentials a websocket connection needs, failing clearly when either is unusable.

    Returns:
        tuple: A (client_id, access_token) pair, both strings.

    Raises:
        DhanCredentialsError: If the client identifier is missing, or the access token is missing or was not issued today.
        pymongo.errors.PyMongoError: If MongoDB cannot be reached.
    """
    client_id = stored_client_id()
    if not client_id:
        raise DhanCredentialsError("Dhan has no client_id in the MongoDB settings collection.")

    access_token = stored_access_token()
    if not access_token:
        raise DhanCredentialsError(
            "Dhan has no access token issued today in the MongoDB last_login collection. The broker login job runs at 07:00 on weekdays; run 'python3 -m utilities.broker_login --brokers dhan' to obtain one now."
        )

    return (client_id, access_token)