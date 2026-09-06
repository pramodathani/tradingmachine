# requirements.txt

A curated list of direct dependencies, not a `pip freeze`. Only packages that tradingmachine imports directly are listed, and pip resolves the transitive set.

This file previously was a byte-for-byte copy of `unified_broker_interface`'s freeze, which carried 97 pins. That brought in that project's Selenium, Flask, and TUI stacks, and, more seriously, contained no Chroma client at all, so the Chroma container would have been unreachable from Python.

It also contained `dotenv==0.9.9` alongside `python-dotenv==1.2.3`. The `dotenv` package on PyPI is a stub, not the library that is actually imported. It has been removed.

## chromadb-client rather than chromadb

`chromadb` is the full server distribution, pulling in FastAPI, uvicorn, onnxruntime, and tokenizers. That is what runs inside the container. tradingmachine only ever talks to it over HTTP, so it needs just the `HttpClient`, which is what `chromadb-client` provides. The pinned version tracks the `chromadb/chroma` image tag in `docker-compose.yml`.

## TA-Lib needs no system library

There is no `libta_lib` on this host, and none is required. TA-Lib 0.6.8 publishes a `cp314` manylinux wheel with the C library bundled. This was verified by installing it and exercising 158 functions across all 10 function groups, including the Hilbert Transform functions, which are among the heaviest native code paths in the library.

## yfinance is a judgment call

It is kept for the `research/` directory, and it covers Indian tickers through the `.NS` and `.BO` suffixes. It is what drags in `curl_cffi`, `beautifulsoup4`, and `peewee` as transitive dependencies. If tradingmachine ends up sourcing its data from `unified_broker_interface` instead, dropping this one line removes those too.

## pyotp and selenium came back deliberately

Both were in the discarded `unified_broker_interface` freeze, and both were dropped when this file was curated. `utilities/broker_login.py` brought them back on purpose.

Every broker's login is protected by a time based one time password, which is what `pyotp` generates from the TOTP secret held in the MongoDB `settings` collection. Seven of the ten brokers then accept an ordinary API call, but Zerodha, Shoonya and Stoxkart have no login endpoint at all: the only way to obtain a request token is to fill in their web login form, which is what Selenium drives in headless Chrome.

Selenium 4 needs no separately installed chromedriver. Selenium Manager downloads a driver matching the installed browser on first use. Google Chrome 151 is already on this host.

Between them these two lines add ten packages, of which `trio`, `trio-websocket` and `sortedcontainers` are Selenium's async transport and the rest are small.

## httpx is declared without yet being imported

`httpx` was already in the environment as a transitive dependency of `chromadb-client`. Listing it here promotes it to a direct dependency and pins the version.

This is a deliberate exception to the rule at the top of this note, which says only packages tradingmachine imports directly are listed. Nothing imports `httpx` yet. It was added on the user's instruction, ahead of whatever will use it.

## Why the three login lines are not at the end of the file

They sit above `yfinance` rather than after `requests`, which is where a new dependency would otherwise go.

Two feature branches were adding to this file at the same time, and both were appending to the end. Git reads that as two different insertions at the same position and reports a conflict, in whichever order the branches merge. Adding the other branch's line to this branch as well does not help, because the inserted blocks still differ; that was tried and it still conflicted both ways. Leaving a few lines of unchanged context between the two insertion points does help, and both merge orders then apply cleanly. Both outcomes were checked by replaying the merges in a throwaway clone rather than reasoned about.

## Verification

The full set resolves and installs on Python 3.14.4 with no build from source. Every package has a `cp314` wheel. 88 packages are installed in total, and `pip check` reports no broken requirements.

The pre-fix version of this file is preserved outside the project, at the session scratchpad path `requirements.txt.orig`, because the project is not yet under version control.

## websockets and orjson arrived with the market data stream

Both were already present in `.venv` as transitive dependencies and both are now declared, because the streaming subsystem imports them directly and a transitive pin is not a promise.

`websockets` is the client the Zerodha ticker is built on. Zerodha publishes `pykiteconnect`, which would have supplied a ready-made ticker, but it is built on Twisted and Autobahn and runs everything on a Twisted reactor, of which there is exactly one per process. That would have forced either one reactor serving several connections, where a slow callback stalls parsing for all of them, or a process per connection anyway. Since the design already puts each connection in its own process, the Twisted dependency bought nothing and cost control over reconnection, timestamping and the decode path, so the client is written directly against `websockets` instead.

`orjson` encodes the ticks that go onto the Redis bus. It matters here in a way it would not elsewhere: at the published rates the encoder runs tens of thousands of times a second, it encodes `datetime` natively without a default hook, and it is several times faster than the standard library `json`. The alternative considered was publishing the raw broker bytes, which would have been faster still but would have forced every consumer to carry a per-broker binary parser, defeating the purpose of a shared bus.

## The archive needs no compression dependency

The raw frame archive is compressed with zstd, and there is deliberately no `zstandard` line in this file. Python 3.14 ships `compression.zstd` in the standard library, bound to libzstd 1.5.7 on this host, which was verified in this virtual environment before the archive was designed around it. That keeps the compression on the one path that must never fail free of third-party code.

## PyNaCl arrived with the Groww feed, and only for Ed25519

Groww's market data feed is a NATS message bus carried over a websocket, and NATS authenticates the client with an NKEY: the server sends a nonce, and the client must return an Ed25519 signature over it alongside the JSON Web Token Groww minted for the key. Python's standard library has no Ed25519, so exactly one third-party primitive is unavoidable here.

`PyNaCl` is what supplies it. Groww's own SDK uses the same library for the same purpose, it is a thin binding over libsodium with no dependencies of its own beyond `cffi`, which is already installed, and `stream/groww/credentials.py` imports precisely two names from it. Everything else the NKEY handshake needs is written out in that module: the base32 encoding, the XMODEM CRC the encoding appends, and the unpadded base64url of the signature.

The alternative was `cryptography`, which also provides Ed25519. It was not chosen because it is a much larger package carrying a Rust toolchain's worth of compiled code for one function call, and because matching Groww's own choice makes the handshake easier to compare against their SDK when it changes.

What was deliberately not taken is `nats-py`, along with its `nkeys` and `aiohttp` dependencies. The NATS client protocol is a handful of newline terminated text operations, the project already speaks `websockets` directly for every other broker, and `stream/groww/connection.py` hand-rolls the protocol for the same reason `stream/fyers/depth_packets.py` hand-decodes protobuf: it keeps the reconnection, the refusal classification and the timestamping under this project's control.

It sits above `PyYAML` rather than at the end of the file, for the merge reason recorded above.
