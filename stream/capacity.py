"""
Remembers how much streaming capacity each broker actually gives us.

Brokers publish limits that bear little relation to what they enforce, so the real numbers have to be measured. Measuring them means opening connections until one is refused, which is exactly the behaviour that should not happen every morning, so the answer is stored and reused and only re-measured deliberately.

MongoDB holds it rather than Postgres, because this is operational state of the same kind as the broker settings and the daily login results that already live there, and because the evidence recorded alongside the numbers has no fixed shape.
"""

from datetime import datetime

import pymongo

from utilities.configuration import mongodb_configuration

CAPACITY_COLLECTION = "stream_capacity"


def open_mongodb_database():
    """
    Open the MongoDB database holding streaming capacity.

    Returns:
        tuple: A (client, database) pair. The caller closes the client when finished.

    Raises:
        pymongo.errors.PyMongoError: If MongoDB cannot be reached.
    """
    client = pymongo.MongoClient(mongodb_configuration["connection_string"])
    return (client, client[mongodb_configuration["database"]])


def read_capacity(broker_name):
    """
    Read the last measured capacity for one broker.

    Args:
        broker_name (str): The broker name, for example "zerodha".

    Returns:
        dict | None: The stored document without its MongoDB identifier, carrying at least "connection_count" and "instruments_per_connection", or None when this broker has never been measured.

    Raises:
        pymongo.errors.PyMongoError: If MongoDB cannot be reached.
    """
    client, database = open_mongodb_database()
    try:
        return database[CAPACITY_COLLECTION].find_one({"broker_name": broker_name}, {"_id": 0})
    finally:
        client.close()


def write_capacity(broker_name, connection_count, instruments_per_connection, refusal_reason, evidence):
    """
    Record what a broker was measured to allow, replacing any earlier measurement.

    Args:
        broker_name (str): The broker name, for example "zerodha".
        connection_count (int): How many simultaneous connections to use, after any safety margin has been applied by the caller.
        instruments_per_connection (int): How many instruments to put on each connection, after any safety margin.
        refusal_reason (str | None): How the broker signalled that it would give no more, for example "handshake_status_429", or None when the probe stopped at its own ceiling instead.
        evidence (list[dict]): What was observed at each step, kept so that a later argument about what the broker allowed can be settled from a record rather than from memory.

    Returns:
        dict: The document that was stored.

    Raises:
        pymongo.errors.PyMongoError: If MongoDB cannot be reached.
    """
    document = {
        "broker_name": broker_name,
        "connection_count": connection_count,
        "instruments_per_connection": instruments_per_connection,
        "last_refusal_reason": refusal_reason,
        "evidence": evidence,
        "measured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
    }
    client, database = open_mongodb_database()
    try:
        database[CAPACITY_COLLECTION].replace_one({"broker_name": broker_name}, document, upsert=True)
    finally:
        client.close()
    return document
