# stream/dhan/packets.py

Decodes Dhan's binary live market feed frames into dictionaries. It imports `struct` and `datetime` and nothing else, knows nothing about instruments, shards, Redis or the database, and is tested completely on bytes alone, mirroring its Zerodha counterpart.

## Prices are converted here, unlike in the Zerodha decoder

Zerodha's wire values are already integers, so its decoder leaves every price untouched and reports a divisor. Dhan's wire prices are IEEE floats, which a BIGINT column cannot hold, so the conversion has to happen somewhere and this is the one place in the pipeline where anything is interpreted: each price becomes `round(price * 100)` paise, and every tick reports `price_divisor = 100`.

The divisor of one hundred was chosen to match what every non-currency Zerodha segment uses, so Dhan and Zerodha rows are indistinguishable in `market_data.ticks_priced` and the future Redis publisher needs no broker branch. Dhan's written documentation publishes no per-segment divisor table at all, so the scale of the wire itself, whether prices arrive in rupees or in some scaled unit, is not settled by documentation; it is settled by the implied-scale check in `verify_stream --against-rest`, exactly as Zerodha's NSE Commodity divisor was. If any segment turns out to scale differently, the fix is a per-segment branch in `price_in_paise`, not in `price_divisor`.

## Float32 limits, and what they mean for high priced instruments

A float32 carries roughly seven significant decimal digits, which is exact integer paise up to 2 to the 24th paise, about Rs 167,772.16. Above that, the wire itself can no longer represent every paisa and successive prices step by 2, 4, 8 and so on. This touches a handful of instruments, mostly high priced NSE equities and some index levels. The conversion never loses anything relative to the wire, because it rounds the float that was actually sent; the step is a property of the exchange's encoding, not of this pipeline. The raw float bits remain recoverable from the archive, which stores frames verbatim.

The synthetic checks pin the conversion on a price the float32 format cannot represent exactly, asserting the stored paise equals the paise of the unpacked float rather than the paise of the decimal that was packed.

## Dispatch is by response code, never by the length field

Each response code has a fixed total size, so the decoder walks a frame by reading the code and advancing by the known size. The header's two byte message length field is used only to skip an unrecognised code, and whether that field counts the header or only the payload is unverified against live bytes. The synthetic checks pin the convention chosen here, that it counts the whole packet, so a first live run that disagrees will show up as a failed check rather than as silent misalignment. This only affects the unknown-code path, because every known code advances by its documented size.

## The index packet layout is inferred, not documented

Dhan names response code 1 as an index packet but publishes no layout for it. Sixteen bytes with the ticker's layout, a float price followed by a four byte epoch, is the reading that fits the size, so that is what this module assumes and it marks the packet as an index rather than as traded data. The first live run should confirm this; if it disagrees, the raw bytes are in the archive to settle it.

## Response code 3 is undocumented but real

The documentation's response code table lists codes 1, 2, 4, 5, 6, 7, 8 and 50. Dhan's own client library also decodes a one hundred and twelve byte packet under code 3, carrying the last traded price and five interleaved twenty byte depth entries. The library's unpack string is the authority here, since the written documentation is silent. The entries are interleaved, one bid and one ask per twenty byte level, not five bids followed by five asks.

## The quote and full packet field orders

The day's four prices are open, close, high, low, in both the quote packet and the full packet. This is the order the documentation's byte table gives and Dhan's client library confirms, and it is not the order a reader would naturally assume, open, high, low, close. The full packet additionally puts three open interest fields between the buy and sell quantities and the day's prices, so a full packet read with the quote reader puts an open interest where the open belongs.

The wire also puts the total sell quantity before the total buy quantity, the reverse of Zerodha's order. Both orderings are covered by synthetic checks with distinct values.

## Full packet depth is interleaved, like the five level packet's

Each of the five depth entries in a full packet carries a bid quantity, an ask quantity, a bid order count, an ask order count, a bid price and an ask price. Reading them as five bids followed by five asks puts level two's bid where level one's ask belongs, producing plausible prices that are wrong. The synthetic check gives every level a distinct bid and ask price so the mistake cannot pass.

## Salvage rather than raise

Exactly as in the Zerodha decoder, a frame shorter than a header decodes to nothing, a frame ending mid packet returns what was read so far, an unknown code is skipped through a plausible length or stops the walk, and no path raises. This runs inside the socket read loop, where one exception would drop a connection carrying thousands of instruments.

## Why the tick carries the Zerodha decoder's keys

The decoded dictionary uses the same key names and the same shape as `stream/zerodha/packets.py`: `security_id` in place of `instrument_token`, `dhan_segment` in place of `kite_segment`, and the same price, quantity, open interest and depth key names. The shared database writer and Redis publisher, when they are built, need no broker branch. A previous close packet maps into `close_price` and `open_interest` with `tick_mode` of `prev_close`, so every key it emits is still a column of the ticks table.