# stream/dhan/credentials.py

Reads the two credentials a Dhan websocket URL needs: the client identifier and the access token, both passed as query parameters, since Dhan authenticates entirely in the URL and uses no handshake headers.

## The client identifier plays the API key's role, but lives elsewhere

Zerodha's websocket takes an API key that belongs to a Kite Connect application, separate from the login credentials. Dhan has no such split: the client identifier is a property of the account itself, and the login job sends it as `dhanClientId` when it obtains the access token. So the websocket's second credential is read from the same settings document that holds the PIN and the TOTP secret, even though it is permanent and does not rotate the way they do. It is not a secret in the sense they are, which is why the websocket can afford to put it in the URL.

## The issued-today check is stricter than Dhan's real expiry

Dhan's access tokens last roughly twenty four hours from issue rather than expiring at midnight, so the check that a token's `last_login` timestamp starts with today's date is a conservative proxy, not a mirror of the broker's rule. A token issued at 07:00 yesterday is technically good until 07:00 today, and this module refuses it from midnight onward.

The same reasoning as Zerodha's applies with a small difference. The point of the check is that an expired token must not be allowed to imitate some other kind of refusal. For Dhan the danger has a sharper edge than for Zerodha: a sixth websocket does not get refused, it evicts the oldest healthy connection with reason 805, so a probe or a connection supervisor that opened sockets with a dying token could silently knock over working connections. Refusing an arguably-still-valid token for the last few minutes of its life is the cheap side of that trade, and the login cron at 07:00 on weekdays makes the window where it matters a small one.

## Deliberate duplication

This module is written out separately rather than shared with the Zerodha and IndMoney credential readers, which do recognisably the same job. The copies differ in which collections they read, which fields they treat as permanent, and how they justify the date check, and a common helper would grow an argument for every one of those differences. Each broker keeps its own copy, per the project's standing preference.