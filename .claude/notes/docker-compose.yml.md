# docker-compose.yml

The black_box data layer. Only the databases are containerized. black_box itself always runs on the host, so there is no `app` service and no Dockerfile. The sibling projects gate an app service behind `profiles: ["app"]` to support their UAT and prod deployments, and that is deliberately omitted here.

The top-level `name: black_box` sets the Compose project name, so a bare `docker compose up -d` works without passing `-p`.

## Networking

All four services share one bridge network, `black_box_network`. Inside it they resolve each other by service name on the container port: `redis:6379`, `mongodb:27017`, `timescaledb:5432`, `chroma:8000`. That is independent of the host ports below. The host-side black_box process does not join this network; it connects through the published ports on localhost instead.

These containers are black_box's own. Following the rule stated in `tradingmachine/README.md`, each project runs its own Compose project on its own network, never joined to `unified_broker_interface`'s or `tradingmachine`'s, and shares no key, collection, or table with them.

## Host ports

| Store | Host port | Container port |
|---|---|---|
| Redis | 1001 | 6379 |
| MongoDB | 1002 | 27017 |
| TimescaleDB | 1003 | 5432 |
| ChromaDB | 1004 | 8000 |

All four ports fall below 1024, in the IANA system range. This was raised with the user and confirmed as intended. The Docker daemon runs as root and can bind privileged ports, and the host-side Python client needs no privileges to connect to them. A rootless Docker setup would refuse these bindings without a `net.ipv4.ip_unprivileged_port_start` change, which is not the case on this machine.

None of these collide with the running sibling containers on 5432, 5434, 6379, 6381, 27017, 27019, 8002, and 8890, nor with the tier bands `unified_broker_interface` reserves for its own UAT and prod on 5433, 6380, 8000, 8001, 27018, 8888, and 8889.

## Published on 127.0.0.1 rather than 0.0.0.0

The sibling projects bind every port to all interfaces, which exposes the stores to anything routable to this machine. The only consumer here is a host-side process, so binding to loopback is sufficient and strictly safer. It matters most for Chroma, which has no password at all, and it keeps the shared database password off the network.

## Per-service notes

### redis

The password is passed into the container as `REDIS_PASSWORD` as well as into the `command`, because the healthcheck needs to expand it at runtime. The `$$` in the healthcheck escapes Compose interpolation so the container's own shell expands the variable, rather than Compose substituting it at parse time.

The RedisInsight port mapping that `unified_broker_interface` carries was deliberately dropped. That project maps `${UBI_REDIS_INSIGHT_PORT}:8001`, but the `redis:trixie` image ships no RedisInsight binary. This was verified by inspecting the running container. The mapping forwards to nothing.

### timescaledb

One container serves both the relational and the timeseries role. TimescaleDB is a Postgres extension, not a separate database engine, so there is no second Postgres container. The image ships `000_install_timescaledb.sh`, which creates the extension in `POSTGRES_DB` on first initialization. Verified present as version 2.29.1. Hypertables are then ordinary application-side DDL, such as `SELECT create_hypertable('ohlcv', 'ts')`.

`shm_size: 256m` is required because Postgres parallel workers exhaust Docker's 64MB default `/dev/shm`.

`PGDATA` is set to `/pgdata` and the volume is mounted there, rather than at the image's default location under `/var/lib/postgresql`.

### chroma

Chroma has no built-in server-side authentication. It was removed entirely in version 1.0.0 as a breaking change, and the project now recommends fronting the server with a reverse proxy for access control. That is why this service has no username or password while the other three do. Access control here is the Docker network boundary plus the loopback-only publish.

Chroma always listens on port 8000 inside the container. That is hardcoded by the image and is not configurable; only the host-side port can be changed.

The healthcheck uses bash's `/dev/tcp` rather than Chroma's own documented curl-based example, because the image contains no curl or wget. This was confirmed by inspecting the container. Bash must be invoked explicitly, because `CMD-SHELL` uses `/bin/sh`, which is dash on this image, and dash does not support `/dev/tcp`. The port in the healthcheck is the container's fixed internal 8000, not the host-mapped port.

## restart: unless-stopped

The sibling projects set no restart policy. This one does, so that the stores come back after a host reboot without manual intervention, which matters for a system expected to be running during market hours.

## Volumes

Volume names carry no environment suffix, because this project has no dev, UAT, or prod tier system. The siblings interpolate `${..._ENV:-dev}` into theirs so their tiers do not collide on disk.
