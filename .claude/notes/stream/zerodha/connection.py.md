# stream/zerodha/connection.py

Drives one Zerodha websocket connection: handshake, subscription, frame delivery and reconnection. It owns a socket and nothing else, handing every frame to a callback without decoding, storing or interpreting it.

## Resubscribing on every reconnection is mandatory

Zerodha retains no subscription state across connections. A reconnected socket that does not resubscribe stays open, answers pings, receives heartbeats, and delivers no data forever. Since the reconnection is otherwise invisible, this failure looks exactly like a quiet market.

`_send_subscription` therefore runs on every session, not only the first, and it sends both the subscribe and the mode message. A bare subscribe puts instruments into quote mode, so full mode always needs the second message; a connection that sent only the first would come back carrying 44 byte packets instead of 184 byte ones and would quietly lose market depth.

## Subscriptions are sent in batches

Tokens go out five hundred at a time rather than as one message. Zerodha documents no maximum message size, and a shard carries several thousand tokens, so a single message would be a JSON array of a size nothing has promised to accept. Batching also makes a refusal attributable to a batch rather than to an entire subscription.

## The four ways a connection can be refused

Discovering how many connections the account really allows depends on telling refusal from every other kind of failure, and refusal has four different signatures.

A handshake rejection raises `InvalidStatus` and carries a status code. A connection accepted and then closed within a few seconds with code 1008, 1011 or 1013 is a refusal that arrived after the handshake. A JSON error frame is advisory evidence, logged verbatim but never parsed for logic, since it is prose that Zerodha can reword at any time. The fourth has no error at all: the connection is accepted, the subscription is accepted, and data simply never arrives.

`seconds_since_last_data_frame` exists for that fourth case and deliberately ignores heartbeats. Zerodha keeps sending its one byte heartbeat on a connection it is not serving, so a socket that is open, subscribed and silent apart from heartbeats is precisely the signature of a subscription accepted and not honoured. Excluding heartbeats is what turns an invisible failure into a number. The connection reports the number and does not act on it, because whether silence means trouble depends on the time of day, which is the caller's business.

## Authentication failure is not refusal

`ZerodhaAuthenticationError` and `ZerodhaConnectionRefusedError` are separate because the correct responses are opposite. A refusal means the account is at its limit, so the right move is to stop opening connections and carry on with the ones that worked. An authentication failure means the token is wrong, no connection will ever succeed, and retrying is both pointless and the fastest way to draw attention to the account.

The two are distinguished by whether this object has ever connected. A 403 on the very first attempt is a credentials problem; the same status on the fifth attempt while four connections are healthy is the limit being found.

## Two defaults from the websockets library are wrong here

`compression` is set to `None`. The library negotiates permessage-deflate by default, which would spend CPU compressing a payload that is already dense binary, on the latency-critical path, for very little gain.

`max_size` is raised from the default one megabyte. A full mode frame carrying several thousand instruments at once can approach that, and the library's response to an oversized frame is to drop the connection.

The ping settings follow `pykiteconnect`: a ping every 2.5 seconds and a 5 second timeout. That is much more frequent than the library's default of 20 seconds, and it exists to catch a half-open connection quickly, which is a real condition on a socket held open all day.

## The backoff is deliberately unhurried

Reconnection backs off from two seconds to a minute. This is slower than it needs to be for an ordinary dropped connection, and that is the point: the design runs many more connections than Zerodha documents, so a tight retry loop against a broker that has just refused one is the behaviour most likely to cost the account. Waiting is cheap and the archive is unaffected by a gap of a few seconds.

`maximum_reconnect_attempts` of zero means do not reconnect at all, which is what capacity probing wants: a probe needs to know whether one connection succeeded, not to be quietly rescued by a retry.
