# stream/dhan/verify_stream.py

Checks that Dhan's binary frames are being decoded correctly, in four modes: `--synthetic` byte-level checks that need no network, `--depth` a live hold of one depth socket, `--against-rest` the oracle comparison against Dhan's REST quote endpoint, and combinations of those.

## The synthetic checks target ways of being wrong, not the happy path

Every check exists because a specific misreading would still produce plausible numbers. The quote check would fail if the day's prices were read in the open, high, low, close order Zerodha uses instead of Dhan's open, close, high, low, the full packet check would fail if its depth were read as five bids then five asks rather than five interleaved levels, and the float32 precision check pins the conversion on a price the float32 format cannot represent exactly. Salvage behaviour is checked by truncating a stacked frame at every byte offset and asserting nothing ever raises, because an exception in the read loop would take down a connection carrying thousands of instruments.

## The wire code bytes are pinned, and mutation testing is why

The depth frame builder and the depth decoder share one module's constants, so planting a wrong bid response code and running the suite produced thirteen self-consistent passes and caught nothing: the builder wrote the mutated code and the decoder read it back happily. The `check_wire_code_bytes` check exists because of that failed mutation. It pins the constants' output to their literal documented values, live code 2 at byte 0 and depth bid 41, ask 51 and disconnect 50 at byte 2, so the constants cannot drift from the wire without the check noticing even though the suite would otherwise agree with itself.

The rest of the suite was mutation tested the same way, one planted mistake at a time: a big endian header, a divisor of one hundred and one, a shifted quote packet size, a full packet layout with the open interest figures displaced, a tightened plausible-epoch guard, a wrong depth bid code, a float32 read of the depth price, a depth header with the code at byte 0, and a renamed disconnect reason. Every one of them fails at least one check, and most fail several.

## --against-rest uses the broker as the oracle, with a measured scale

The synthetic checks prove the parser agrees with this file's idea of the format, since every byte they read was written here. The REST comparison uses Dhan's Market Quote endpoint as an independent oracle, so it catches a field that both the parser and the synthetic checks are wrong about in the same direction. It selects a spread of instruments from `instruments.broker_mappings` for Dhan's latest mapping date, excluding expired contracts, captures live ticks over one FULL mode connection, and compares every field the two sources share at a tolerance of 0.011 rupees.

The implied scale check is the part that settles an undocumented fact. Dhan documents no price divisor, so the comparison turns each stored price back into rupees and takes the median ratio against the REST price, segment by segment, preferring the close price for the ratio because it does not move between the capture and the fetch the way the last price does. A median of one means the wire carries rupees, which the decoder's conversion to paise assumes, and a median near one hundred or one hundredth would mean the divisor table needs a per-segment correction like Zerodha's NSE Commodity got.

The endpoint takes up to one thousand instruments per request at one request per second, so the fetch batches segments together into a single body and pauses between batches, rather than spending one request per segment.

## Instrument selection needs a translation the tables do not store

`instruments.broker_mappings` records Dhan's security id but nothing about which exchange segment it belongs to, and Dhan security ids are unique per segment, not globally. The selection joins `instruments.master` and translates the canonical exchange-prefixed segment, for example `bse_currency_futures`, into Dhan's segment number through `dhan_exchange_segment`. Segments Dhan does not feed, indexes on BSE and everything on NCDEX, translate to None and are skipped. One live catch from testing: the canonical bare segment is the plural `currencies`, so a check for a `currency` prefix silently misses it and must test both the plural and the prefixed forms.

## What still needs a live run

The full `--against-rest` path has only been exercised to the request boundary. It needs a token issued today, and the broker login cron runs on weekdays, so a weekday session is when the first real oracle run should happen. Two open questions ride on that run: whether Dhan delivers a snapshot on subscribe, which determines whether the oracle check is runnable outside market hours the way Zerodha's is, and whether the implied scale is one for every segment. When no ticks arrive at all, the mode reports a note and exits zero rather than passing silently, because outside market hours silence is the expected answer and during a session it would be the snapshot question answering itself.