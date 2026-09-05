# stream/zerodha/capacity_probe.py

Measures Zerodha's real websocket limits by trying them, and records the answer in `stream_capacity` so it is never measured by accident. Run by hand as `python3 -m stream.zerodha.capacity_probe`; it is deliberately not part of the daily session.

## What the measurement leans on

Zerodha sends a full snapshot of every subscribed instrument the moment it accepts a subscription. That is what makes this probe possible at all, and it is why the probe works on a weekend: completeness is judged from the snapshot rather than from ticks, so nothing has to be trading.

The probe exploits the worst failure mode in the whole streaming design. A broker can accept an over-limit subscription and then quietly serve only part of it, with no error anywhere — the one refusal signal that nothing downstream can see. Here it becomes visible immediately, because instruments missing from the snapshot are exactly instruments that were not served.

## Why tokens are DISTINCT and expiry-filtered

`live_instrument_tokens` applies two filters, and the earlier ad-hoc probing session showed both of them mattering in practice. Expired contracts are excluded because they will never tick and would make capacity look consumed by instruments that produce nothing. De-duplication matters even more: one Zerodha token can map to more than one instrument identity, so the mapping table returns 108,601 rows holding only 108,431 distinct tokens. Probing with the raw row list makes a complete snapshot look incomplete — 88 of 5,000 "missing" — and sends the probe chasing a capacity limit that does not exist.

## Completeness is an explicit criterion, not a heuristic

The collector waits until every subscribed token has arrived, not for a quiet period. An earlier version used a settle window, and it drew the wrong conclusion twice from the same data: a subscription that had simply not finished arriving within the window was recorded as truncated. With the explicit criterion, "the snapshot has not finished yet" and "the snapshot will never finish" are different observations.

## The two probes and their safety margins

Instruments are probed on one connection at a time over an ascending ladder, ending at the entire live universe, because a subscription added to an existing connection would not distinguish a connection that accepts many instruments from one that accepts many subscriptions. Connections are probed by opening one at a time and **holding every earlier one open**, because the question is how many the account supports simultaneously, and because a broker that starves an older connection when a new one arrives would go unnoticed if each probe closed the previous one.

Both probes stop at the first refusal rather than probing around it. The stored numbers are then deliberately smaller than the measurements: connections minus 2, instruments at 80 percent. The margin is the honest response to measuring against an undocumented limit — the account is the asset at risk if Zerodha ever starts enforcing its documented 3.

## The ceiling is a courtesy to the broker

`--ceiling` bounds the connection probe regardless of what the account allows, so a runaway probe cannot sit opening connections indefinitely. The default of 40 is well above anything measured; the flag exists so the module can be smoke-tested cheaply, as it was on the night it was written — full instrument ladder, connection probe capped at 2, `--no-store`.

`--no-store` exists for the same reason: a truncated run must not overwrite a good measurement. The stored document is only written by a run that measured both limits properly.

## What the measurement does and does not establish

The 108,431 figure is the largest subscription Zerodha *accepted and snapshotted in full* on a closed market. It is not evidence that one connection can *sustain* the whole universe while it ticks. Under live load the failure modes are quieter than a handshake refusal: throttled delivery, frames arriving slower than the market produces them, or the same silent partial service that this probe watches for. The weekend number should be read as an upper bound on acceptance, with the operationally meaningful number — instruments per connection under real tick load — left for a deliberate market-hours measurement.

That re-measurement belongs to the health counters rather than to another probe. A full-universe session on Monday will show directly whether delivery keeps pace, through `last_frame_age_seconds`, `packets_per_second` and `decode_microseconds_per_frame`; if it cannot, the stored `instruments_per_connection` comes down and the shortfall is covered by more connections, which the measured 25-connection limit has room for.

## Why the first authentication failure is raised, not recorded

A `ZerodhaAuthenticationError` propagates out of the probe rather than being counted as evidence. A bad API key or a stale token is refused at the very first handshake, with the same status code an over-limit connection gets at the twenty-sixth. Recording it would write "the account allows nothing" over a perfectly good measurement; raising it keeps the authentication failure visible as what it is, and `credentials.py` already refuses to hand over a token that was not issued today so the common case never reaches here.