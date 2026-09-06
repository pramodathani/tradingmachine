# utilities/configuration.py

Environment-derived configuration for the data layer, read once at import time and exposed as one dictionary per datastore. This follows the house pattern from `unified_broker_interface/utils/config.py` and from the `util/config.py` of an earlier project, also named tradingmachine, whose checkout has since been deleted from this machine: module-level dictionaries, so that code elsewhere does `from utilities.configuration import *` rather than reading `os.environ` directly.

Of the two, the earlier project's version was the model, because it builds each `connection_string` from the dictionary it just created rather than re-reading `os.environ` a dozen times as UBI's does.

## Hosts are localhost by design

tradingmachine always runs on the host, and only its databases are containers. So the hosts here are `localhost` and the ports are the host-side published ports, not the container-internal ones. Inside the Docker network those same stores answer to `redis:6379`, `mongodb:27017`, `timescaledb:5432`, and `chroma:8000` instead.

## No environment tiers

There is no `TRADINGMACHINE_ENV` variable and no `.env.dev`, `.env.uat`, or `.env.prod`. This project deliberately has no tier system, so the bare `.env` that `load_dotenv()` finds is the whole configuration. The sibling projects require `set -a; source .env.dev; set +a` to select a variant; nothing equivalent is needed here.

## Three departures from the sibling modules

### `__all__` is defined

Without it, `from utilities.configuration import *` also exports `os`, `load_dotenv`, and `quote_plus`, which then silently shadow those names in the importing module. The siblings have this problem. Verified that `import *` now leaks nothing.

### Credentials are percent-encoded

`unified_broker_interface`'s config module imports `quote_plus` and then never applies it. That is latent breakage rather than a present bug, because the current password is alphanumeric. Credentials sit in the userinfo component of the connection URL, so a rotated password containing `@`, `:`, or `/` would be parsed as a delimiter and would silently produce a connection string pointing somewhere else.

Verified with the password `p@ss:w/rd#1`, which encodes to `p%40ss%3Aw%2Frd%231` and leaves the host, port, and database name still parsing correctly.

### chromadb_configuration carries no credentials

Chroma removed server-side authentication entirely in version 1.0.0, so there is nothing to authenticate with. The sibling modules carry `username` and `password` keys for Chroma that can only ever be `None`. Pass `host` and `port` to `chromadb.HttpClient()`. The `connection_string` key is there for anything that wants the base URL directly.

## Naming

Identifiers here are spelled out in full, per the project-wide convention. The dictionaries are named `redis_configuration` rather than `redis_config`, and the key holding the database name is `database` rather than `db`, including in the matching `TRADINGMACHINE_*_DATABASE` environment variables. This diverges from both sibling projects, which use `*_config` and `db` throughout.

The package directory is `utilities/` rather than `util/`, and the module is `configuration.py` rather than `config.py`, for the same reason, so the import is `from utilities.configuration import *`. The sibling projects use `util/config.py` and `utils/config.py` respectively.

Two names are set by libraries and cannot follow the convention: redis-py's client takes a `db=` keyword argument, and the TimescaleDB and MongoDB images own `POSTGRES_DB`, `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD`.

## postgres_configuration serves both roles

One container serves both the relational and the timeseries workload, because TimescaleDB is a Postgres extension rather than a separate server. Hypertables and ordinary relational tables live in the same database. The dictionary is still named `postgres_configuration` for parity with the sibling projects.

The connection string uses the bare `postgresql://` scheme rather than `postgresql+psycopg2://`, matching the siblings. SQLAlchemy resolves it to psycopg2, the pinned driver, by default.

## Known rough edge, inherited from the siblings

With no `.env` present and no `TRADINGMACHINE_*` variables set, `postgres_configuration["connection_string"]` evaluates to `postgresql://:@localhost:1003/None` rather than raising a clear error. Both sibling modules behave the same way, and worse, producing `None:None@`. It only bites if the module is imported with no configuration at all, which would fail at connection time regardless, though with a more confusing message. Left matching house behaviour rather than adding validation that was not requested.

## Verification

All four clients were driven purely from these dictionaries against the running containers: Redis `ping` returned true, SQLAlchemy through `postgres_configuration["connection_string"]` reported `current_database()` as `tradingmachine` with TimescaleDB 2.29.1, `MongoClient` built from the Mongo connection string answered `{'ok': 1.0}`, and `chromadb.HttpClient` returned a heartbeat.

The host and port defaults were verified separately, from an isolated copy of the module with no `.env` reachable anywhere up the tree. An earlier attempt at this check was invalid, because the defaults are deliberately identical to the `.env` values and so could not distinguish a default being applied from `.env` being reloaded.

## stream_configuration and the market data subsystem

The market data stream added a fifth dictionary. It breaks the "one dictionary per datastore" description of this module, because it is not a datastore: it is the set of tunables for the streaming processes, covering where the raw archive is written, how often it is flushed and rotated, how long ticks are buffered before each Redis flush, how large a batch the TimescaleDB writer accumulates, and how many websocket connections the supervisor may open.

They live here rather than in the streaming package for the same reason the datastore settings do. Everything that reads the environment reads it in one place, so there is one file to look at when asking what a running process was configured with, and `__all__` still controls what a star import brings in.

Two of these values are worth singling out. `archive_directory` defaults to `/data/tradingmachine_archive`, which is a dedicated ext4 filesystem on its own NVMe rather than a directory under the project, because the archive is expected to grow by tens of gigabytes a day and must not be able to fill the root filesystem. `timescale_queue_rows` bounds the in-memory queue in front of the database writer, and it is the value that decides how long a database outage can last before ticks start being dropped from the queue; they are never lost, because the archive has them and the replay tool can put them back.

## broker_stream_setting exists because brokers differ

Every value in `stream_configuration` can be overridden for a single broker by putting the broker name into the variable, so `TRADINGMACHINE_STREAM_ZERODHA_SEED_CONNECTION_COUNT` overrides `seed_connection_count` for Zerodha alone and leaves every other broker on the shared default.

This exists because the numbers that matter most are the ones brokers disagree about. Zerodha documents three websocket connections per API key and three thousand instruments on each, and in practice accepts far more; another broker will have entirely different real limits. Without the override, adding a second broker whose limits differ would mean either changing the shared default and disturbing the first broker, or adding code. With it, a broker's limits are deployment configuration.

The function converts the override to the type of the shared value, so a setting that defaults to an integer stays an integer. The check for `bool` comes before the check for `int` deliberately, since `bool` is a subclass of `int` in Python and the order would otherwise turn a boolean setting into `0` or `1`.
