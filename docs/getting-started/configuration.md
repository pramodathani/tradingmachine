# Configuration

Everything configurable lives in one gitignored `.env` file in the repository root. Two readers
share it: Docker Compose, which takes the ports and passwords for the containers, and
`utilities.configuration`, which builds the settings the Python code uses.

## The variables

| Variable | Read by | What it is |
| --- | --- | --- |
| `PYTHONPATH` | Tools that load `.env` | Set to `.` so that `from assets import equities` resolves from the project root |
| `TRADINGMACHINE_UBI_BASE_URL` | `utilities.configuration` | Where UBI is served, normally `http://127.0.0.1:8080` |
| `TRADINGMACHINE_MONGODB_HOST` | Both | The address the container is reachable at, which is this machine's address on the local network rather than `127.0.0.1`, because the ports are published on `0.0.0.0` |
| `TRADINGMACHINE_MONGODB_PORT` | Both | Host port for MongoDB, `2003` by default |
| `TRADINGMACHINE_MONGODB_DB` | `utilities.configuration` | The database holding the `settings` collection |
| `TRADINGMACHINE_MONGODB_USERNAME` | Both | The root user Compose creates |
| `TRADINGMACHINE_MONGODB_PASSWORD` | Both | That user's password |
| `TRADINGMACHINE_REDIS_*` | Compose | Host, port, database number, username and password |
| `TRADINGMACHINE_TIMESCALEDB_*` | Compose | Host, port, database, username and password |

Redis and TimescaleDB are brought up by Compose and their variables are read there, but no Python
module reads them yet. They are in place for the storage layer the
[dependency list](installation.md) anticipates.

## What the code actually reads

`utilities.configuration` is deliberately small. It loads `.env` once at import, exposes one
dictionary per service, and every other module imports the dictionary rather than calling
`os.getenv` for itself.

```python
from utilities import configuration

configuration.ubi_configuration["base_url"]
configuration.mongodb_configuration["connection_string"]
```

The MongoDB connection string is assembled in the module rather than kept in `.env`, so the
username and password are percent-escaped exactly once and `authSource=admin` is never forgotten.
That last part matters: Compose creates a root user, and a root user authenticates against `admin`
rather than against the application database.

```
mongodb://<username>:<password>@<host>:<port>/?authSource=admin
```

## The credentials UBI needs

The base url is not enough to talk to UBI. `ubi_client.UnifiedBrokerInterface` reads an api key
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
