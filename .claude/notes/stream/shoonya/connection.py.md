# stream/shoonya/connection.py

## Why one connection class covers both feeds

Dhan needed a separate depth connection because its depth wire has a different binary shape and its own URL. Shoonya's touchline and depth are the same socket, the same JSON text frames, and messages that differ only in the subscribe type (`t` versus `d`), so a second class would be parameterised on nothing. The `mode` parameter follows the shape Dhan and Flattrade already established.

## Authentication happens in-band, so the refusal taxonomy shifts

The socket opens with no credentials at all; the client's first message must be the connect request, and the server answers with an `ak` acknowledgement. Shoonya's overview page says outright that `Not_Ok` means invalid credentials and to not proceed to subscribe. That moves the authentication signal off the handshake and onto the wire, which changes how refusals are classified:

- `Not_Ok` on the first session ever means the credentials are wrong, and raises `ShoonyaAuthenticationError` — retrying cannot help.
- `Not_Ok` on a later session, while earlier ones worked, means the credentials are fine and this connection was one too many. This is what Shoonya's documented one-connection-per-session limit should look like on the wire, so it raises `ShoonyaConnectionRefusedError("connect_not_ok")`.
- No acknowledgement within ten seconds raises `ShoonyaConnectionRefusedError("connect_ack_timeout")`, because an open socket that never answers the connect message is what "accepted but not served" means on this protocol.

The handshake status taxonomy (429/503 refusals, 401/403 authentication) is kept for parity with the other brokers even though Shoonya signals authentication on the socket; a live run that shows a handshake status doing real work should be written down here.

## The acknowledgement status is compared without regard to case

Shoonya's documentation spells the success value `"Ok"`; Flattrade's spells the same field `"OK"`, and Flattrade's module compares against that literal. Rather than pick one and hope, `connect_acknowledgement_is_ok` upper-cases before comparing.

The asymmetry is what decides it. Reading a good acknowledgement as a refusal raises `ShoonyaAuthenticationError`, which is deliberately non-retryable, so a casing mismatch would kill every connection on the first session and look exactly like a bad token. Reading a refusal as success is not a symmetric risk, because `Not_Ok` differs from `Ok` in far more than its case. The looser comparison cannot mistake a refusal for success in either spelling, and the strict one can mistake success for a refusal in one of them.

## The heartbeat is a guess corroborated by the platform, not by the documentation

Shoonya's overview says only "respond to server pings" and that the gateway drops idle connections. It documents no application heartbeat at all. Flattrade, running the same Noren platform, documents `{"t":"h"}` every thirty seconds as required, and Noren's own client sends it, so this module sends it too.

The websockets library's protocol pings (`ping_interval=20`) detect a half-open socket; the application heartbeat is what a Noren gateway wants to see. The heartbeat acknowledgement (`hk`) is counted in `heartbeats_received` but deliberately does not refresh `last_data_frame_at` — on an all-text protocol the heartbeat acknowledgement looks exactly like data to a naive counter, and it is heartbeats that a silently-unserved connection keeps sending. **Whether `hk` actually comes back is a live-run question; if it does not, the heartbeat is either unnecessary or spelled differently, and the answer belongs here.**

## The documented single-connection limit is not obeyed here

Shoonya's rate limits page says "1 connection per session" and to multiplex all symbols over it. Published websocket limits have been unreliable across every broker measured so far, and Shoonya's universe of 162,247 instruments makes the question expensive to get wrong in either direction. So this module caps nothing and the capacity probe measures it, treating the documented number as the hypothesis rather than the constraint. If the probe confirms a hard limit of one, that is a finding worth recording — but it is a finding, not an assumption.

## Resubscription is mandatory on every session

Shoonya's own page states that the gateway does not persist subscriptions across a dropped connection and that every subscription must be re-sent after every reconnect. `_send_subscription` therefore runs on every session, batching instruments one hundred per message. Without it a reconnected socket sits open and permanently silent, which is the Zerodha failure mode word for word.

## Batch size one hundred is a choice, not a rule

Shoonya documents no limit on the `k` field, only that the number of `tk` acknowledgements equals the number of scrips in it. That equality is what the first live run counts to validate the batch size, and widening it afterwards is a one-constant change.

## Every frame goes to the archive, not only market data

`on_frame` receives every frame encoded to UTF-8, whatever it carries, because the archive is the system of record for what came off the socket and `frame_packet_count` already reports zero for the non-data frames, so the manifest's reconciliation is unaffected. Frames that are not market data also go to `on_text`, which is how order updates reach a caller without touching the market data path. The one asymmetry: frames read during the authentication wait are accounted but not handed to `on_frame`, since nothing market-shaped can arrive before the subscription is sent.

## Probe mode must not swallow a failed first session

`maximum_reconnect_attempts == 0` means probe mode, and there the first session's ordinary failure — ConnectionClosed, OSError or TimeoutError — is raised wrapped as `ShoonyaConnectionError` rather than returning silently. This is the fix Flattrade's weekend smoke test forced: a probe that returns nothing on failure is indistinguishable from one that returned nothing because the market was closed. The ordinary-retry path is unchanged; only the no-retry path behaves this way, because there a silent return has no honest meaning.
