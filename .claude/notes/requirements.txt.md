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

## Verification

The full set resolves and installs on Python 3.14.4 with no build from source. Every package has a `cp314` wheel. 78 packages are installed in total, and `pip check` reports no broken requirements.

The pre-fix version of this file is preserved outside the project, at the session scratchpad path `requirements.txt.orig`, because the project is not yet under version control.
