# src/tradingmachine/ubi_client/json_array_stream_parser.py

The parser was copied on 2026-09-26 from instruments_explorer's `instruments_explorer/unified_broker_interface/json_array_stream_parser.py`, together with its tests, when instruments_explorer moved its UBI access onto this library. Only the quote style and the docstring format changed.

It parses one top-level JSON array fed as consecutive pieces of text and returns each value as soon as it is complete. It uses `json.JSONDecoder.raw_decode` from the start of each value. A value is returned only once the character after it has arrived, because `raw_decode` would otherwise accept a number such as `123` that is really the start of `12345` split across two pieces. `finish` then checks that the closing bracket arrived and that nothing but whitespace follows it.

The buffer is trimmed to the unparsed tail after every piece, so memory stays at about one chunk plus one value however long the array is.
