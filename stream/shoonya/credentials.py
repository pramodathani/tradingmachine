"""
Reads the two pieces of credential a Shoonya websocket connection needs.

The connect message takes a user identifier and an access token, sent as JSON once the socket is open. They live in two different MongoDB collections and have two different lifetimes: the user identifier is a permanent property of the Shoonya account, while the access token is issued by the login job that cron runs at seven in the morning and is written to the last_login collection.

Reading the token is written out here rather than shared with the other brokers' modules, which do the same thing for different brokers. The copies are similar enough to invite a common helper and different enough that one would grow arguments for every broker's quirks, so each broker keeps its own.
"""

from datetime import datetime

import pymongo

from utilities.configuration import mongodb_configuration

BROKER_NAME = "shoonya"


class ShoonyaCredentialsError(Exception):
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
    Read today's Shoonya access token from the last_login collection.

    A token issued on an earlier day is not returned. Noren session tokens expire some hours after they are issued rather than at midnight, so a token issued yesterday evening may still technically work this morning. Reporting no token in that window is the conservative reading, because it cannot mistake a token expiry for any other kind of refusal.

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


def stored_uid():
    """
    Read the Shoonya user identifier the connect message needs.

    The connect message sends the same value as both `uid` and `actid`, and that value is the account's unique client code. The login already signs in with it and sends it to the token exchange as `uid`, so the settings document is the authoritative source and there is no last_login fallback to consult.

    Returns:
        str | None: The user identifier, or None when the settings document carries no client code.

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
    return settings.get("ucc_code")


def websocket_credentials():
    """
    Read both credentials a websocket connection needs, failing clearly when either is unusable.

    Returns:
        tuple: A (uid, access_token) pair, both strings.

    Raises:
        ShoonyaCredentialsError: If the user identifier is missing, or the access token is missing or was not issued today.
        pymongo.errors.PyMongoError: If MongoDB cannot be reached.
    """
    uid = stored_uid()
    if not uid:
        raise ShoonyaCredentialsError("Shoonya has no ucc_code in the MongoDB settings collection, and the websocket connect message sends it as both uid and actid.")

    access_token = stored_access_token()
    if not access_token:
        raise ShoonyaCredentialsError(
            "Shoonya has no access token issued today in the MongoDB last_login collection. The broker login job runs at 07:00 on weekdays; run 'python3 -m utilities.broker_login --brokers shoonya' to obtain one now."
        )

    return (uid, access_token)
