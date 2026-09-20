# src/tradingmachine/utilities/configuration.py

This module is the one place that knows which environment variable holds which setting. Every other module asks it rather than calling `os.getenv` for itself, so each variable name appears exactly once in the codebase.

It originally held two module-level dictionaries, `ubi_configuration` and `mongodb_configuration`, built at import time by a bare `dotenv.load_dotenv()` at the top of the file. That followed `utilities/configurations.py` in the sibling project `unified_broker_interface`. The user chose on 2026-09-20, while converting the project into an installable library, to replace both with a single `Configuration` class that reads lazily.

## What it holds

| Property | Environment variable |
|---|---|
| `ubi_base_url` | `TRADINGMACHINE_UBI_BASE_URL` |
| `mongodb_host` | `TRADINGMACHINE_MONGODB_HOST` |
| `mongodb_port` | `TRADINGMACHINE_MONGODB_PORT` |
| `mongodb_database_name` | `TRADINGMACHINE_MONGODB_DB` |
| `mongodb_username` | `TRADINGMACHINE_MONGODB_USERNAME` |
| `mongodb_password` | `TRADINGMACHINE_MONGODB_PASSWORD` |
| `mongodb_connection_string` | Assembled from the four above |

Only the two services that code uses so far are configured. Redis and TimescaleDB properties should be added here when the first code needs them, reading the `TRADINGMACHINE_REDIS_*` and `TRADINGMACHINE_TIMESCALEDB_*` variables that `.env` already defines.

## Why it reads lazily

Reading at import time is fine for a script and wrong for a library. `import tradingmachine.assets.equities` pulls this module in transitively, and under the old design that single import went looking at the filesystem for a `.env` file before the caller had done anything at all. On a machine with no such file it silently produced a `mongodb_connection_string` reading `mongodb://:@None:None/?authSource=admin`, which then failed much later with a confusing error from `pymongo`.

Now `__init__` stores three attributes and reads nothing. `_ensure_environment_file_loaded` runs on the first property access, sets its flag before doing any work so a second access is a single boolean check, and calls `dotenv.load_dotenv` at most once. Importing the library therefore touches nothing outside the process.

## The three ways to point it somewhere

| What the caller wants | How they ask |
|---|---|
| The `.env` in the working directory or a parent | `Configuration()` |
| A file somewhere else | `Configuration(environment_file="/etc/tradingmachine.env")` |
| Only the exported environment, with no file read | `Configuration(load_environment_file=False)` |

`reload()` clears the flag so the next read loads the file again. It exists for a long-running process whose `.env` has changed on disk, and nothing in the library calls it.

`dotenv.load_dotenv` never overrides a variable that is already set in the process environment, so an exported value always beats the file. That was true of the old design too and is worth remembering when a change to `.env` appears to have no effect.

## Decisions carried over from the dictionaries

The MongoDB connection string ends in `/?authSource=admin`, because the container creates its root user in the `admin` database (see `docker-compose.yml.md`). Without it, authentication fails against the `tradingmachine` database.

The username and password are passed through `urllib.parse.quote_plus` before they go into the connection string. MongoDB URIs reject unescaped `@`, `:` and `/` in credentials, and generated passwords can contain them. A missing value becomes an empty string rather than the text `None`.

The port is kept as a string, because it is only ever interpolated into the connection string.

`TRADINGMACHINE_UBI_BASE_URL` is set to `http://127.0.0.1:8080` in `.env`. UBI binds to `127.0.0.1` by default (`UNIFIED_BROKER_INTERFACE_API_HOST`), so, unlike the databases, it is not reachable through the LAN address `192.168.1.2`.

## How the client gets one

`UnifiedBrokerInterface.__init__` takes an optional `project_configuration` and builds a plain `Configuration()` when it is not given, so the default behaviour is exactly what it was before. The parameter is named `project_configuration` rather than `configuration` because the module itself is imported under that name, and a parameter called `configuration` would shadow it inside the method.

Instruments already accept an optional `unified_broker_interface`, so a caller who wants their own settings builds a `Configuration`, hands it to a client, and hands that client to an instrument. There is deliberately no global default configuration object and no `set_configuration` function, because module-level mutable state is exactly what the class was introduced to remove.
