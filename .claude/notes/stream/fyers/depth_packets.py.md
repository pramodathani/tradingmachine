# stream/fyers/depth_packets.py

## This feed is the opposite of the quote feed in every respect

Fyers documents the tick-by-tick socket fully, publishes its schema at `https://public.fyers.in/tbtproto/1.0.0/msg.proto`, and encodes it in Protocol Buffers. The quote feed, by contrast, is a private binary layout that appears in no documentation at all. So the two decoders in this package share nothing and were arrived at completely differently: one from a published schema, the other by reading a client library.

What this feed does not do is carry many instruments. Fyers documents five symbols per connection against three connections per user, so fifteen at a time. That makes it a watched-symbol feature rather than a way to cover the universe, and it stands in exactly the same relation to the quote feed as Dhan's two hundred level depth socket does to its live feed: built, useful for a handful of instruments, and never the thing that carries the bulk.

## Why the protobuf is decoded by hand

The obvious alternative is to run the schema through `protoc` and commit the generated module. This decodes it by hand instead, for reasons that are about this project rather than about protobuf.

The schema uses two of protobuf's six wire types. Every scalar is wrapped in a standard wrapper message whose only field is the value. The whole of what a depth subscription needs is four message types. A varint reader and a tag loop cover that in less code than a generated module's import machinery, and the result reads like the other decoders here rather than like generated output.

It also keeps a promise the rest of the package makes. `requirements.txt` gains nothing, no build step is introduced, and the module stays testable on bytes alone exactly as `stream/zerodha/packets.py` and `stream/flattrade/packets.py` are.

The correctness argument for generated code was answered directly rather than waved away. Golden frames were encoded once by Fyers' own generated code, from their published schema, and are stored as bytes in `verify_stream.py`. Every run decodes those bytes with this module and asserts the values they were built from, so the hand-rolled reader stays pinned to the official encoder without the client library needing to be installed or a build step to exist. Regenerating them needs the library and is a deliberate act, which is the point: the vectors are evidence, not fixtures that move when the code does.

## Two protobuf details that are easy to get wrong

Negative `int64` values are written as their two's complement in ten bytes, not zigzag encoded. `sint64` is the zigzag type and this schema does not use it. A negative price read without `signed_value` comes back as roughly eighteen quintillion, which is obviously wrong when you see it and completely invisible when you do not look.

A wrapper message that is present but empty means the value really is zero, which is different from the wrapper being absent, which means the server did not set the field. That distinction is the entire reason the schema wraps its scalars, and `read_wrapper_value` returning zero for an empty wrapper while the caller leaves absent fields as None is what preserves it.

`skip_field` steps over unread fields by wire type rather than by field number, so a field Fyers adds to the schema later is stepped over cleanly instead of derailing the parse.

## Levels carry their own position, which is what makes differences work

Fyers sends the full book once when a subscription starts and only the levels that moved afterwards. Each level carries a `num` giving its zero-based place in the book, so a difference carrying three levels updates those three places and leaves the other forty-seven alone.

`apply_levels` writes by position and skips a level whose number is missing or out of range rather than appending it. Appending would lengthen the array, and an instrument whose book is fifty-three levels long when every other instrument's is fifty is a problem that surfaces far downstream from where it was created.

A snapshot clears the book before applying, because a snapshot describes the whole book and any level left over from before it is stale rather than merely old.

## The assembler needs no topic table

Unlike the quote feed, every message here names its instrument, so a difference is at least self-identifying and a frame from the archive can be read without replaying the session that preceded it. The assembler still belongs to one connection, because a book half built from one session's snapshot and half from another's differences would be neither, but the failure if it were shared is a stale book rather than one instrument's prices appearing under another's name.
