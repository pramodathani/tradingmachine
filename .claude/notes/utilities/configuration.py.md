# utilities/configuration.py

This module reads the environment once, on import, and exposes one dictionary per external service. Other modules import these dictionaries instead of calling `os.getenv` themselves, so every environment variable name appears in exactly one place. The pattern follows `utilities/configurations.py` in the sibling project `unified_broker_interface`, with names spelled out in full (`mongodb_configuration`, not `mongodb_config`).

## What it holds

| Dictionary | Keys | Environment variables |
|---|---|---|
| `ubi_configuration` | `base_url` | `TRADINGMACHINE_UBI_BASE_URL` |
| `mongodb_configuration` | `host`, `port`, `db`, `username`, `password`, `connection_string` | `TRADINGMACHINE_MONGODB_*` |

Only the two services that code uses so far are configured. Redis and TimescaleDB dictionaries should be added here when the first code needs them, reading the `TRADINGMACHINE_REDIS_*` and `TRADINGMACHINE_TIMESCALEDB_*` variables that `.env` already defines.

## Decisions

`dotenv.load_dotenv()` loads only a bare `.env` from the working directory or its parents, and it never overrides a variable that is already set in the process environment. To run against a different file, export it into the environment first.

The MongoDB connection string ends in `/?authSource=admin`, because the container creates its root user in the `admin` database (see `docker-compose.yml.md`). Without it, authentication fails against the `tradingmachine` database.

The username and password are passed through `urllib.parse.quote_plus` before they go into the connection string. MongoDB URIs reject unescaped `@`, `:` and `/` in credentials, and generated passwords can contain them. A missing value becomes an empty string rather than the text `None`.

The port is kept as a string, because it is only ever interpolated into the connection string.

`TRADINGMACHINE_UBI_BASE_URL` is set to `http://127.0.0.1:8080` in `.env`. UBI binds to `127.0.0.1` by default (`UNIFIED_BROKER_INTERFACE_API_HOST`), so, unlike the databases, it is not reachable through the LAN address `192.168.1.2`.
