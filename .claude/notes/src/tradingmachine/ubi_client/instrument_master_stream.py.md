# src/tradingmachine/ubi_client/instrument_master_stream.py

`InstrumentMasterStream` reads `GET /api/instruments/master` in batches. It was added on 2026-09-26 for instruments_explorer, which reads the whole master (about 540,000 instruments and 127 MB for `exchange=all&segment=all`, in about 7 seconds) into its own search index whenever UBI's mapping date changes.

## Why not `UnifiedBrokerInterface.get`

`get` reads the whole body with `response.json()`. For the full master that means holding 127 MB of text and then over half a million dicts at once. Worse, UBI writes the master with `utilities/json_stream.py` as one array in chunks of about 64 KB, and if something fails part-way through, UBI has already sent status 200: the array simply ends early. `get` would then either return None, because `_parse_body` swallows the JSON error, or, if the cut fell between values, never notice. The stream raises `IncompleteResponseError` in both cases, so a short catalogue can never be mistaken for a complete one.

## How it reads

`UnifiedBrokerInterface.stream_get` returns the open response once its status is known to be successful. The stream then:

1. requires the `X-Mapping-Date` header, raising `IncompleteResponseError` and closing the response when it is missing;
2. reads 64 KB chunks of bytes with `iter_content`, decoding them with an incremental UTF-8 decoder, because a multi-byte character such as `₹` can be split across two chunks and `iter_content(decode_unicode=True)` falls back to bytes when the response names no charset;
3. feeds the text to `JsonArrayStreamParser`, which returns each value once the character after it has arrived;
4. at the end of the body, calls the parser's `finish`, which raises when the closing bracket never came.

A `requests.RequestException` while reading becomes `UnreachableError`, naming how many instruments had arrived.

## Why `next_batch` as well as `batches`

instruments_explorer runs in an asyncio event loop and must not block it. `next_batch` reads only as much as one batch needs, so the caller can hand one call at a time to a worker thread with `asyncio.to_thread(stream.next_batch, 5000)` and await its own processing of each batch in between. `batches` is the plain generator for everyone else.

The caller must close the stream, or use it in a `with` block, whether or not it read to the end; closing releases the pooled connection.
