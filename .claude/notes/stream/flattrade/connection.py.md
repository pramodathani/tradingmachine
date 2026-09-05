# stream/flattrade/connection.py

## Why one connection class covers both feeds

Dhan needed a separate depth connection because its depth wire has a different binary shape and its own URL. Flattrade's touchline and depth are the same socket, the same JSON text frames, and messages that differ only in the subscribe type (`t` versus `d`), so a second class would be parameterised on nothing. The `mode` parameter follows Dhan's single-class three-mode shape instead of its two-file layout.

## Authentication happens in-band, so the refusal taxonomy shifts

The socket opens with no credentials at all; the client's first message must be the connect request, and the server answers with an `ak` acknowledgement. That moves the authentication signal off the handshake and onto the wire, which changes how refusals are classified:

- `Not_Ok` on the first session ever means the credentials are wrong, and raises `FlattradeAuthenticationError` — retrying cannot help.
- `Not_Ok` on a later session, while earlier ones worked, means the credentials are fine and this connection was one too many. This is the only way Flattrade has been observed to refuse a connection, so it raises `FlattradeConnectionRefusedError("connect_not_ok")`.
- No acknowledgement within ten seconds raises `FlattradeConnectionRefusedError("connect_ack_timeout")`, because an open socket that never answers the connect message is what "accepted but not served" means on this protocol.

The handshake status taxonomy (429/503 refusals, 401/403 authentication) is kept for parity with the other brokers even though Flattrade signals authentication on the socket; a live run that shows a handshake status doing real work should be written down here.

## The heartbeat is two things, and only one of them is ours

The websockets library's protocol pings (`ping_interval=20`) detect a half-open socket. The application heartbeat `{"t":"h"}` every thirty seconds is Flattrade's own keepalive, documented as required, and is sent by a separate asyncio task so a slow or missing heartbeat can never block the read loop. The heartbeat acknowledgement (`hk`) is counted in `heartbeats_received` but deliberately does not refresh `last_data_frame_at` — on an all-text protocol the heartbeat acknowledgement looks exactly like data to a naive counter, and it is heartbeats that a silently-unserved connection keeps sending.

## Every frame goes to the archive, not only market data

`on_frame` receives every frame encoded to UTF-8, whatever it carries, because the archive is the system of record for what came off the socket and `frame_packet_count` already reports zero for the non-data frames, so the manifest's reconciliation is unaffected. Frames that are not market data also go to `on_text`, which is how order and position updates reach a caller without touching the market data path. The one asymmetry: frames read during the authentication wait are accounted but not handed to `on_frame`, since nothing market-shaped can arrive before the subscription is sent.

## Resubscription is mandatory on every session

Flattrade retains no subscription state across connections, and its own client library has resubscription commented out, so a reconnected socket would sit open and permanently silent — the Zerodha failure mode word for word. `_send_subscription` therefore runs on every session, batching instruments one hundred per message, a choice rather than a documented rule that the first live run validates by counting one `tk`/`dk` per subscribed scrip.

## Batch size one hundred is a choice, not a rule

Flattrade documents no limit on the `k` field. One hundred per message is conservative and easy to widen after a live run; the connection constants are where a probe-validated change lands.

## Mutation testing

`check_connection_message_builders` pins the builders' JSON to their literal field names and values, plus the websocket URL and the heartbeat interval, because the connection and the decoder never touch the same wire direction and a renamed field in a builder would otherwise pass every decoder check unnoticed.