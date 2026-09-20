# Configuration

Everything configurable lives in one gitignored `.env` file in the repository root. Two readers
share it: Docker Compose, which takes the ports and passwords for the containers, and
`tradingmachine.utilities.configuration.Configuration`, which builds the settings the Python code
uses. Because Trading Machine is an installed library, that file is a convenience rather than a
requirement, and a caller who exports the variables another way never needs one.

## The variables

| Variable | Read by | What it is |
| --- | --- | --- |
| `TRADINGMACHINE_UBI_BASE_URL` | `Configuration` | Where UBI is served, normally `http://127.0.0.1:8080` |
| `TRADINGMACHINE_MONGODB_HOST` | Both | The address the container is reachable at, which is this machine's address on the local network rather than `127.0.0.1`, because the ports are published on `0.0.0.0` |
| `TRADINGMACHINE_MONGODB_PORT` | Both | Host port for MongoDB, `2003` by default |
| `TRADINGMACHINE_MONGODB_DB` | `Configuration` | The database holding the `settings` collection |
| `TRADINGMACHINE_MONGODB_USERNAME` | Both | The root user Compose creates |
| `TRADINGMACHINE_MONGODB_PASSWORD` | Both | That user's password |
| `TRADINGMACHINE_REDIS_*` | Compose | Host, port, database number, username and password |
| `TRADINGMACHINE_TIMESCALEDB_*` | Compose | Host, port, database, username and password |

Redis and TimescaleDB are brought up by Compose and their variables are read there, but no Python
module reads them yet. They are in place for the storage layer the
[dependency list](installation.md) anticipates.

## What the code actually reads

`tradingmachine.utilities.configuration` holds one class, `Configuration`, and it is deliberately
small. It is the only place that knows which environment variable holds which setting, and every
other module asks it rather than calling `os.getenv` for itself.

```python
from tradingmachine.utilities import configuration

project_configuration = configuration.Configuration()

project_configuration.ubi_base_url
project_configuration.mongodb_connection_string
```

Nothing is read when the module is imported. The first property access loads the `.env` file, and
every value is read from the process environment at that moment. That laziness is what makes the
library safe to import: bringing in `tradingmachine.assets.equities` does not go looking at your
filesystem, and it does not fail on a machine that has no `.env` at all.

Three arguments control where the settings come from.

| What you want | How to ask for it |
| --- | --- |
| The `.env` in the working directory or a parent of it | `Configuration()` |
| A file somewhere else | `Configuration(environment_file="/etc/tradingmachine.env")` |
| Only what is already exported in the shell, with no file read | `Configuration(load_environment_file=False)` |
| The file read again, after you have changed it | `project_configuration.reload()` |

`dotenv` never overrides a variable that is already set in the process environment, so an exported
value always wins over the file.

To use your own settings, build the configuration and hand it to the client, then hand the client
to your instruments.

```python
from tradingmachine.assets import equities
from tradingmachine.ubi_client import client
from tradingmachine.utilities import configuration

unified_broker_interface = client.UnifiedBrokerInterface(
    project_configuration=configuration.Configuration(environment_file="/etc/tradingmachine.env")
)
infosys = equities.Equity(
    exchange="nse",
    symbol="INFY",
    unified_broker_interface=unified_broker_interface,
)
```

The MongoDB connection string is assembled by the class rather than kept in `.env`, so the
username and password are percent-escaped exactly once and `authSource=admin` is never forgotten.
That last part matters: Compose creates a root user, and a root user authenticates against `admin`
rather than against the application database.

```
mongodb://<username>:<password>@<host>:<port>/?authSource=admin
```

## The credentials UBI needs

The base url is not enough to talk to UBI. `tradingmachine.ubi_client.client.UnifiedBrokerInterface` reads an api key
and secret out of this project's MongoDB, from a single document in the `settings` collection.

```javascript
{
  "broker_name": "unified_broker_interface",
  "api_key": "...",
  "api_secret": "..."
}
```

!!! warning "This document is seeded by hand"

    No code in this project creates it. The same key and secret must also be present in UBI's own
    MongoDB, which is a separate database on a separate port, or UBI will refuse the connect call.
    If `connect` raises an `AuthenticationError`, a mismatch between those two documents is the
    first thing to check.

See [The UBI client](../architecture/ubi-client.md) for what happens to the token once the
credentials are found.
