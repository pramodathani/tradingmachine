# docker-compose.yml

This file runs the three databases the project depends on, each in its own Docker container: Redis, MongoDB and TimescaleDB. It was adapted from the `docker-compose.yml` of the sibling project `unified_broker_interface`, keeping the same structure, images, healthchecks and restart policy, with the project, volume, network and variable names changed to `tradingmachine`.

## Services, ports and names

| Service | Image | Host port | Container port | Volume |
|---|---|---|---|---|
| `redis` | `redis:trixie` | 2002 | 6379 | `tradingmachine_redis_volume` |
| `mongodb` | `mongo:8.0.4` | 2003 | 27017 | `tradingmachine_mongodb_volume` |
| `timescaledb` | `timescale/timescaledb:latest-pg18` | 2004 | 5432 | `tradingmachine_timescaledb_volume` |

All three services share the bridge network `tradingmachine_network`. Ports are bound on `0.0.0.0`, so they are reachable from other machines on the local network, and `.env` points clients at this machine's LAN address, `192.168.1.2`.

Ports 2002 to 2004 were chosen so that this project can run alongside `unified_broker_interface`, whose containers use 1002 to 1005 on the same machine.

## Variables read from `.env`

Docker Compose loads `.env` from the project folder automatically. The containers read only some of the variables; the rest exist for the Python clients.

| Variable | Read by the container | Used for |
|---|---|---|
| `TRADINGMACHINE_REDIS_PASSWORD` | Yes | `--requirepass` and the healthcheck |
| `TRADINGMACHINE_REDIS_PORT` | Yes | Published host port, defaulting to 2002 |
| `TRADINGMACHINE_REDIS_HOST`, `_DB`, `_USERNAME` | No | Client connection only |
| `TRADINGMACHINE_MONGODB_USERNAME` | Yes | Root user name, defaulting to `tradingmachine` |
| `TRADINGMACHINE_MONGODB_PASSWORD` | Yes | Root user password |
| `TRADINGMACHINE_MONGODB_PORT` | Yes | Published host port, defaulting to 2003 |
| `TRADINGMACHINE_MONGODB_HOST`, `_DB` | No | Client connection only |
| `TRADINGMACHINE_TIMESCALEDB_DB` | Yes | Database created at first start, defaulting to `tradingmachine` |
| `TRADINGMACHINE_TIMESCALEDB_USERNAME` | Yes | Superuser name, defaulting to `tradingmachine` |
| `TRADINGMACHINE_TIMESCALEDB_PASSWORD` | Yes | Superuser password |
| `TRADINGMACHINE_TIMESCALEDB_PORT` | Yes | Published host port, defaulting to 2004 |
| `TRADINGMACHINE_TIMESCALEDB_HOST` | No | Client connection only |

The TimescaleDB variables are spelled `TIMESCALEDB` rather than `POSTGRES`, matching the service name and the `unified_broker_interface` convention. `.env` originally used `TRADINGMACHINE_POSTGRES_*`, and those keys were renamed when this file was added.

The `PYTHONPATH = ...` line in `.env` refers to `$PYTHONPATH`, so Compose warns that the variable is not set. The warning is harmless because no container uses it.

## Details per service

Redis sets its password with `--requirepass`, which assigns it to the built-in `default` user; that is why `.env` sets the Redis username to `default`. Append-only persistence is enabled so data survives restarts. The healthcheck uses `$$` so that Compose passes `$REDIS_PASSWORD` through to the container's shell instead of interpolating it itself.

MongoDB creates the root user in the `admin` database, so clients must connect with `authSource=admin`. The `tradingmachine` database named in `.env` does not exist until something first writes to it.

TimescaleDB stores its data in `/pgdata` rather than the image default, and it has a 1 GB shared memory segment, because PostgreSQL's parallel queries can exhaust Docker's 64 MB default. The image installs the `timescaledb` extension into the database it creates at first start.

## Credentials only apply to a new volume

The username, password and database variables are read only when a container starts with an empty volume. Changing them in `.env` afterwards does not change the existing database. To change a credential, either change it inside the running database, or delete the volume with `docker compose down -v`, which destroys all of that service's data. Redis is the exception, because `--requirepass` is applied on every start.

## Services left out

The template also defines `chroma`, `nginx` and `certbot`. ChromaDB was deferred at the user's request, and nginx and certbot were not needed because this project has no postback domain yet.

## Verified on 2026-09-14

After `docker compose up -d`, all three services reported healthy, and a Python check using the `.env` values succeeded: Redis 8.10.1 answered `PING`, MongoDB 8.0.4 answered `ping`, and PostgreSQL 18.6 reported the `timescaledb` extension at version 2.30.0.
