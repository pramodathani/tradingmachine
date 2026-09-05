"""
Environment-derived configuration for the black_box data layer.

Reads the process environment once at import time and exposes one dictionary per datastore, plus one dictionary of settings for the market data streaming subsystem. Code elsewhere does `from utilities.configuration import *` rather than reading os.environ directly.
"""

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

__all__ = [
    "redis_configuration",
    "mongodb_configuration",
    "postgres_configuration",
    "chromadb_configuration",
    "stream_configuration",
    "broker_stream_setting",
]

redis_configuration = {
    "host": os.environ.get("BLACK_BOX_REDIS_HOST", "localhost"),
    "port": int(os.environ.get("BLACK_BOX_REDIS_PORT", "1001")),
    "database": int(os.environ.get("BLACK_BOX_REDIS_DATABASE", "0")),
    "username": os.environ.get("BLACK_BOX_REDIS_USERNAME"),
    "password": os.environ.get("BLACK_BOX_REDIS_PASSWORD"),
}

mongodb_configuration = {
    "host": os.environ.get("BLACK_BOX_MONGODB_HOST", "localhost"),
    "port": int(os.environ.get("BLACK_BOX_MONGODB_PORT", "1002")),
    "database": os.environ.get("BLACK_BOX_MONGODB_DATABASE"),
    "username": os.environ.get("BLACK_BOX_MONGODB_USERNAME"),
    "password": os.environ.get("BLACK_BOX_MONGODB_PASSWORD"),
}
mongodb_configuration["connection_string"] = (
    f"mongodb://{quote_plus(mongodb_configuration['username'] or '')}"
    f":{quote_plus(mongodb_configuration['password'] or '')}"
    f"@{mongodb_configuration['host']}:{mongodb_configuration['port']}/"
)

postgres_configuration = {
    "host": os.environ.get("BLACK_BOX_POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("BLACK_BOX_POSTGRES_PORT", "1003")),
    "database": os.environ.get("BLACK_BOX_POSTGRES_DATABASE"),
    "username": os.environ.get("BLACK_BOX_POSTGRES_USERNAME"),
    "password": os.environ.get("BLACK_BOX_POSTGRES_PASSWORD"),
}
postgres_configuration["connection_string"] = (
    f"postgresql://{quote_plus(postgres_configuration['username'] or '')}"
    f":{quote_plus(postgres_configuration['password'] or '')}"
    f"@{postgres_configuration['host']}:{postgres_configuration['port']}/{postgres_configuration['database']}"
)

chromadb_configuration = {
    "host": os.environ.get("BLACK_BOX_CHROMADB_HOST", "localhost"),
    "port": int(os.environ.get("BLACK_BOX_CHROMADB_PORT", "1004")),
    "database": os.environ.get("BLACK_BOX_CHROMADB_DATABASE"),
}
chromadb_configuration["connection_string"] = (
    f"http://{chromadb_configuration['host']}:{chromadb_configuration['port']}"
)

stream_configuration = {
    "archive_directory": os.environ.get("BLACK_BOX_STREAM_ARCHIVE_DIRECTORY", "/data/black_box_archive"),
    "cold_archive_directory": os.environ.get("BLACK_BOX_STREAM_COLD_ARCHIVE_DIRECTORY", "/data/black_box_cold/black_box_archive"),
    "compression_level": int(os.environ.get("BLACK_BOX_STREAM_COMPRESSION_LEVEL", "3")),
    "archive_rotation_seconds": int(os.environ.get("BLACK_BOX_STREAM_ARCHIVE_ROTATION_SECONDS", "900")),
    "archive_rotation_bytes": int(os.environ.get("BLACK_BOX_STREAM_ARCHIVE_ROTATION_BYTES", str(512 * 1024 * 1024))),
    "archive_sync_seconds": float(os.environ.get("BLACK_BOX_STREAM_ARCHIVE_SYNC_SECONDS", "5.0")),
    "publish_interval_seconds": float(os.environ.get("BLACK_BOX_STREAM_PUBLISH_INTERVAL_SECONDS", "0.1")),
    "last_value_cache_seconds": int(os.environ.get("BLACK_BOX_STREAM_LAST_VALUE_CACHE_SECONDS", "172800")),
    "timescale_batch_rows": int(os.environ.get("BLACK_BOX_STREAM_TIMESCALE_BATCH_ROWS", "20000")),
    "timescale_flush_seconds": float(os.environ.get("BLACK_BOX_STREAM_TIMESCALE_FLUSH_SECONDS", "1.0")),
    "timescale_queue_rows": int(os.environ.get("BLACK_BOX_STREAM_TIMESCALE_QUEUE_ROWS", "400000")),
    "seed_connection_count": int(os.environ.get("BLACK_BOX_STREAM_SEED_CONNECTION_COUNT", "20")),
    "seed_instruments_per_connection": int(os.environ.get("BLACK_BOX_STREAM_SEED_INSTRUMENTS_PER_CONNECTION", "4000")),
    "maximum_connection_count": int(os.environ.get("BLACK_BOX_STREAM_MAXIMUM_CONNECTION_COUNT", "40")),
    "minimum_free_archive_bytes": int(os.environ.get("BLACK_BOX_STREAM_MINIMUM_FREE_ARCHIVE_BYTES", str(50 * 1024 * 1024 * 1024))),
}


def broker_stream_setting(broker_name, setting_name):
    """
    Read one streaming setting for one broker, preferring a broker-specific override.

    Brokers differ in how many websocket connections they allow and how many instruments each connection will carry, so every setting in stream_configuration can be overridden for a single broker. The override variable puts the broker name after the BLACK_BOX_STREAM prefix, so the Zerodha seed connection count is BLACK_BOX_STREAM_ZERODHA_SEED_CONNECTION_COUNT. When no override is set the shared value from stream_configuration is used, which keeps the common case free of per-broker configuration.

    Args:
        broker_name (str): The broker the setting is being read for, for example "zerodha".
        setting_name (str): A key of stream_configuration, for example "seed_connection_count".

    Returns:
        int | float | str: The override converted to the type of the shared value, or the shared value itself when no override is set.

    Raises:
        KeyError: If setting_name is not a key of stream_configuration.
        ValueError: If an override is set but cannot be converted to the type of the shared value.
    """
    shared_value = stream_configuration[setting_name]
    variable_name = f"BLACK_BOX_STREAM_{broker_name.upper()}_{setting_name.upper()}"
    override = os.environ.get(variable_name)
    if override is None:
        return shared_value
    if isinstance(shared_value, bool):
        return override.strip().lower() in ("1", "true", "yes")
    if isinstance(shared_value, int):
        return int(override)
    if isinstance(shared_value, float):
        return float(override)
    return override
