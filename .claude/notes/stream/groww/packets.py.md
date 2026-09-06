# stream/groww/packets.py

Decodes one archived NATS message operation into a tick. No network, no MongoDB, testable on bytes alone, like every other broker's decoder.

## Why the archived record is a whole NATS message, not a websocket frame

Every other broker's archive stores the websocket frame it received, because for those brokers a frame is self-contained: it carries its instrument, or the decoder knows from the connection's own state which instrument it belongs to.

Groww's transport is NATS carried over a websocket, and NATS is a byte stream, not a frame protocol. One websocket frame may hold half a NATS message, three of them, or the tail of one and the head of the next. Archiving raw websocket frames would leave the archive full of records that cannot be decoded on their own.

So the connection driver (not this module) reassembles the stream into complete NATS message operations and archives each one whole: the `MSG <subject> <sid> <count>` header line, the payload, and the trailing `\r\n` that followed it, exactly as NATS sent them. The archived record is then self-contained in the way the other brokers' frames are, and `decode_frame` on a replayed record produces the identical tick it produced live.

The header line travels with the payload on purpose. The subject is the only place the instrument's exchange token appears — see below — so a payload archived without its header would be an unusable record.

## Why the subject carries the instrument's identity

The protobuf response carries `symbol`, `segment` and `exchange`, but not the exchange token. The exchange token is what `data/instruments/groww.py` produces and what the mapping tables and tick table key on, and it exists nowhere except in the subject the message was published on: `/ld/eq/nse/price_detailed.2885`.

This is why `decode_frame` parses the header itself rather than taking the payload alone. It is also why the driver must never batch two instruments' payloads under one archived record — the subject/payload pairing is the identity.

## The schema is all doubles, and what that costs

Every scalar in `StocksLivePriceProto` and `StocksLiveIndicesProto` is a `double` on the wire, including volume, bid quantity, offer quantity, open interest and the millisecond timestamp. This was read out of the descriptor embedded in `growwapi`'s generated `stocks_socket_response_pb2`, not inferred from samples.

Consequences: `read_double` exists here and not in Fyers' copy (Fyers' schema uses only varints and length-delimited fields), and quantities are rounded while prices are scaled — a count has no divisor.

## Absent is not zero, and zero is not absent

proto3 without wrapper types does not transmit a field set to its default. An absent `ltp` and an `ltp` of 0.0 are the same bytes, and Groww sends only the fields that changed, so partial messages are normal, not exceptional.

This module reports an absent field as `None`, which is what the tick table's nullable columns mean. The unavoidable cost: a broker sending a genuine zero — for example an offer quantity of zero when there is no seller — also reads as `None`. There is no way to distinguish them from this end, and inventing a default would misstate more rows than it fixes.

The same rule applies at the outer level, and it is visible in the golden equity payload: `segment` decodes to `None` rather than `CASH` because `CASH` is enum value 0 and proto3 dropped it. An equity tick's segment being `None` while a derivative's says `FNO` is correct behaviour, not a decoding gap.

## Why index and price are separate functions

`StocksLiveIndicesProto` is not a short price message. It puts its value in field 2, which in `StocksLivePriceProto` is the day's opening price. Decoding an index through the price reader would report the NIFTY level as an opening price of 25432.85 with no last price at all.

So the two arms are decoded by `decode_live_price` and `decode_live_indices`, with disjoint field-name tables, and `decode_frame` picks between them by the response's oneof field number — 4 for price, 6 for indices — never by length or by content sniffing. The synthetic check `index_decodes_through_field_six` pins this.

## Why the price divisor is 10000 and not 100

Groww is the first broker here that sends floating-point rupees instead of integer paise. The tick table stores raw integers with a per-row `price_divisor`, so the value has to be multiplied by something and rounded.

A hundred would preserve paise and lose the four decimals a currency instrument quotes in (USDINR settles to four places: 88.4275). Ten thousand keeps those. It is comfortably inside `BIGINT` — even the traded value of a full day on RELIANCE stays well within it — and `price_divisor` travels on the row, so `ticks_priced` divides it back without knowing which broker produced it.

## Why the decoder never raises

`decode_frame` is called from the socket read loop and from archive replay. One malformed record — a truncated payload, an unknown subject family, a header line that is not a `MSG` — must not take down a connection or break a replay, so every failure path returns an empty list.

Unknown field numbers and unknown wire types inside the payload are skipped by wire type rather than rejected, so a schema addition on Groww's side degrades to missing data rather than to an exception.

## Where the golden payloads came from

The six hex payloads in `verify_stream.py` were encoded by Groww's own generated `stocks_socket_response_pb2` module, in a scratchpad environment with `growwapi` unpacked, and pasted in as literals. The hand-written reader is thereby pinned against the official encoder without the SDK becoming a dependency. Regenerate them and diff the hex if the schema is ever in doubt.

The depth payload is included in the goldens as a negative case: the response's depth arm (field 5) is deliberately out of scope for this branch and must decode to zero ticks, not to a misshapen price tick.