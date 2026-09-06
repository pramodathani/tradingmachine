# stream/groww/capacity_probe.py

Measures Groww's real feed limits — subscriptions per connection and simultaneous connections — and stores them in MongoDB the way every other broker's probe does. The structure follows `stream/fyers/capacity_probe.py`, but the success signal is different, and that difference shapes the whole file.

## Why the probe pings instead of counting snapshots

Fyers sends a snapshot for every instrument the moment a subscription is accepted, so the Fyers probe counts what arrives and can tell an honoured subscription from an ignored one without any trading. NATS keeps no retained values: a subscription delivers nothing until the instrument next trades, so outside market hours a fully honoured subscription and a silently truncated one are indistinguishable by data.

The probe's success signal is therefore protocol level. A batch of SUB operations is sent, then a PING, and the connection waits for PONG. NATS processes operations in order, so the PONG proves the server took every SUB before it; a breach arrives as -ERR ahead of it. This works outside market hours, which is when a probe is safe to run.

## The stated gap

If Groww enforces its limit by quietly ignoring subscriptions beyond it instead of answering -ERR, this probe cannot see that from the protocol and would report success at any size. The evidence stored with the numbers records exactly what was observed so the record can settle later arguments. This is the same honesty rule as the connection note: state what the measurement cannot see rather than let the number imply more certainty than it has.

## Why ProbeConnection is a second connection implementation

The production driver in `stream/groww/connection.py` could not be reused for this. It subscribes and returns to reading, because in normal operation acceptance is proven by the data that follows, and it has no way to send a confirming PING after subscribing. The probe needs the handshake plus subscribe plus confirming PING, then a loop that stays open answering the bus's pings. Keeping that in the probe file, self-contained and separately readable, follows the project's duplication-over-abstraction rule; the handshake and -ERR classification are duplicated deliberately, and the probe's copy does not have to carry reconnection state.

## How the connection-count probe holds connections open

Each accepted connection keeps running until `stop_event` is set — `run()`'s read loop answers the bus's PINGs for the whole life of the connection, so an accepted connection can simply be left alone while the next one is attempted. Before each new attempt the probe checks `connected` on every earlier connection, so a bus that drops an older connection when a new one arrives is caught as `earlier_connection_dropped` rather than silently overstating capacity.

Each held connection also subscribes a small basket of subjects rather than nothing, because a bus might tolerate empty connections it would not tolerate busy ones.

## The dead-after-acceptance case

If the bus closes a connection right after the confirming PONG, `run_probe_session` returns a `None` task even though `accepted` is true. The connection-count probe treats that as a refusal (`connection_closed_after_acceptance`) rather than counting a dead connection towards capacity. This was found by testing the probe against a local fake NATS bus before any live run.

## Testing against a fake bus

The probe's session logic was exercised offline against a small `websockets` server that impersonates the NATS layer: INFO with a nonce, PONG on request, SUB accounting, and a configurable -ERR. Four cases pass: clean acceptance, refusal by -ERR, refusal by closing after acceptance, and holding open with pings answered. One lesson from building the fake: a real NATS server terminates every operation, including INFO, with `\r\n`, and `ProtocolReader` correctly refuses to yield a line until it sees the terminator — an INFO without the terminator simply hangs the handshake, which is the correct response to a truncated stream.