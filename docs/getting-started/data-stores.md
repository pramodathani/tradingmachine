# Data stores

Three databases run in Docker containers defined by `docker-compose.yml` in the repository root.
Compose reads their ports and passwords from the same `.env` the Python code reads, so there is
one place to change a password and it changes everywhere.

```bash
docker compose up -d
docker compose ps
docker compose down
```

| Service | Image | Host port | Volume | Used today for |
| --- | --- | --- | --- | --- |
| Redis | `redis:trixie` | 2002 | `tradingmachine_redis_volume` | Nothing yet |
| MongoDB | `mongo:8.0.4` | 2003 | `tradingmachine_mongodb_volume` | The UBI api key and secret |
| TimescaleDB | `timescale/timescaledb:latest-pg18` | 2004 | `tradingmachine_timescaledb_volume` | Nothing yet |

Only MongoDB is on the critical path at the moment. Redis and TimescaleDB are up so that the
storage layer has somewhere to land when it is written, and because bringing all three up together
is one command rather than three decisions.

## Why the ports look arbitrary

They are chosen to stay out of the sibling project's way. `unified_broker_interface` runs its own
Redis, MongoDB and TimescaleDB containers on ports 1002 to 1005 on the same machine, so this
project takes the 2000 block. Two independent sets of containers, two independent sets of data,
and no chance of one project's `docker compose down -v` taking the other's data with it.

## Details worth knowing

**Every port is published on `0.0.0.0`**, so the databases are reachable from other machines on
the local network, and `.env` points the clients at this machine's local network address rather
than at `127.0.0.1`.

**MongoDB is created with a root user**, which is why every client has to authenticate against the
`admin` database rather than against `tradingmachine`. `utilities.configuration` puts
`authSource=admin` into the connection string for exactly this reason, so code that builds its own
connection string by hand and forgets it will fail to authenticate with a confusing message.

**Redis requires a password for the `default` user**, set by `--requirepass` on the server command
line, and it runs with append-only persistence so a restart does not lose what is in it.

**TimescaleDB is PostgreSQL 18 with the `timescaledb` extension**, and the container is given a
gigabyte of shared memory because PostgreSQL's parallel queries need more than Docker's default
64 MB.

**Every container has a healthcheck and restarts unless stopped**, so `docker compose ps` shows
`healthy` rather than merely `running`, and a reboot brings all three back.

!!! danger "`docker compose down -v` deletes the data"

    The `-v` flag removes the three named `tradingmachine_*_volume` volumes along with the
    containers. For MongoDB that means the hand-seeded UBI credentials document is gone and has to
    be recreated, as described in [Configuration](configuration.md). Plain `docker compose down`
    keeps every volume.

The reasoning behind the compose file, including why each of these choices was made, is in
`.claude/notes/docker-compose.yml.md` in the repository.
