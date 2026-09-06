# stream/shoonya/packets.py

## Why this module exists in this shape

Shoonya's feed is plain JSON in websocket text frames, one message per frame, the same as Flattrade's and unlike Zerodha's and Dhan's binary packets. Both are Noren, so the wire keys and message types are the same vocabulary. The two modules are still kept separate rather than shared, for the reason the instrument masters are kept separate: each file should be readable on its own, and the differences below are already real.

## The decoder and the assembler are separate on purpose

`decode_frame` stays stateless and returns a partial tick holding only the fields the wire sent, because `tk`/`dk` snapshots and `tf`/`df` updates share the same message shape and the updates carry only changes. Shoonya's own documentation is unusually explicit about this — it says in a callout that the feed is a diff stream after the initial `tk` and that no single later message is a complete quote — so the split is not an inference here, it is the documented contract. `TickAssembler` is the stateful half: it keeps last seen values per (exchange, token), remembers each scrip's `pp` price precision from its acknowledgement, and emits the complete contract tick.

## Prices scale by the wire's own `pp`, not by a fixed hundred

Shoonya documents `pp` as 2 for NSE and BSE and 4 for CDS USDINR, which is the clearest statement any of the four brokers makes that a fixed divisor is wrong. The decoder multiplies by ten to the power of that precision and stores the divisor per tick. An absent `pp` defaults to precision 2, and the default is pinned by a synthetic check so a silent change cannot pass unnoticed. The `--against-rest` implied-scale check is the oracle that settles the precision segment by segment, and Shoonya is the first broker whose run reaches NCX.

## The order update type is `om`, and there is no position type

Flattrade's module knows `o` for order updates and `p` for position updates. Shoonya's order update feed page states that order updates arrive automatically on connect with `t: "om"`, that no subscribe frame exists for them, and that positions are a REST endpoint rather than a feed. So this module's constant differs from Flattrade's and carries no position type at all. It matters only for classifying non-market-data frames, but a wrong constant there would put order updates in the wrong counter.

## Depth is entirely undocumented on Shoonya

Shoonya publishes a touchline page and an order update page and no depth page at all. Every key `decode_depth_message` reads — `tbq`, `tsq`, `ltq`, `ltt`, and the five `bp`/`bq`/`bo` and `sp`/`sq`/`so` levels — is the Noren key that Flattrade documents, carried across on the strength of the two brokers running the same platform. The order update page corroborates that depth exists by referring to it in passing ("unlike touchline or depth"), but nothing states its shape.

This is the module's largest open question. The first live `d` subscription either produces `dk` frames that decode cleanly, or it does not, and if it does not the touchline's own `bq1`/`bp1`/`sq1`/`sp1` become the book instead.

## What was deliberately left out

- The touchline's top of book fields `bq1`/`bp1`/`sq1`/`sp1` are not mapped, on the same reasoning as Flattrade: the depth feed reports the same book with five levels, and one scrip carrying two different depth shapes would force every consumer to branch. **This decision is contingent on depth working.**
- `pc`, the percentage change, is documented on Shoonya's touchline and has no place in the shared contract, which stores the previous close and lets a consumer compute it.
- `ts`, `ti` and `ls` — trading symbol, tick size and lot size — are instrument reference data already held in `instruments.shoonya` and refreshed daily. Taking them off the tick feed would create a second, staler copy.
- `poi` and `toi`, the previous day's open interest and the underlying's total open interest, are not mapped; `oi` alone feeds the contract's open_interest.

## Native identity keys are the wire's own names

The decoded tick carries `exchange` and `token`, the long forms of the wire's `e` and `tk`. The token stays a string: Shoonya's `k` field examples include `NSE|NIFTY`, an index key that is not a number at all, so coercing tokens to integers would fail outright on indices and corrupt the mapping join elsewhere.

## The `tk` collision hazard

`tk` is both a message type ("touchline acknowledgement") and the token field's wire key. The constants are named so the two never meet: `MESSAGE_TYPE_TOUCHLINE_ACK` versus `TOKEN_KEY`. `check_wire_message_type_strings` in the verification module pins every one of these literals so the builders and the decoder cannot drift from the wire together.

## Counting packets for the archive manifest

One frame carries one JSON message, so `frame_packet_count` returns 1 for `tk`/`tf`/`dk`/`df` and 0 for everything else. Acknowledgements are not market data and would corrupt the manifest's reconciliation if counted. The counter parses the same bytes `decode_frame` parses, so the two can never disagree about what a frame claimed.
