"""
Environment-derived configuration for the black_box data layer.

Reads the process environment once at import time and exposes one dictionary per datastore. Code elsewhere does `from utilities.configuration import *` rather than reading os.environ directly.
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
]

redis_configuration = {
    "host": os.environ.get("BLACK_BOX_REDIS_HOST", "localhost"),
    "port": int(os.environ.get("BLACK_BOX_REDIS_PORT", "10001")),
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
