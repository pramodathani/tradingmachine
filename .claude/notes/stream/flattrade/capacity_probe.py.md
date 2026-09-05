# stream/flattrade/capacity_probe.py

## Why this probe exists at all

Flattrade documents no connection limit and no instrument limit. Zerodha's and Dhan's probes were written to test whether documented limits were real; this one has to discover the limits from zero, which is why the instrument ladder runs higher (5000 through 80000) and the connection ceiling is lower (20) than the other brokers' probes — with no documentation there is no reason to expect a large connection count, and 146,513 distinct keys means the instrument axis is the one that matters.

## The universe is 146,513 keys

The distinct instrument keys after expiry filtering and segment filtering, measured live. For comparison, Dhan's live universe is a few tens of thousands. No single Flattrade connection can be assumed to carry the whole universe, and the probe's last candidate is deliberately the full universe so the run learns exactly where acceptance stops. The deduplication is on the "EXCHANGE|TOKEN" string itself rather than on instrument identity, because Flattrade's scrip master carries more duplicate tokens than any other broker's and two master instruments can share one wire key.

## What the probe watches for instead of a documented refusal

The protocol's only observed way of saying no is the connect acknowledgement answering Not_Ok on a session that is not the first, which the connection driver raises as `FlattradeConnectionRefusedError` with reason "connect_not_ok". The connection-count probe holds every earlier connection open and counts survivors, the same shape Dhan's probe uses, because a limit on simultaneous connections can only be seen through connections that stay open. Whether Flattrade ever evicts an earlier connection when one too many arrives is an open question; if it does, the "earlier_connection_died" branch is what records it.

## The depth pass holds a touchline connection open

The five depth measurement opens its depth connection while one touchline connection carries a 200-instrument basket, so the answer reflects an account that is already streaming. The depth basket is 500 instruments, a choice rather than a documented number, and larger than the touchline basket on the reasoning that a depth snapshot is bigger per instrument, so the constraint is more likely to bind there. Whether Flattrade shares one limit across both feeds or caps each separately is an open question; if the depth connection is refused while the touchline one is serving, that is the answer.

## What it stores

Two documents in `stream_capacity`, feed "market_feed" (touchline measurements) and feed "five_depth" (one depth connection's delivery count), following the Zerodha and Dhan convention that separately capped feeds get separate documents. `--no-store` reports without recording, for the first cautious run.