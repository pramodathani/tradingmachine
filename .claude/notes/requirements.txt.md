# requirements.txt

A curated list of direct dependencies, not a `pip freeze`. Only packages that black_box imports directly are listed, and pip resolves the transitive set.

This file previously was a byte-for-byte copy of `unified_broker_interface`'s freeze, which carried 97 pins. That brought in that project's Selenium, Flask, and TUI stacks, and, more seriously, contained no Chroma client at all, so the Chroma container would have been unreachable from Python.

It also contained `dotenv==0.9.9` alongside `python-dotenv==1.2.3`. The `dotenv` package on PyPI is a stub, not the library that is actually imported. It has been removed.

## chromadb-client rather than chromadb

`chromadb` is the full server distribution, pulling in FastAPI, uvicorn, onnxruntime, and tokenizers. That is what runs inside the container. black_box only ever talks to it over HTTP, so it needs just the `HttpClient`, which is what `chromadb-client` provides. The pinned version tracks the `chromadb/chroma` image tag in `docker-compose.yml`.

## TA-Lib needs no system library

There is no `libta_lib` on this host, and none is required. TA-Lib 0.6.8 publishes a `cp314` manylinux wheel with the C library bundled. This was verified by installing it and exercising 158 functions across all 10 function groups, including the Hilbert Transform functions, which are among the heaviest native code paths in the library.

## yfinance is a judgment call

It is kept for the `research/` directory, and it covers Indian tickers through the `.NS` and `.BO` suffixes. It is what drags in `curl_cffi`, `beautifulsoup4`, and `peewee` as transitive dependencies. If black_box ends up sourcing its data from `unified_broker_interface` instead, dropping this one line removes those too.

## pyotp and selenium came back deliberately

Both were in the discarded `unified_broker_interface` freeze, and both were dropped when this file was curated. `utilities/broker_login.py` brought them back on purpose.

Every broker's login is protected by a time based one time password, which is what `pyotp` generates from the TOTP secret held in the MongoDB `settings` collection. Seven of the ten brokers then accept an ordinary API call, but Zerodha, Shoonya and Stoxkart have no login endpoint at all: the only way to obtain a request token is to fill in their web login form, which is what Selenium drives in headless Chrome.

Selenium 4 needs no separately installed chromedriver. Selenium Manager downloads a driver matching the installed browser on first use. Google Chrome 151 is already on this host.

Between them these two lines add ten packages, of which `trio`, `trio-websocket` and `sortedcontainers` are Selenium's async transport and the rest are small.

## httpx is declared without yet being imported

`httpx` was already in the environment as a transitive dependency of `chromadb-client`. Listing it here promotes it to a direct dependency and pins the version.

This is a deliberate exception to the rule at the top of this note, which says only packages black_box imports directly are listed. Nothing imports `httpx` yet. It was added on the user's instruction, ahead of whatever will use it.

## Why the three login lines are not at the end of the file

They sit above `yfinance` rather than after `requests`, which is where a new dependency would otherwise go.

Two feature branches were adding to this file at the same time, and both were appending to the end. Git reads that as two different insertions at the same position and reports a conflict, in whichever order the branches merge. Adding the other branch's line to this branch as well does not help, because the inserted blocks still differ; that was tried and it still conflicted both ways. Leaving a few lines of unchanged context between the two insertion points does help, and both merge orders then apply cleanly. Both outcomes were checked by replaying the merges in a throwaway clone rather than reasoned about.

## Verification

The full set resolves and installs on Python 3.14.4 with no build from source. Every package has a `cp314` wheel. 88 packages are installed in total, and `pip check` reports no broken requirements.

The pre-fix version of this file is preserved outside the project, at the session scratchpad path `requirements.txt.orig`, because the project is not yet under version control.
