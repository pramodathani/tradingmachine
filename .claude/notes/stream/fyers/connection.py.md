# stream/fyers/connection.py

## Why this is modelled on the Flattrade driver rather than the Zerodha one

Zerodha and Dhan put their credentials in the handshake, so their drivers learn whether a connection was accepted from an HTTP status code before a single frame is read. Flattrade and Fyers both open a socket with no credentials at all and authenticate with a message sent after the socket is up, which means acceptance and refusal are both things that happen in-band and several seconds later.

That difference drives the whole shape: an authentication timeout has to be a refusal rather than a slow server, the handshake status classification survives only for parity, and every session has to resubscribe because nothing about the previous one is remembered.

## The token in the authentication message is not the access token

Field 1 of the authentication message carries the `hsm_key` claim decoded out of the access token, not the access token. Sending the access token there does not work.

This is the single most surprising thing about the protocol and it is the mistake most likely to be made by anyone reading the field name alone, so `stream/fyers/credentials.py` returns the `hsm_key` as its own value rather than leaving the caller to remember to dig it out.

## The server sets an obligation it then never mentions again

The authentication reply carries an acknowledgement interval, and after that the server says nothing more about it. Every that-many data frames, the client owes an acknowledgement quoting the message number from the most recent frame. A connection that stops acknowledging is eventually stopped being fed.

The failure mode is what makes this worth spelling out: the socket stays open, the keep-alives keep working, and the data simply stops. That is indistinguishable from a subscription that was quietly dropped, so a missing acknowledgement would be diagnosed as a subscription problem and the real cause would never be looked at. `_acknowledgement_due` and `_send_acknowledgement` are small, but the reason they exist is not.

## The feed mode is a separate message and must go first

A socket that has authenticated but has not been told full or lite has been told nothing. `_send_subscription` sends the mode message before any subscription for that reason. Subscribing first is how a connection ends up delivering one price per instrument when twenty fields were wanted, and again the symptom is thin data rather than an error.

The mode message's channel field is a sixty four bit mask, not a channel number, so the channel is selected by raising the bit at its position. Passing the channel number where the mask belongs sets channel 11 to mean channels 0, 1 and 3.

## Two keep-alives, doing different jobs

The `websockets` library's protocol pings detect a half-open socket, where the connection is gone but nothing has told either end. Fyers additionally expects an application keep-alive, the three byte frame `bytes([0, 1, 11])`, every ten seconds, and closes a socket that stops sending it.

These are different jobs, so both run. Dropping the protocol ping because the application one exists would leave a dead socket looking alive; dropping the application one because the protocol ping exists gets a healthy socket closed.

## `on_session_start` exists because Fyers renumbers its topics

Fyers identifies an instrument in an update packet by a topic number that only a snapshot on the same connection gives meaning to, and it hands out fresh numbers on every connection. A topic table carried across a reconnection would attribute one instrument's prices to another, and nothing about the resulting ticks would look wrong.

The topic table lives in the `TickAssembler` the shard holds, not in this class, so rather than reaching into the shard's state this driver reports the new session through the `on_session_start` callback and lets the shard discard and rebuild. The callback fires after authentication and before anything is subscribed, which is the only window where the old table is certainly finished with and the new one is certainly empty.

## Refusal and authentication failure are deliberately different exceptions

The two demand opposite responses. A refusal means the account is at its connection limit: stop opening more, keep the ones that worked, and record the limit. An authentication failure means the token is wrong or expired: no number of connections will work, and retrying is both pointless and the fastest way to get the account noticed.

The same unreadable authentication reply means one or the other depending on history, which is why `_raise_for_authentication_reply` branches on `ever_connected`. On the very first session a refusal is about the credentials. On a later session, while earlier ones worked, the credentials are demonstrably fine and this connection was one too many.

Fyers documents one connection per user and says nothing about how a second is refused, so the four reasons this class knows — a failed authentication reply, a handshake status, an early close with a refusal code, and a reply that never arrives — are the complete set of ways it has been observed to say no. The capacity probe is what finds out which of them Fyers actually uses.

## `maximum_reconnect_attempts=0` is for probing, not for production

Zero does not mean "reconnect forever with no limit"; it means do not reconnect at all, and raise the first session's failure to the caller instead of swallowing it. The capacity probe needs that: a probe that silently retried would report a limit higher than the broker actually allows, because the retry would eventually succeed as an earlier probe connection timed out.
