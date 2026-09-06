"""
Reads the credentials a Groww websocket connection needs, and mints the one Groww does not store.

Groww is the only broker here whose feed credential is not simply read out of MongoDB. Its market data feed is a NATS message bus, and NATS authenticates a client with an NKEY: an Ed25519 key pair that the client generates for itself, whose public half Groww signs into a JSON Web Token, and whose private half then signs a nonce the server issues on every connection. So this module does three things rather than one. It reads the daily access token from the last_login collection, it generates a key pair and exchanges its public half for a token, and it signs nonces for the connection driver.

The key pair is generated here rather than stored anywhere. It is worth being clear about why: it is not a credential of the account, it is a credential of one streaming session. Groww's own SDK does the same, generating thirty two random bytes per feed instance. Nothing is gained by keeping it, and a stored private key would be a durable secret where there is currently none.

The NKEY encoding is written out here instead of taken from the nkeys package. It is a prefix byte, the key, and a two byte checksum, base32 encoded without padding, which is thirty lines including the checksum table-free loop. The one thing that genuinely cannot be written out is Ed25519 itself, which is why PyNaCl is a dependency.

Reading the token is written out here rather than shared with the other brokers' modules, which do the same thing for different brokers. The copies are similar enough to invite a common helper and different enough that one would grow arguments for every broker's quirks, so each broker keeps its own.
"""

import base64
import os
from datetime import datetime

import nacl.signing
import pymongo
import requests

from utilities.configuration import mongodb_configuration

BROKER_NAME = "groww"

SOCKET_TOKEN_URL = "https://api.groww.in/v1/api/apex/v1/socket/token/create/"

REQUEST_TIMEOUT_SECONDS = 30

NKEY_PREFIX_BYTE_USER = 20 << 3

SEED_BYTES = 32

CRC16_POLYNOMIAL = 0x1021


class GrowwCredentialsError(Exception):
    """
    Raised when the credentials a websocket connection needs are missing, out of date, or refused.
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
    Read the Groww access token from the last_login collection, if today's login produced one.

    Groww's access token carries no readable expiry, unlike Fyers', so the login date stands in for one. A token from an earlier day is treated as unusable rather than tried, because a socket token minted with a stale access token is refused at the handshake, which is a slower and less obvious failure than this one.

    Returns:
        str | None: Today's token, or None when there is no document, no token in it, or the login was not today.

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
    if not last_login or last_login[:10] != datetime.now().strftime("%Y-%m-%d"):
        return None

    return document.get("access_token")


def crc16(data):
    """
    Compute the CRC-16/XMODEM checksum an NKEY carries in its last two bytes.

    Args:
        data (bytes): The prefix byte followed by the key.

    Returns:
        int: The checksum, in the range 0 to 65535.
    """
    checksum = 0
    for byte in data:
        checksum = checksum ^ (byte << 8)
        for _ in range(8):
            if checksum & 0x8000:
                checksum = ((checksum << 1) ^ CRC16_POLYNOMIAL) & 0xFFFF
            else:
                checksum = (checksum << 1) & 0xFFFF
    return checksum


def encode_nkey(prefix_byte, key):
    """
    Encode a key in the NKEY text form NATS expects.

    The form is one prefix byte saying what kind of key this is, the key itself, and the checksum of both in little endian order, the whole base32 encoded and stripped of its padding. A user public key comes out starting with the letter U, which is what the prefix byte is chosen to produce.

    Args:
        prefix_byte (int): The kind byte, for example NKEY_PREFIX_BYTE_USER.
        key (bytes): The raw key, thirty two bytes.

    Returns:
        str: The encoded key.
    """
    body = bytes([prefix_byte]) + key
    checksum = crc16(body)
    encoded = base64.b32encode(body + checksum.to_bytes(2, "little"))
    return encoded.decode("ascii").rstrip("=")


def generate_key_pair():
    """
    Generate the Ed25519 key pair one streaming session authenticates with.

    The pair belongs to the session rather than to the account, so it is generated fresh and never stored. Groww's own SDK does the same.

    Returns:
        tuple: A (seed, public_key_text) pair, where seed is the thirty two raw private bytes and public_key_text is the NKEY encoded public half to send to Groww.
    """
    seed = os.urandom(SEED_BYTES)
    signing_key = nacl.signing.SigningKey(seed)
    public_key = bytes(signing_key.verify_key)
    return (seed, encode_nkey(NKEY_PREFIX_BYTE_USER, public_key))


def request_socket_token(access_token, public_key_text):
    """
    Ask Groww to mint a socket token for a public key.

    Args:
        access_token (str): Today's Groww access token.
        public_key_text (str): The NKEY encoded public key from generate_key_pair.

    Returns:
        tuple: A (socket_token, subscription_identifier) pair. The socket token is the JSON Web Token the NATS handshake presents. The subscription identifier addresses this account's own order and position subjects and is not used by the market data feed, but is returned rather than discarded because it is what the response carries.

    Raises:
        GrowwCredentialsError: If Groww refuses the request or returns no token.
        requests.RequestException: If the request cannot be made at all.
    """
    response = requests.post(
        SOCKET_TOKEN_URL,
        json={"socketKey": public_key_text},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise GrowwCredentialsError(f"Groww refused to mint a socket token, status {response.status_code}: {response.text}")

    body = response.json()
    payload = body.get("payload", body)
    socket_token = payload.get("token")
    if not socket_token:
        raise GrowwCredentialsError(f"Groww returned no socket token: {response.text}")

    return (socket_token, payload.get("subscriptionId"))


def sign_nonce(seed, nonce):
    """
    Sign the nonce a NATS server issued, in the form its CONNECT expects.

    NATS issues a fresh nonce on every connection, so this runs once per session rather than once per key pair. The signature goes into CONNECT as unpadded base64url text.

    Args:
        seed (bytes): The thirty two private bytes from generate_key_pair.
        nonce (bytes): The nonce exactly as it arrived in the server's INFO, as ASCII bytes rather than as text, because it is the bytes that are signed.

    Returns:
        str: The signature, base64url encoded without padding.
    """
    signing_key = nacl.signing.SigningKey(seed)
    signature = signing_key.sign(nonce).signature
    return base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")


def websocket_credentials():
    """
    Produce everything a Groww market data connection needs to authenticate.

    Returns:
        tuple: A (socket_token, seed) pair. The connection presents the socket token in CONNECT and signs each session's nonce with the seed.

    Raises:
        GrowwCredentialsError: If there is no usable access token, or Groww refuses to mint a socket token.
        pymongo.errors.PyMongoError: If MongoDB cannot be reached.
        requests.RequestException: If Groww cannot be reached.
    """
    access_token = stored_access_token()
    if not access_token:
        raise GrowwCredentialsError(
            "Groww has no access token from today in the MongoDB last_login collection. The broker login job runs at 07:00 on weekdays; run 'python3 -m utilities.broker_login --brokers groww' to obtain one now."
        )

    seed, public_key_text = generate_key_pair()
    socket_token, _ = request_socket_token(access_token, public_key_text)
    return (socket_token, seed)
