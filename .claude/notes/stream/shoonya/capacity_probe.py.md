# stream/shoonya/capacity_probe.py

## Why this probe exists when Shoonya publishes a limit

Shoonya's rate limits page is unusually definite: "1 connection per session", with every symbol multiplexed over that one socket. Flattrade's probe exists because Flattrade documents nothing; this one exists despite Shoonya documenting something, for two reasons.

The first is that published websocket limits have not survived contact with any broker measured so far, so a number in a documentation page is a hypothesis. The second is more practical: the number Shoonya publishes is not the number that constrains this project. Whether one connection or four can be opened matters far less than how many of 146,921 instruments a single connection will actually carry, and that number appears nowhere in the documentation at all. The instrument ladder is the pass that earns the probe's existence; the connection pass is what settles the published claim either way.

A run that stops at one connection has confirmed the documentation, which is a good outcome and worth having on record rather than assumed.

## The universe is 146,921 keys across seven exchange codes

Measured live against `instruments.broker_mappings` at the latest mapping date, after excluding expired contracts and the segments Shoonya lists but does not feed:

```
  BFO    36,085
  BSE     4,731
  CDS    11,043
  MCX    14,749
  NCX         4
  NFO    77,163
  NSE     3,146
```

NCX is the code no other broker's stream reaches, and it is tiny — four live contracts. That is small enough that an NCDEX instrument may well not appear in a `--per-exchange 3` verification sample if all four have expired, and small enough that it will never be the reason a connection runs out of room. It is worth carrying anyway, because it is coverage no other broker in this project provides.

The deduplication is on the "EXCHANGE|TOKEN" string rather than on instrument identity, because two master instruments can share one wire key, and subscribing to the same key twice both wastes a slot and makes a complete snapshot look permanently incomplete.

## What the probe watches for instead of a documented refusal

Shoonya documents the limit but not the refusal. The protocol's clearest way of saying no is the connect acknowledgement answering `Not_Ok` on a session that is not the first, which the connection driver raises as `ShoonyaConnectionRefusedError` with reason "connect_not_ok". The connection-count probe holds every earlier connection open and counts survivors, because a limit on simultaneous connections can only be seen through connections that stay open. If Shoonya instead evicts an earlier connection when one too many arrives, the "earlier_connection_died" branch is what records it — and given a documented limit of one, that branch is more likely to fire here than it was for Flattrade.

## The depth pass answers a more basic question here

For the other brokers, the depth pass measures how much depth costs. For Shoonya it first has to establish that depth exists at all, since no page documents it. Zero delivered with no refusal is the signature of a subscription accepted and silently not honoured — and outside market hours it is also exactly what a closed market looks like. So a zero from this pass is only meaningful read against the touchline pass in the same run: touchline serving and depth silent is a real finding, both silent is an inconclusive run.

The depth connection is opened while a touchline connection carries a 200-instrument basket, so the answer reflects an account that is already streaming. That matters more here than for Flattrade, because if the documented one-connection limit is real then the depth connection is the second connection and may be refused for that reason rather than for anything to do with depth. The evidence records both stages, so the two causes stay distinguishable.

## What it stores

Two documents in `stream_capacity`, feed "market_feed" (touchline measurements) and feed "five_depth" (one depth connection's delivery count), following the convention the other three brokers already use. `--no-store` reports without recording, which is what the first cautious run should use.
