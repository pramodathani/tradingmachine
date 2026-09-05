# stream/dhan/verify_stream.py

Checks that Dhan's binary frames are being decoded correctly. It mirrors `stream/zerodha/verify_stream.py` and grows alongside the Dhan module: this phase carries only the synthetic byte-level checks, later phases add the REST cross-check and the depth socket check.

## The synthetic checks, and why each one exists

A binary parser fails silently: a wrong offset, a wrong width, or a wrong field order produces numbers that are still plausible prices and quantities. Each check below targets one specific way the parser could be wrong, rather than exercising the happy path.

- Frames shorter than a header decode to nothing, on both feeds.
- The endianness check uses a security id whose bytes are zero, zero, zero, one, which a big endian reader reports as one and a little endian reader as one crore sixty seven lakh. Zerodha's frames are big endian, so this check is what stops the two decoders being confused with each other.
- The quote check asserts open, close, high, low order with four distinct prices, and that the wire's sell quantity comes before its buy quantity.
- The full packet check asserts the open interest fields sit before the day's prices, and that the five depth levels are interleaved, with order counts including 65535 so a wrong width shows up as wrong prices.
- The float32 precision check pins the paise conversion on a price the float32 format cannot represent exactly, asserting the stored paise equals the paise of the unpacked float rather than the paise of the decimal that was packed.
- The side packet check covers previous close, open interest, market status, and both feeds' disconnect packets.
- The truncation check cuts a stacked frame at every byte offset and asserts nothing raises, because the decode loop runs inside the socket read loop.

## The expected_paise helper

Every price assertion goes through one helper that computes the paise of the float32 round trip of the price, not the paise of the decimal. This is the decoder's actual contract, since the wire rounds the price before the decoder sees it, and writing the assertion in the check as the same expression the decoder evaluates means a conversion change fails loudly here rather than drifting silently.

## Building frames by hand

The builders write each packet byte by byte from the documented and library-derived layouts, with the message length field set to the whole packet including the header. That convention is this module's own choice, pinned by the unknown-code check, because the real field's coverage is unverified against live bytes. If a live run shows the field counts only the payload, the fix is in the builders and in the parsers' unknown-code path, and the synthetic checks say exactly where.

## Mutation testing, in phase 5

The synthetic checks are only as good as their ability to fail, so phase 5 deliberately introduces each dangerous mistake, reading a full packet with the quote reader, decoding the depth as five bids then five asks, reading security ids big endian, dropping the paise multiplication, and reading the open interest at the quote packet's offsets, and confirms the intended check fails for each one. A check that survives its own mistake was never a check.