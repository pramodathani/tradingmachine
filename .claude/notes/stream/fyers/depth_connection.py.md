# stream/fyers/depth_connection.py

## Subscribing is not enough: the channel has to be resumed

This is the one trap on this socket and it is worth stating plainly. Putting symbols on a channel does not start data flowing. The channel also has to be resumed, in a separate message of a different type.

A connection that subscribes and never resumes sits open, keeps answering pings, and stays silent forever. That is indistinguishable from a subscription that was refused, from a symbol the exchange serves no tick-by-tick data for, and from a market that is closed. `_send_subscription` therefore always sends both messages, in that order, and never one without the other.

## Why the address is discovered rather than hard-coded

Fyers publishes `wss://rtsocket-api.fyers.in/versova` in its documentation and also serves an address from `https://api-t1.fyers.in/indus/home/tbtws`, and its own client library asks the endpoint every time rather than trusting the documented value. That is a strong hint that the two are expected to diverge.

`discover_websocket_url` asks, and falls back to the documented address on any failure at all: a timeout, a non-JSON body, an unexpected shape. A documented address that might be stale is better than refusing to connect, and the fallback costs nothing when the endpoint is healthy.

## This authenticates completely differently from the quote socket

The quote socket opens with no headers and authenticates in-band with a token dug out of the access token's claims. This one sends an ordinary `Authorization` header whose value is the application identifier and the access token joined by a colon.

The two share a package and share almost nothing else, which is why `stream/fyers/credentials.py` returns three values and each driver takes what it needs rather than the two drivers trying to share a credential shape.

## Error frames are the only way a rejected symbol is reported

If a symbol is wrong, or is one the exchange does not serve tick-by-tick data for, Fyers says so in a frame marked as an error and then simply never sends data for it. Nothing else surfaces this: the connection stays healthy and the other four symbols keep flowing.

So `_handle_frame` pulls the text out of every error frame, logs it, keeps the most recent one on the connection, and passes it to `on_error_message`. Error frames deliberately do not refresh `last_data_frame_at`, so a connection receiving nothing but errors correctly reports that it has never been served.

## The documented limits are recorded but not enforced

`DOCUMENTED_SYMBOLS_PER_CONNECTION` and `DOCUMENTED_CONNECTIONS_PER_USER` are here as constants and nothing checks against them. That is deliberate and consistent with how every broker in this project is treated: documented limits have been wrong for every broker so far, sometimes by more than an order of magnitude, so the capacity probe measures rather than the driver assuming. The constants record what Fyers claims so the probe's result can be compared against it.
