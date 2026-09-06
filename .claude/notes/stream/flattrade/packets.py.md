# stream/flattrade/packets.py

## Why this module exists in this shape

Flattrade's feed is plain JSON in websocket text frames, one message per frame, unlike Zerodha's and Dhan's binary packets. That removes offsets and widths from the risk surface and introduces a different one: fields are named, so the failure mode is a wrong wire key reading as absent, not a wrong offset reading as plausible.

## The decoder and the assembler are separate on purpose

`decode_frame` stays stateless and returns a partial tick holding only the fields the wire sent, because `tk`/`dk` snapshots and `tf`/`df` updates share the same message shape and the updates carry only changes. `TickAssembler` is the stateful half: it keeps last seen values per (exchange, token), remembers each scrip's `pp` price precision from its acknowledgement, and emits the complete contract tick. The split keeps `decode_frame` testable on bytes alone and gives the future shard exactly one object to drive, the same role the decoders play for the other two brokers.

## Prices scale by the wire's own `pp`, not by a fixed hundred

Noren sends prices as decimal strings and each snapshot carries the scrip's price precision in `pp`. The decoder multiplies by ten to the power of that precision and stores the divisor per tick. A fixed divisor of 100, Dhan's choice, would misstate currency scrips, which quote to four decimals; this is the same class of trap as Zerodha's NSE commodity divisor. The `--against-rest` implied-scale check is the oracle that settles the precision segment by segment, exactly as it settled Zerodha's NCO divisor of 10,000 and Dhan's scale of 1. An absent `pp` defaults to precision 2, and the default is pinned by a synthetic check so a silent change cannot pass unnoticed.

## What was deliberately left out

- The touchline's top of book fields `bq1`/`bp1`/`sq1`/`sp1` are not mapped. The depth feed reports the same book with five levels, and one scrip carrying two different depth shapes would force every consumer to branch.
- The depth message's `cp` field is left undecoded. The docs list both `c` (previous close) and `cp` (close price) on the depth feed while the touchline has only `c`; the shared contract's close_price takes `c` on both feeds, which matches how Zerodha and Dhan store the previous close. The first live run should confirm what `cp` actually holds; the archive keeps the raw frames either way.
- `poi` and `toi` (previous day's open interest and the underlying's total open interest) are not mapped either; `oi` alone feeds the contract's open_interest. Same reason, same live-run question.

## Native identity keys are the wire's own names

The decoded tick carries `exchange` and `token`, the long forms of the wire's `e` and `tk`, mirroring how Zerodha kept `instrument_token`/`kite_segment` and Dhan kept `security_id`/`dhan_segment`. The token stays a string: BSE tokens and index keys are not plain integers in Noren, and coercing them would corrupt the mapping join.

## The `tk` collision hazard

`tk` is both a message type ("touchline acknowledgement") and the token field's wire key. The constants are named so the two never meet: `MESSAGE_TYPE_TOUCHLINE_ACK` versus `TOKEN_KEY`. `check_wire_message_type_strings` pins every one of these literals so the builders and the decoder cannot drift from the wire together — the exact failure Dhan's mutation testing recorded when builders and decoders share constants.

## `ltt` has no documented format

The depth feed's last trade time is documented only as "last trade time". `time_of_day_to_datetime` reads a number as epoch seconds and a colon-bearing string as a time of day on the day of arrival. The first live run should settle which form actually arrives; both paths are checked synthetically for the forms they accept.

## Counting packets for the archive manifest

One frame carries one JSON message, so `frame_packet_count` returns 1 for `tk`/`tf`/`dk`/`df` and 0 for everything else. Acknowledgements are not market data and would corrupt the manifest's reconciliation if counted. The counter parses the same bytes `decode_frame` parses, so the two can never disagree about what a frame claimed.

## Mutation testing

The synthetic checks were mutation-tested with one mistake planted at a time, each caught: counting `hk` as data, reading `bp` keys as `sp`, scaling prices by a fixed 100, initialising never-seen fields as zeros, replacing instead of merging on updates, and trimming the zero at depth level five. The zeros-instead-of-None and replace-instead-of-merge mutants initially survived until the merge check grew a never-seen-field scenario and a snapshot with a real `ft`; both were added and the mutants now die. Run with `PYTHONDONTWRITEBYTECODE=1` — a stale `.pyc` silently resurrects the unmutated code.