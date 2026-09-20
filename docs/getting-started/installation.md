# Installation

Trading Machine is an installable Python library named `tradingmachine`. It runs on Python 3.14 in
a virtual environment at `.venv/` in the repository root. Every command below uses that interpreter
directly rather than a system-wide one, which is the convention throughout this project.

## The TA-Lib C library comes first

`TA-Lib` is a thin Python wrapper around a native C library, and `pip` cannot install the C part.
The wrapper fails to build if the library is missing, so install it before the requirements.

=== "Debian and Ubuntu"

    Take the newest source release from
    [the TA-Lib releases page](https://github.com/ta-lib/ta-lib/releases), then build it.

    ```bash
    sudo apt-get install build-essential
    tar -xzf ta-lib-<version>-src.tar.gz
    cd ta-lib-<version>
    ./configure --prefix=/usr
    make
    sudo make install
    ```

=== "macOS"

    ```bash
    brew install ta-lib
    ```

Everything else in `requirements.txt` is a pure Python wheel or ships its own binaries.

## Installing the library

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
```

`pip install -e .` is an editable install. It reads `pyproject.toml`, installs the seven packages
the library actually imports, and then points the environment at `src/tradingmachine` where it
sits rather than copying it, so an edit to a source file takes effect the next time you import it
without reinstalling anything.

The library declares only what it imports: `requests`, `pymongo`, `python-dotenv`, `pandas`,
`numpy`, `TA-Lib` and `backtesting`. Anyone installing the library gets those and nothing else.

### Installing a user of the library

If you only want to use Trading Machine from your own project, install it from a checkout without
the `-e`, and nothing from this repository has to be on your import path.

```bash
python3.14 -m pip install /path/to/tradingmachine
```

### The development environment

`requirements.txt` is a fully pinned freeze of the working environment, and it is much larger than
the library's own dependency list. It describes where the project is going as much as where it is:
`streamlit`, `Flask` and `textual` for interfaces, `redis`, `psycopg2-binary`, `SQLAlchemy` and
`peewee` for storage, and `yfinance`, `beautifulsoup4`, `selenium` and the websocket libraries for
market data from outside UBI. Install it when you want that whole environment reproduced.

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e . --no-deps
```

Two optional extras are declared in `pyproject.toml` for the pieces that are not library code.
`docs` holds the MkDocs toolchain and `development` holds `ruff` and `build`.

```bash
.venv/bin/python -m pip install -e ".[docs,development]"
```

## Checking that it worked

```bash
.venv/bin/python -c "import talib; print(talib.__version__)"
.venv/bin/python -c "import tradingmachine; print(tradingmachine.__version__)"
```

The first is the one that fails when the C library is missing, with an error about a missing
`ta_libc` symbol or a missing header rather than a missing Python package, which is a confusing
message the first time you see it.

## Linting and formatting

`ruff` is the only quality tool the project uses. It is pinned in `requirements.txt` and is also
the `development` extra in `pyproject.toml`. There is no `ruff.toml` and no `[tool.ruff]` section,
so it runs on its defaults.

```bash
.venv/bin/ruff check .
.venv/bin/ruff format .
```

!!! note "There is no test suite yet"

    `pytest` is not in `requirements.txt` and is not installed, so it has to be added before any
    test can run. Testing this project against UBI is not free of consequences either: as the
    [pitfalls](../contributing/pitfalls.md) page explains, exercising the order routes means
    placing real orders at a real broker.

## The documentation toolchain

The documentation packages are pinned in `requirements.txt` alongside everything else, and they are
also the `docs` extra in `pyproject.toml`, so either install is enough to build this site.

```bash
.venv/bin/mkdocs serve
.venv/bin/mkdocs build --strict
```

See [Writing docs](../contributing/documentation.md) for how the site is put together.
