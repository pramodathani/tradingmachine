# stream/dhan/depth_packets.py

Decodes the frames of Dhan's full market depth sockets, for both the twenty level and the two hundred level book. It imports `struct` and nothing else and is tested completely on bytes alone.

## Why this is a separate module from the live feed decoder, and why they share no code

The depth feed is a different wire format. Its header is twelve bytes with the message length first, then the response code, then the segment, the security id, and a last field that means different things on the two sockets. The live feed's header is eight bytes with the code first. A helper shared between the two decoders would have to be parameterised on the header shape, and a wrong argument would read one header with the other's offsets, exactly the class of silent mistake the project's per-broker duplication exists to prevent. This is the same reasoning that keeps the Zerodha index and tradeable decoders apart.

The two tables this module duplicates from `stream/dhan/packets.py`, the segment names and the disconnect reasons, are pinned together by a synthetic check that asserts both tables cover exactly the segments Dhan documents, so they cannot drift apart silently.

## One section per side, stacked in one frame

A depth frame is a stack of sections. Each section is a twelve byte header followed by one side of one instrument's book: bids under response code 41, asks under response code 51. A frame carries one instrument's bids followed by its asks, and may carry several instruments in subscription order. The decoder walks section by section and returns one tick per section, tagged with `side`.

## The header's last field means different things on the two sockets

On the twenty level socket it is a sequence number the documentation says to ignore, so the row count comes from the subscription's depth level, since a twenty level book is always twenty rows. On the two hundred level socket it is the number of rows that follow, capped at two hundred because that is the socket's maximum. `depth_rows` is the one function that encodes this difference, and the depth connection passes its own depth level into every decode call.

## Float64 prices convert to paise losslessly

Every depth entry is a float64 price, an unsigned four byte quantity and an unsigned four byte order count. A float64 is exact for any realistic price, so multiplying by a hundred and rounding loses nothing, and there is no equivalent of the live feed's float32 caveat here. Quantities and order counts are integers on the wire and are stored as they arrived.

## Disconnect frames are a different shape on this feed

A live feed disconnect is a ten byte packet on an eight byte header. A depth disconnect is a twelve byte header carrying response code 50 followed by a two byte reason code, so the reason sits at a different offset. `decode_disconnect` here reads the depth layout, and the connection layer calls it when a frame's code byte is 50.

## Salvage rather than raise

The same policy as both other decoders: a frame shorter than a header yields nothing, a frame ending mid section stops the loop with what was read, an unrecognised code is skipped through a plausible length or stops the walk, and nothing raises. One malformed frame must not take down a connection carrying a watched instrument's book.

## What this module deliberately does not decide

Whether the twenty level socket's message length field counts the header or the payload is unverified against live bytes, exactly as for the live feed, and it only matters for the unknown-code path. Whether the depth sockets share the five connection pool with the live feed is treated as true, on the principle that exceeding it costs an eviction of a healthy socket, which is worse than assuming a smaller pool than may exist.