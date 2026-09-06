# stream/fyers/verify_stream.py

## The two feeds fail in opposite ways, so they are checked in opposite ways

The quote feed is positional. Its entire risk is a wrong field order, which produces plausible numbers in the wrong places: swapping the day's open with its close gives two values that both look exactly like prices. It is also stateful in a way no other broker's feed in this project is, because an update packet identifies its instrument by a number that only an earlier snapshot gave meaning to.

The depth feed is Protocol Buffers. Its structure is self-describing and cannot be misaligned, so field order is a non-issue, but the reader is hand-written and can disagree with the published schema.

So the checks are split accordingly: the quote feed's checks are about ordering and about state, and the depth feed's checks are about agreeing with the official encoder.

## `check_field_lists_are_pinned_literally` is the most important check here

It was added because the checks were mutation-tested and one mutation walked straight through them.

Reordering `SCRIP_FIELD_NAMES` so that `open_price` and `close_price` swapped places broke nothing: all twenty-five checks still passed. The reason is that `check_snapshot_round_trips_every_field` iterates the decoder's own field list and compares position by position, so when the list moves, the check moves with it. It is self-consistent and structurally incapable of noticing a reorder. Every other check that touches field names has the same blind spot.

`check_field_lists_are_pinned_literally` writes all three lists out in full inside the check, along with the segment table and the packet kind constants, so it is the one place that does not read its expectations from the thing it is testing. After adding it, the same reorder fails immediately, as do reorders of the index and depth lists and a changed packet kind byte.

The comment in the check saying the names must not be edited to match a modified decoder is the whole point of it. A failure here means the decoder is wrong, not that the check is out of date, unless the wire has actually been shown to change.

## What the mutation testing established

Seven deliberate faults were introduced and the checks were run against each:

| Fault | Caught |
|---|---|
| `open_price` and `close_price` swapped in the scrip list | yes, after the pinning check was added |
| `last_price` and `close_price` swapped in the index list | yes |
| bid and ask price groups swapped in the depth list | yes |
| the update packet kind changed from 85 to 84 | yes |
| the two's complement conversion for negative protobuf prices removed | yes |
| depth levels reporting zero trimmed out of the arrays | yes |
| the absent-value sentinel read as a real number | yes |

Three of these were caught before the pinning check existed and four only after it, which is the argument for keeping it.

## The golden protobuf frames

`SNAPSHOT_FRAME`, `DIFFERENCE_FRAME`, `ERROR_FRAME` and `NEGATIVE_PRICE_FRAME` are real bytes produced by Fyers' own generated protobuf code from their published schema, stored as hex.

This is what lets the depth decoder be hand-written without that being a leap of faith. The alternative was committing a generated module and depending on the protobuf runtime; storing the encoder's output instead gets the same guarantee with no dependency and no build step. Regenerating them requires the client library and is a deliberate act, which is correct: they are evidence about the wire, not fixtures that should move whenever the code does.

`NEGATIVE_PRICE_FRAME` earns its place specifically. A negative `int64` encodes as ten bytes of two's complement, and reading it without conversion yields roughly eighteen quintillion, so the frame also carries a wrapper that is present but empty, to pin that a real zero stays a zero while an absent field stays absent.

## Why the oracle's own comparison is checked synthetically

`check_compare_tick_to_quote` and `check_implied_scale_ratio` test the functions the live mode uses, on values whose right answer is known. The oracle is only as trustworthy as its comparison, and a comparison bug would show up as either a false alarm on a market day or, far worse, as silent agreement.

`check_implied_scale_ratio` matters most, because the implied-scale measurement is what settles the one question this package deliberately leaves open: whether the snapshot's `multiplier` or its `precision` is the real price divisor. The check feeds it prices whose divisor is ten thousand while the tick claims a hundred, and asserts it measures ten thousand — that is, that it reports what the wire implies rather than what the decoder assumed. If that function were wrong, the live run would confirm the decoder's guess no matter what the guess was.

## Choosing instruments by spread rather than by count

`select_verification_instruments` takes a few instruments from every segment rather than many from one. The price divisor is a per-instrument property here, carried in each snapshot, so a hundred NSE equities would settle NSE equities and say nothing about currency or commodity, where the scales are most likely to differ. This is the same reasoning the Zerodha checks used, and Zerodha's commodity segment is exactly where its documented divisor turned out to be wrong.

## The oracle paces itself on purpose

The REST quote endpoint takes fifty symbols per call against ten calls a second and two hundred a minute, and Fyers blocks the account for the rest of the day after three breaches of the per-minute limit. `fetch_quotes` sleeps a second between calls, which is far below the limit and is meant to be: being verifiably slow is worth more than being fast when the penalty for a mistake is losing the account for a day.

## Instruments that never tick are reported by name

`run_against_rest` prints the instruments that no tick arrived for, rather than only counting them. On this broker that list is diagnostic rather than noise: an index whose name was guessed wrong, and there are nine of those, produces a subscription that is accepted and then silently never ticks. There is no error and no refusal, so the only evidence is the instrument's absence from the capture.
