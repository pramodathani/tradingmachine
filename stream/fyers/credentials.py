"""
Reads the credentials a Fyers websocket connection needs.

Fyers has two market data sockets and they authenticate differently, so this module produces three values rather than the usual two. The quote socket takes no headers at all and authenticates in-band, and the token it wants is not the access token but the `hsm_key` claim carried inside it. The tick-by-tick depth socket takes an ordinary Authorization header whose value is the application identifier and the access token joined by a colon.

The application identifier is a permanent property of the Fyers account and lives in the settings collection. The access token is issued by the login job that cron runs at seven in the morning and is written to the last_login collection.

Fyers is the one broker whose token says exactly when it stops working. Its access token is a JSON Web Token whose payload carries an `exp` claim, so this module reads that instead of comparing the login date to today's date the way the other brokers' modules do. The date comparison is a conservative stand-in for an expiry that cannot be seen; here the expiry can be seen, so there is no reason to guess at it.

Reading the token is written out here rather than shared with the other brokers' modules, which do the same thing for different brokers. The copies are similar enough to invite a common helper and different enough that one would grow arguments for every broker's quirks, so each broker keeps its own.
"""

import base64
import json
import time

import pymongo

from utilities.configuration import mongodb_configuration

BROKER_NAME = "fyers"

HSM_KEY_CLAIM = "hsm_key"
EXPIRY_CLAIM = "exp"


class FyersCredentialsError(Exception):
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


def decode_token_claims(access_token):
    """
    Read the claims out of a Fyers access token without verifying its signature.

    The signature is the broker's business, not ours. Nothing here decides whether to trust the token, only what the broker itself said about it, so verifying would need a key we do not have in order to answer a question we are not asking.

    Args:
        access_token (str): The access token as issued by Fyers, which is a JSON Web Token of three dot-separated parts.

    Returns:
        dict | None: The payload claims, or None when the token is not a readable JSON Web Token.
    """
    parts = access_token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1]
    try:
        decoded = base64.urlsafe_b64decode(payload + "===")
    except (ValueError, TypeError):
        return None
    try:
        claims = json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(claims, dict):
        return None
    return claims


def seconds_until_expiry(claims):
    """
    Say how long a token has left, from the expiry claim it carries.

    Args:
        claims (dict): The claims decoded out of an access token.

    Returns:
        float | None: Seconds until the token expires, negative when it already has, or None when the token carries no readable expiry.
    """
    expiry = claims.get(EXPIRY_CLAIM)
    if expiry is None:
        return None
    try:
        return float(expiry) - time.time()
    except (TypeError, ValueError):
        return None


def stored_access_token():
    """
    Read the Fyers access token from the last_login collection.

    Whether the token is still usable is not decided here, because the token itself carries the answer and websocket_credentials reads it. This returns whatever was stored, so a caller reporting an expired token can say when it expired rather than only that it was too old.

    Returns:
        str | None: The stored token, or None when there is no document or no token in it.

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
    return document.get("access_token")


def stored_application_identifier():
    """
    Read the Fyers application identifier the tick-by-tick socket's header needs.

    Args:
        None.

    Returns:
        str | None: The application identifier, for example "LUJI2M5GOT-100", or None when the settings document carries none.

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
    return settings.get("app_id")


def authorization_header_value(application_identifier, access_token):
    """
    Build the Authorization header the tick-by-tick depth socket expects.

    Args:
        application_identifier (str): The Fyers application identifier.
        access_token (str): An access token that has not expired.

    Returns:
        str: The header value, which is the two joined by a colon.
    """
    return f"{application_identifier}:{access_token}"


def websocket_credentials():
    """
    Read every credential the two market data sockets need, failing clearly when any is unusable.

    Returns:
        tuple: An (application_identifier, access_token, hsm_key) triple, all strings. The quote socket needs the hsm_key, the tick-by-tick socket needs the other two.

    Raises:
        FyersCredentialsError: If the application identifier is missing, or the access token is missing, unreadable, expired, or carries no hsm_key claim.
        pymongo.errors.PyMongoError: If MongoDB cannot be reached.
    """
    application_identifier = stored_application_identifier()
    if not application_identifier:
        raise FyersCredentialsError("Fyers has no app_id in the MongoDB settings collection.")

    access_token = stored_access_token()
    if not access_token:
        raise FyersCredentialsError(
            "Fyers has no access token in the MongoDB last_login collection. The broker login job runs at 07:00 on weekdays; run 'python3 -m utilities.broker_login --brokers fyers' to obtain one now."
        )

    claims = decode_token_claims(access_token)
    if claims is None:
        raise FyersCredentialsError("The stored Fyers access token is not a readable JSON Web Token, so its hsm_key cannot be read.")

    remaining = seconds_until_expiry(claims)
    if remaining is None:
        raise FyersCredentialsError("The stored Fyers access token carries no readable exp claim, so there is no way to tell whether it is still valid.")
    if remaining <= 0:
        raise FyersCredentialsError(
            f"The stored Fyers access token expired {-remaining / 3600:.1f} hours ago. The broker login job runs at 07:00 on weekdays; run 'python3 -m utilities.broker_login --brokers fyers' to obtain a fresh one."
        )

    hsm_key = claims.get(HSM_KEY_CLAIM)
    if not hsm_key:
        raise FyersCredentialsError("The stored Fyers access token carries no hsm_key claim, which is the token the quote socket authenticates with.")

    return (application_identifier, access_token, hsm_key)
