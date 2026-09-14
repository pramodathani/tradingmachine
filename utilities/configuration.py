"""Configuration read from the environment and the project's `.env` file.

Each service the project talks to has one dictionary here, and other modules import the dictionary rather than reading environment variables themselves.

Typical usage example:

  from utilities import configuration

  base_url = configuration.ubi_configuration["base_url"]
"""

import os
import urllib.parse

import dotenv

dotenv.load_dotenv()

ubi_configuration = {
    "base_url": os.getenv("TRADINGMACHINE_UBI_BASE_URL"),
}

mongodb_configuration = {
    "host": os.getenv("TRADINGMACHINE_MONGODB_HOST"),
    "port": os.getenv("TRADINGMACHINE_MONGODB_PORT"),
    "db": os.getenv("TRADINGMACHINE_MONGODB_DB"),
    "username": os.getenv("TRADINGMACHINE_MONGODB_USERNAME"),
    "password": os.getenv("TRADINGMACHINE_MONGODB_PASSWORD"),
}
mongodb_configuration["connection_string"] = (
    "mongodb://"
    f"{urllib.parse.quote_plus(mongodb_configuration['username'] or '')}"
    f":{urllib.parse.quote_plus(mongodb_configuration['password'] or '')}"
    f"@{mongodb_configuration['host']}:{mongodb_configuration['port']}"
    "/?authSource=admin"
)
