# Installation

The project runs on Python 3.14 in a virtual environment at `.venv/` in the repository root. Every
command below uses that interpreter directly rather than a system-wide one, which is the
convention throughout this project.

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

## The virtual environment

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

`requirements.txt` is a fully pinned list, so the environment is reproducible. It includes far
more than the code currently imports, because the dependency list describes where the project is
going as much as where it is: `streamlit`, `Flask` and `textual` for interfaces, `redis`,
`pymongo`, `psycopg2-binary`, `SQLAlchemy` and `peewee` for storage, and `yfinance`,
`beautifulsoup4`, `selenium` and the websocket libraries for market data from outside UBI. What is
actually imported today is `requests`, `pymongo`, `python-dotenv`, `pandas`, `numpy`, `TA-Lib` and
`backtesting`.

## Checking that it worked

```bash
.venv/bin/python -c "import talib; print(talib.__version__)"
.venv/bin/python -c "import backtesting, pandas; print(pandas.__version__)"
```

The first is the one that fails when the C library is missing, with an error about a missing
`ta_libc` symbol or a missing header rather than a missing Python package, which is a confusing
message the first time you see it.

## Linting and formatting

`ruff` is pinned in `requirements.txt` and is the only quality tool the project uses. There is no
`ruff.toml`, so it runs on its defaults.

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

The documentation packages are pinned in `requirements.txt` alongside everything else, so a plain
install of the requirements is enough to build this site.

```bash
.venv/bin/mkdocs serve
.venv/bin/mkdocs build --strict
```

See [Writing docs](../contributing/documentation.md) for how the site is put together.
