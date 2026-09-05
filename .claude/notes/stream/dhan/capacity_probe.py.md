# stream/dhan/capacity_probe.py

Measures how much Dhan's websockets actually allow, run deliberately and by hand, and stores the two measurements in MongoDB `stream_capacity` as separate documents keyed on feed name: `market_feed` for the live feed and `twenty_depth` for the twenty level depth socket.

## The eviction changes how the connection count is read

Zerodha refuses a connection beyond its limit, so its probe counts refusals. Dhan does not refuse the excess connection, it evicts the oldest healthy one with disconnect reason 805, so a refusal-style probe would count one connection too many and, worse, would need the victim to be one of its own held-open probes to notice at all. This probe holds every earlier connection open while opening the next and watches for one of them dying, then counts the survivors plus the connection that caused the eviction as the measured limit. A refusal of the new connection itself counts only the survivors.

## The completeness question rides on the first live run

Like Zerodha's probe, this one judges a subscription honoured by whether every subscribed instrument arrived. That only works if Dhan sends a snapshot on subscribe, which the documentation does not promise and which this probe is the first thing to find out; the expectation is prev close packets on subscribe. If the first live run shows subscriptions completing with nothing delivered, the measured instrument count bounds acceptance only, the same way Zerodha's 108,431 figure bounds acceptance on a closed market, and the count must be re-qualified during market hours before it is trusted as sustained capacity.

## What each probe measures

The instrument ladder for the live feed is 5000, 8000, 10000, 15000, 20000, then the full universe, each candidate on a fresh connection, stopping at the first incomplete or refused subscription. The connection count probe opens baskets of two hundred instruments up to its ceiling, holding them open. The depth pass holds one live feed connection open throughout, then opens a fifty instrument twenty level socket, then a two hundred level socket carrying its single instrument, and records whether the twenty level socket kept serving after the two hundred level socket joined, which is the coexistence evidence for the shared five connection pool.

The safety margins differ from Zerodha's on purpose. Dhan signals eviction explicitly with reason 805, so the probe knows exactly when it crossed the line, and one connection of margin is enough. The Zerodha probe took two, because Zerodha's refusal is inferred from statuses and silence rather than named.

## The instrument universe is a pair, not a number

Dhan security ids are unique per exchange segment, not globally, so `live_instrument_pairs` returns (exchange segment, security id) pairs from `instruments.broker_mappings` joined to `instruments.master`, translated through the same segment mapping the verifier uses, with segments Dhan does not feed dropped and pairs de-duplicated. The 2026-09-06 mapping held 136,863 distinct pairs.

## What the stored documents mean

The `market_feed` document carries the same two safety-margined numbers Zerodha's does, with a margin of one connection. The `twenty_depth` document carries one connection and however many of the fifty instruments the depth socket delivered, with the two hundred level socket's coexistence evidence riding in its evidence list, because the two hundred level socket takes one connection for one instrument by design and has nothing to measure beyond coexistence.