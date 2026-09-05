# stream/dhan/connection.py

Drives one Dhan live market feed websocket connection. It mirrors `stream/zerodha/connection.py` in shape, including the identical health counter names, so a shared supervisor or health module can treat both brokers' connections the same way.

## Authentication is entirely in the URL

Zerodha signs its handshake with a header; Dhan takes everything as query parameters on the URL, so there are no handshake headers at all here. Two consequences follow. The access token is a JWT whose characters include ones a query string would otherwise misread, so both credentials are URL quoted. And the connection's credentials are visible in the URL, which is normal for this feed and one reason the client identifier, unlike the token, is not really a secret.

## No connect packet is sent

The written documentation lists RequestCode 11 as "Connect Feed". Dhan's own client library, on the version two feed, opens the socket and immediately subscribes, sending no connect packet, and that library is the authority wherever it and the documentation differ. So this module subscribes immediately too. The constant is kept, and the note is here: if a first live run shows subscriptions being silently ignored, sending the connect request first is the first thing to try.

## The feed's keep-alive rules, and what we add on top

Dhan's server pings every ten seconds and closes a connection it has heard nothing from for forty seconds. The pings are websocket protocol pings, which the library answers automatically, so there is no code here for them. What this module adds is its own client side ping at a twenty second interval with a ten second timeout, so a dead socket is detected in about thirty seconds, inside Dhan's forty second window. This is the same half-open-connection argument Zerodha's connection makes, tuned to Dhan's cadence rather than Zerodha's two and a half second one, because a socket the server is actively pinging is unlikely to be half-open in the first place.

## Batching is the wire's own rule

Zerodha's five hundred instrument batches were a choice made in the absence of a documented limit. Dhan caps a subscription message at one hundred instruments and requires the instrument count to match the list length, so the hundred is not negotiable, and a connection carrying thousands of instruments sends its subscription as a series of messages.

## The refusal taxonomy is cleaner than Zerodha's, because Dhan says why

Zerodha's refusals have to be inferred from handshake statuses, close codes and silence. Dhan sends a disconnect packet carrying a two byte reason, and the reasons split into two opposite answers. An expired token, an invalid client identifier or a failed authentication means the credentials are wrong and no connection will ever work, so that raises an authentication error. Exceeding the connection limit or lacking the data entitlement means the credentials are fine and this particular connection was one too many, so that raises a refusal. Handshake statuses and early closes map the same way they do for Zerodha, and an undocumented disconnect reason is treated as a refusal, because recording it as one is recoverable and treating a possibly-authenticating failure as a refusal to retry is not.

## An eviction is not a refusal, and must not be retried tightly

The sharpest difference from Zerodha: Dhan does not refuse a sixth websocket, it closes the oldest healthy one with reason 805. A tight reconnect loop on an evicted socket therefore churns healthy siblings, and the backoff exists partly to prevent exactly that. A connection reporting 805 is telling the supervisor to stop opening connections, not to try again, and the class docstring states the budget: live feed sockets and depth sockets together must stay at or below the measured count.

## The heartbeat test is a frame shorter than the header

Zerodha's one byte heartbeat made "shorter than two bytes" the right test. Dhan sends no one byte heartbeats; its shortest frame is the eight byte header of a market status packet, so the test here is a frame shorter than the eight byte header, and any such frame is counted as a heartbeat and cannot carry a packet. A disconnect packet, by contrast, is counted, handed to the callback so the archive holds the reason the connection ended, and only then raises.