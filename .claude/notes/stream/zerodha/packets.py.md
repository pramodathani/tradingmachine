# stream/zerodha/packets.py

Decodes Zerodha's binary websocket frames into dictionaries. This is the single most correctness-critical module in the streaming subsystem, and it is deliberately the one with the fewest dependencies: it imports `struct` and `datetime` and nothing else, knows nothing about instruments, shards, Redis or the database, and can therefore be tested completely on bytes alone.

## Why a parser rather than pykiteconnect

Zerodha publishes `pykiteconnect`, which already contains a working version of this code. It was not used, for reasons that are about the process model rather than the parsing. That library is built on Twisted and Autobahn and runs on a Twisted reactor, of which there is exactly one per process, so several connections in one process share a single callback thread and a slow handler stalls parsing for all of them. The design here puts each connection in its own process anyway, which removes the only thing the library was buying, while leaving its Twisted dependency and its allocation of a dictionary per tick with fields the database does not want.

Its source was read closely, though, and it is the authority behind two decisions below where Zerodha's written documentation is wrong.

## Prices are not converted here

Every price is left exactly as it arrived, and `price_divisor` reports what to divide by. This looks like an omission and is not.

The same decoded dictionary is consumed by two things that want different forms. The database stores raw integers with the divisor in a column, because integers are exact, half the width of a double, and compress far better. The Redis publisher wants rupees, because a consumer should not have to think about divisors. Converting here would mean the writer had to multiply back, and multiplying a float back to an integer is exactly where a price silently gains or loses a paisa. Leaving the wire value untouched means the value written to the database is provably the value that arrived.

## The two currency divisors come from the client libraries, not the documentation

Zerodha's written documentation says that for currencies the price should be divided by 10000000 to obtain four decimal places, which is arithmetically impossible, and it never mentions BSE currency at all. Both the Python and the Go client libraries instead divide NSE currency by 10000000 and BSE currency by 10000, and they agree exactly with each other. This module follows the libraries.

This matters more than the small number of affected instruments suggests. There were 7808 NSE currency instruments in the September 2026 mapping, and getting the divisor wrong there does not produce an obviously broken number: USDINR at 86.12 would read as 8612345 or as 0.0000086, neither of which is visible unless somebody specifically looks at a currency instrument. The synthetic checks therefore test both currency segments explicitly.

## NSE Commodity divides by ten thousand, and this was nearly got wrong

Segment 12 is NSE Commodity. It is not in either client library's segment table, both of which stop at 9, it is absent from the written documentation, and it covered 24913 of the 108981 instruments Zerodha listed on 2026-09-04, which is close to a quarter of them.

Its divisor is ten thousand. This was originally implemented as a hundred, reasoning from the tick sizes in the instrument file, which run from one paisa upwards and look exactly like an ordinary rupee-and-paise segment. That reasoning was wrong and the error was out by a factor of a hundred: NCO crude oil futures arrived on the wire as 85730000 and Zerodha's own quote endpoint priced the same contract at 8573.

Nothing about the instrument file would have revealed this. It was found by comparing decoded ticks against the REST quote endpoint, where fourteen NCO instruments implied a divisor of exactly ten thousand and nothing else. The general lesson is worth keeping: a divisor cannot be inferred from tick size, and the only reliable way to establish one for a new segment is to ask the broker what the same instrument is worth and divide.

Note that MCX commodity, segment 7, does divide by a hundred. The two commodity segments scale differently, so neither one can be used to guess the other.

## Unknown segments divide by a hundred rather than failing

An unrecognised segment is named by number and divided by a hundred, never rejected. Zerodha adds segments faster than it updates its client libraries, and a parser that raised on an unfamiliar segment would take down a connection carrying thousands of instruments the first time a new one appeared.

The NCO experience shows the limit of that default, though. Falling back to a hundred keeps the data flowing and keeps the raw wire integer in the archive, which is recoverable, but the prices it produces will be silently wrong if the new segment happens to scale differently. So the fallback is a way to avoid losing data, not a way to be correct, and any newly appearing segment should be checked against the quote endpoint before its prices are trusted.

## Index and tradeable packets share no code, on purpose

After the last traded price, an index packet carries high, low, open, close. A tradeable packet carries open, high, low, close. Nothing in the bytes distinguishes the two orderings, and both are four consecutive unsigned integers, so decoding an index with the tradeable reader produces four perfectly plausible prices with the open and the high swapped and the low and the close swapped.

`decode_index_packet` and `decode_tradable_packet` therefore duplicate their unpacking rather than sharing a helper that takes an ordering. This is the project's general preference for duplication over parameterisation, but here it is also a safety property: there is no single place where a wrong argument could silently swap the two, and each function reads top to bottom as a statement of what its own packet shape is.

The field at offset 24 of an index packet is the exchange's own price change. It is ignored, exactly as both client libraries ignore it, because it is read as an unsigned integer and a falling index would therefore report a number near four billion.

## The depth order count is two bytes

Each depth entry is a four byte quantity, a four byte price, a two byte order count, and two bytes of padding. Reading the order count as four bytes shifts every subsequent entry by two bytes, and because the shifted values are still integers in a plausible range, the result is five bid levels with wrong prices that look like real prices.

`pykiteconnect`'s own docstring contains a sample tick showing order counts like 1048576, which is stale output from a version that made exactly this mistake. Its current code reads two bytes. If order counts ever come out in the millions, this is why.

## Everything is unsigned

All four byte fields are read with `>I`, matching both client libraries. This is why every wire column in the database is `BIGINT` rather than `INTEGER`: an unsigned four byte value can exceed what a signed four byte column holds, and because the writer loads rows in batches of twenty thousand with `COPY`, one such value would reject the whole batch rather than one row.

## Timestamps outside a plausible range become None

The exchange sends zero when it has nothing to report and occasionally sends a value that is not a time. Since the ticks table is partitioned by time, storing a wrong timestamp would place rows in the wrong chunk and distort that chunk's time range. Anything at or below zero, or at or beyond the year 2100, becomes `None`.

Note that the column guarded here is not the partitioning column. `arrival_time` is recorded by the shard from its own clock and is always sound; these are the exchange's own timestamps, which are stored but not partitioned on, precisely because they cannot be trusted.

## Malformed frames stop the loop rather than raising

`decode_frame` returns an empty list for anything shorter than two bytes, which is how the one byte heartbeat is handled. Within the loop, both the length prefix and the packet body are bounds checked against the frame, and a frame that ends mid packet returns the packets read so far.

This runs inside the socket read loop. An exception escaping it would drop a websocket connection carrying several thousand instruments because of one malformed frame, so the loop is written to salvage what it can and continue. The packet count in the header is likewise treated as a claim rather than a fact, since a corrupted count would otherwise drive the loop past the end of the buffer.
