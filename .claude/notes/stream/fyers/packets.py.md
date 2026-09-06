# stream/fyers/packets.py

## Where this wire format came from

Fyers documents no wire format. Its published API reference describes the `fyers_apiv3` client library and the shape of the data after that library has decoded it, and the only two websocket URLs anywhere in it are the order socket and the tick-by-tick socket. The quote feed's endpoint, its framing, its packet kinds and its field order appear nowhere.

Everything in this module was therefore established by reading the client library's source, which is a public package fetched and read but deliberately not imported. Every other broker here hand-rolls its protocol on `websockets` alone, and adding one broker's client library as a runtime dependency would make Fyers the odd one out in three ways that matter: its threading model fights the asyncio connection driver, its reconnection logic would sit outside the driver every other broker routes through, and it hands back decoded dictionaries, which would break the archive's guarantee that what is stored is what came off the socket.

Constants, field orders and the segment table were transcribed as evidence about the broker. The library's control flow was not treated as a design to copy.

## The one thing that shapes the whole module: updates do not name their topic

A snapshot packet, kind 83, carries a topic identifier *and* the topic name, so it is self-describing. An update packet, kind 85, carries the identifier only. The number 41 in an update means an instrument solely because an earlier snapshot on the same connection said that topic 41 is `sf|nse_cm|2885`.

Two consequences follow, and both are deliberate.

`decode_frame` stays a pure function of bytes, matching the signature every other broker's decoder has, and returns partial ticks carrying the raw identifier and, for updates, an unnamed positional list of values. It does not try to name them. All the state lives in `TickAssembler`, which is the only thing that holds the topic table, so the decoder remains testable on bytes alone.

The topic table belongs to one connection and must not outlive it. Fyers numbers topics per connection, so after a reconnection the same number means a different instrument. An assembler carried across a reconnection would silently attribute one instrument's prices to another, which is the worst failure this module could have because nothing about the output would look wrong. `FyersConnection` builds a fresh assembler per session for exactly this reason.

It also means an archived update frame is not self-describing on its own. The archive is still the system of record, but a replay has to read a shard's files in order from the start of the session so the snapshots that introduce the topics are seen first. The manifest's per-file arrival ranges still make a windowed backfill cheap; the window just has to begin at a session boundary.

## An update for an unknown topic is dropped, not guessed

`TickAssembler.merge` returns None when an update arrives for a topic no snapshot has introduced. That is a race rather than an error: a subscription's first update can overtake its snapshot. Dropping it loses one revision of a field the next update will carry again. Guessing at the instrument would attribute a price to the wrong one, which is unrecoverable and invisible.

## The topic identifier's byte order does not matter, and cannot be known

The client library reads the topic identifier with native byte order while reading every other integer in the protocol big endian. That looks like a bug, and it may be one, but it cannot be observed: the identifier is only ever a dictionary key, and a consistently wrong byte order is a perfectly good key. Nothing in the protocol compares an identifier against a number from anywhere else.

This module reads it little endian, matching the library's effective behaviour, and the only requirement is that snapshots and updates be read the same way. If Fyers ever sends an identifier the project has to correlate with something external, this is the line to revisit.

## Fields are positional, so the lists are the entire naming

A packet says how many values follow and nothing else. The values are read against `SCRIP_FIELD_NAMES`, `INDEX_FIELD_NAMES` or `DEPTH_FIELD_NAMES` depending on the topic's prefix, so those lists *are* the field naming. Reordering one silently mislabels every field it moves, and the mislabelling is plausible rather than obvious: swapping the day's open and its high produces two numbers that both look like prices.

The index list is not a shortened scrip list. An index carries last price, previous close, feed time, high, low and open, in that order, where a scrip carries last price and volume first. Reading an index with the scrip list produces prices in the wrong fields, which is the same trap the Zerodha decoder documents for its own index packets and the reason the two are kept apart there too.

`-2147483648` means the wire sent nothing for the field. It is not a price and it is not a sentinel that can be arithmetic on. `read_field_values` turns it into None, and `apply_scalar_values` then leaves the field off the partial tick entirely, so the assembler can tell "this packet did not mention the field" from "this packet said the field is nothing".

## Top of book from the quote feed is kept, under names that cannot collide

The quote feed carries a single level of book alongside the day's prices. The Flattrade decoder deliberately drops its equivalent, on the grounds that the depth feed reports the same book with five levels and one instrument must not carry two different shapes.

The concern is right but dropping the data is not the only way to answer it. These four values are kept under `touchline_bid_price`, `touchline_bid_quantity`, `touchline_ask_price` and `touchline_ask_quantity`, which are separate contract fields that are never merged into the five-level arrays. A quote-feed subscriber gets top of book without paying for the depth feed, and no instrument ever has an array of an unexpected length.

## The price divisor is the open question this module leaves

A snapshot carries both a `multiplier` and a `price_precision`, and Fyers documents neither. `price_divisor` returns ten to the power of the precision, following the Flattrade decoder, because that form handles a currency scrip quoted in fractions of a paisa where a fixed hundred would misstate it.

That is the decoder's best reading, not an established fact. The multiplier is carried on every tick beside the divisor rather than being discarded, so `verify_stream --against-rest` can measure the implied scale per exchange and settle which of the two is really the divisor. This is exactly how Zerodha's, Dhan's and Flattrade's scales were settled, including the case where Zerodha's own written documentation turned out to be wrong.

## The subscription key is built offline, which is the reason this scales

The client library builds its subscription key by posting every symbol to `POST https://api-t1.fyers.in/data/symbol-token` and reading the token back. The endpoint returns the token the instrument master already holds, so the round trip buys nothing.

`hsm_symbol_for_instrument` builds the key directly: the segment from the token's first four digits and the exchange token from the instrument master's `scrip_code`. Both halves were checked against a full day's file — all 158,943 rows have a known segment prefix, and `scrip_code` equalled the token's remainder in every one of them, with zero exceptions. All 158,943 quote keys build offline.

The saving is not cosmetic. Fyers allows ten requests a second and blocks the account for the rest of the day after three breaches of the per-minute limit. Resolving the universe over REST every morning would take hours and put the account a few retries away from being locked out for the day.

## Indices are keyed by name, and nine of them are a guess

An index is not subscribed by a numeric token but by the name the exchange publishes it under, and that name is nowhere in the Fyers instrument master. `INDEX_NAMES_BY_TICKER` is transcribed from the table the client library ships and covers 173 of the 182 index rows in a day's file.

For the other nine, `index_name_for_ticker` falls back to the ticker's own symbol, so `NSE:NIFTYCHEMICALS-INDEX` becomes `NIFTYCHEMICALS`. That is what the library does and it is known to be a guess. Whether the exchange agrees can only be settled on a live run; a wrong name produces a subscription that is accepted and then silently never ticks, which is why `verify_stream` checks delivery per instrument rather than only that data arrived.

Depth on an index returns no key at all, because Fyers does not serve one, and the library's own error message says so.

## Failing softly is not laziness here

An unrecognised packet kind ends the frame rather than being skipped, because an unknown kind has an unknown length and nothing after it can be located. A frame that ends mid-packet returns the packets read so far. A malformed topic name yields a partial tick that the assembler refuses.

None of these raise, for the same reason the Zerodha and Flattrade decoders do not: this runs inside the socket read loop, and one malformed frame taking down a connection carrying thousands of instruments would be a far worse outcome than losing that frame.
