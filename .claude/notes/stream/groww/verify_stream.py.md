# stream/groww/verify_stream.py

The verification harness, in two modes like every other broker's copy: `--synthetic` runs offline on bytes alone and is the gate for decoder and framing; `--against-rest` compares live ticks against Groww's own REST quote endpoint during market hours.

## How the synthetic checks are aimed

Each check targets one specific way this decoder could be wrong, rather than exercising a happy path:

- The field tables are pinned literally, because every other check reads them out of the decoder — if a table were reordered, all the other checks would move with it and none would notice.
- All sixteen price fields use deliberately distinct values, so a swap of any two shows up instead of being masked by equal values.
- The index check exists because `StocksLiveIndicesProto` puts its value in field 2, which in a price message is the day's open. Reading an index through the price reader would put the NIFTY level in `open_price` and leave `last_price` empty, and nothing about the result would look wrong. This is Groww's equivalent of Zerodha's index field order check.
- The framing checks exist because the websocket carries a NATS byte stream: several messages coalesced in one frame, one message split at every possible cut point, control operations interleaved with data, and a payload containing the `\r\n` that would fool a line-splitting reader. The split check cuts at every byte position, not at a convenient one.
- The reader's refusal to accept an unreadable MSG header is a check, not just behaviour: once the stream desynchronises every later byte is garbage, so raising is the correct response and the check pins that it happens rather than a silent hang.

## Where the golden frames come from and how to regenerate them

The six hex payloads were encoded by Groww's own generated `stocks_socket_response_pb2` module, unpacked from the growwapi 1.5.0 wheel into a scratch directory, and pasted in as literals. The generator script lives in the session scratchpad as `generate_golden_frames.py`; run it there with the project's virtual environment and diff the printed hex against this file before trusting a schema change.

They must never be regenerated with this project's own encoder — the whole point is that the hand-written reader is pinned against the official one, and an encoder we wrote would agree with our decoder about any shared mistake.

The equity payload was built with all sixteen fields set, including `openInterest = 0.0` — and that field is absent from the wire, because proto3 drops defaults. That absence is itself part of what the golden check pins: the equity tick's `open_interest` must come back as None, and the derivative payload, which sets it to a real number, comes back with the number.

## The REST oracle

`--against-rest` captures live ticks over a window, then asks `GET https://api.groww.in/v1/live-data/quote` about the same instruments and compares. The endpoint's shape — `last_price`, an `ohlc` object, `average_price`, `volume` — is Groww's documented live-data response, not the websocket's field names, so the comparison goes through a dotted-path reader rather than assuming the two agree on names.

Two details matter more than they look:

- The access token comes from the same `last_login` document the connection's credentials came from, so a run needs both a login from today and market hours. On a weekend both the socket and the REST endpoint may be dark.
- The implied scale measurement divides each tick's price, after its own divisor, by the REST `last_price`. For a correct decoder the median is 1.0, because Groww's wire is floating-point rupees and the divisor only exists for storage. A wrong divisor shows up as a clean factor, which is the same trick Fyers' harness uses to settle its multiplier-versus-precision question.

Pacing is one request per second, far below the documented limit of ten per second and three hundred per minute.

## What the oracle can and cannot catch

The oracle catches a wrong field number that the synthetic checks happened to agree with, because REST prices are produced by an independent codepath. It cannot catch fields REST does not publish — the trade range fields and open interest beyond FNO are compared only if present — and it cannot validate the index subjects, because indices are not in Groww's tradable instrument CSV and so are not selected. Index decoding is covered synthetically and, later, by eyeballing a live index session against a public index level.