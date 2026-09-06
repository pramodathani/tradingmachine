# stream/groww/credentials.py

Reads the daily access token, generates the session key pair, exchanges its public half for a socket token, and signs the nonce each connection is issued.

## Why this module does more than the other brokers' copies

Every other `stream/<broker>/credentials.py` reads two values out of MongoDB and hands them over. Groww's feed is a NATS message bus, and NATS does not authenticate with a bearer token at all. It authenticates with an NKEY, which is an Ed25519 key pair, plus a JSON Web Token that vouches for the public half.

So there are three steps rather than one. The daily access token is read from `last_login`. A key pair is generated. The public half is posted to `https://api.groww.in/v1/api/apex/v1/socket/token/create/` with the access token as a bearer credential, and Groww answers with a JSON Web Token and a subscription identifier. From then on the access token plays no further part: the socket presents the JSON Web Token and proves it owns the key by signing a nonce.

## The key pair belongs to the session, not to the account

It is generated with `os.urandom(32)` and never written anywhere. This is deliberate rather than an oversight.

The pair is not an account credential. It is minted, vouched for, used, and thrown away, and Groww will mint another for another key on request. Storing the private half would create a durable secret where the design currently has none, and would buy nothing, because obtaining a fresh one costs a single HTTP request that the connection has to make anyway to get its JSON Web Token.

Groww's own SDK reaches the same conclusion by the same route: `growwapi/groww/feed.py` calls `os.urandom(32)` per `GrowwFeed` instance.

## The NKEY encoding is written out rather than imported

`nkeys` is a real package and Groww's SDK depends on it. It is not a dependency here, because the part of it this project needs is one function: take a public key, prepend a kind byte, append a CRC-16/XMODEM checksum in little endian, base32 encode the lot and strip the padding. That is `crc16` and `encode_nkey`, thirty lines between them, and it removes a dependency whose only other contribution would be seed encoding that this project does not need, since it keeps the seed as raw bytes and never writes it to a credentials file.

The user prefix byte is `20 << 3`, which is what makes an encoded user key start with `U`.

This was not reasoned about and left there. `encode_nkey` was checked against `nkeys.KeyPair.public_key` over two hundred randomly generated keys with no mismatch, and `sign_nonce` against `nkeys.KeyPair.sign` on the same keys. The library was downloaded to a scratch directory for the comparison and is not installed in the project environment.

## Ed25519 is the one thing that could not be written out

Hence PyNaCl, and hence exactly two names imported from it. The reasoning for choosing it over `cryptography`, and for not taking `nats-py`, is in the note on `requirements.txt`.

## Why the login date stands in for an expiry

Fyers' access token says when it expires, and `stream/fyers/credentials.py` reads that claim rather than guessing. Groww's does not, so this module falls back on what Zerodha's, Dhan's, Flattrade's and Shoonya's copies do: a token whose `last_login` date is not today is treated as unusable.

The check earns its place here more than it does elsewhere. A stale access token does not fail at the socket, it fails one step earlier and less legibly, when Groww refuses to mint a socket token for it. Rejecting it here produces an error naming the login command instead of an HTTP status from an endpoint the reader has never heard of.

## What the subscription identifier is, and why it is returned and then dropped

Groww's token response carries a `subscriptionId` alongside the token. It addresses this account's own order and position update subjects, `stocks/order/updates.apex.<id>` and the derivatives equivalents. Market data subjects do not use it; they are addressed by exchange token.

`request_socket_token` returns it anyway rather than discarding it inside, because it is what the response contains and a caller that later wants order updates should not have to re-mint a token to get it. `websocket_credentials` is the caller that does not want it.
