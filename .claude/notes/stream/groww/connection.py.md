# stream/groww/connection.py

Drives one Groww connection: opens the websocket, authenticates the NATS session, subscribes, hands complete message operations to a callback, and reconnects. Same contract as every other broker's connection.

## Why NATS is hand-rolled

nats-py would work, and Groww's own SDK uses it. It is not used here for the same reasons none of the other brokers' connection drivers use their broker's SDK: the project's connections share one shape — one socket, `run(stop_event)`, `on_frame`, a three exception hierarchy, our own backoff — and a library with its own reconnect loop, its own thread and its own callback threading would have to be bent out of shape to fit. Hand-rolling also keeps the refusal classification inside our code, which the capacity probe depends on.

What was not guessed was the protocol itself. The CONNECT shape, the signature encoding and the operation grammar were taken from nats-py 2.15.0's source (`nats/aio/client.py`, `_connect_command`), downloaded to a scratch directory for the comparison. The one subtle point is the signature: nats-py base64-encodes the raw sixty four byte signature in standard base64 with padding, while this project's `sign_nonce` produces unpadded base64url. Both are accepted, because the NATS server tries `RawURLEncoding` first and falls back to `StdEncoding` (`server/auth.go`). The unpadded base64url form was kept because it is the Go-native convention.

## The credential split, again

The websocket opens with no headers; nothing about the account is sent at the websocket layer. Authentication happens entirely at the NATS layer: INFO carries a fresh nonce, CONNECT carries the socket token as a `jwt` field plus a signature over that nonce made with the session seed. Because the nonce is fresh per connection, signing happens per session. This is why `sign_nonce` lives in credentials and is called from the handshake rather than once at startup.

## Why the ProtocolReader exists, and why it raises

Every other broker's connection archives the websocket frame it received. Here that would be wrong: NATS is a byte stream, one websocket frame may carry a fragment, several messages, or a tail plus a head, and a protobuf payload can contain the same `\r\n` that ends a control line. The reader's state machine is therefore the single most important piece of code in this package: it yields one item per complete operation, and for a MSG it yields the header line, the payload and the trailing terminator as one record — the unit the archive stores.

It raises `GrowwConnectionError` on a malformed or implausible MSG header rather than trying to resynchronize, because once the stream desynchronizes every subsequent byte is garbage and the only honest recovery is to drop the socket and reconnect. This cannot happen while in sync — the reader only ever sees server bytes — so it is a safety net, not a path.

## Two keep-alive layers

The websockets library answers the websocket's own pings, which detects a half-open socket. Separately the connection sends a NATS PING every sixty seconds and answers the server's NATS PINGs with PONGs, matching the `ping_interval=60` of Groww's SDK. They do different jobs and both are needed; dropping the NATS one gets the socket closed by the bus for silence, and dropping the websocket one lets a dead socket sit undetected.

## ever_connected means "a session has authenticated"

The flag is set only after a handshake completes, not after the websocket opens. This is what gives the -ERR classification its meaning: an authorization violation before any session ever authenticated means the credentials are wrong, while the same error on a session that follows ones which worked means this connection was one too many — the bus's way of refusing. Getting this backwards would make the capacity probe misread a limit as a login failure and vice versa.

The websocket handshake status codes classify unconditionally, following the plan: 401 and 403 are authentication errors on every session, because the NATS layer is where a connection limit is normally expressed, and a refused websocket handshake has not been observed to be the limit's signature. If a live probe ever contradicts this, the classification to revisit is this one.

## What the subscription identifiers are for

Each SUB carries an identifier unique within the session, starting at one and counting up. NATS requires it so that an UNSUB can address one subscription, but nothing in this driver ever unsubscribes: the set of subjects is fixed for the connection's life, and a change of set is done by the shard building a new connection. The identifiers are still tracked and still sent, because the protocol requires them and because a future UNSUB costs nothing to add once they exist.

## Why there is no on_control

Fyers' connection hands non-data frames to an `on_control` callback because its control frames are structured and worth watching. Groww's non-data operations are single short lines — INFO, PING, PONG, +OK, -ERR — that carry nothing archivable, and the -ERR lines are acted on by raising rather than by being handed on. So there is no second callback; the accounting counters are the record.