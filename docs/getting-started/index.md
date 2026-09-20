# Getting started

Four things have to be true before an instrument object can be built, and they are independent of
each other, so it is worth checking them in order.

1. The Python environment exists and the packages are installed, including the TA-Lib C library
   that the analysis methods sit on. See [Installation](installation.md).
2. The `.env` file holds the UBI base url and the MongoDB credentials, which is everything
   `utilities.configuration` reads. See [Configuration](configuration.md).
3. The database containers are up, because the UBI client reads its api key and secret out of this
   project's MongoDB. See [Data stores](data-stores.md).
4. The sibling project `unified_broker_interface` is running on `http://127.0.0.1:8080` with at
   least one broker logged in, because every price and every order comes from there.

## The shortest thing that proves it all works

```bash
docker compose up -d
PYTHONPATH=. .venv/bin/python -c "
from assets import equities
infosys = equities.Equity(exchange='nse', symbol='INFY')
print(infosys)
print(infosys.last_price())
"
```

The first line of output is the instrument's identity, which means the lookup through UBI
succeeded and the credentials are right. The second is a live price, which means at least one
broker that serves quotes is logged in on the UBI side.

!!! note "`PYTHONPATH=.` is not optional"

    Imports in this project use full package paths, such as `from assets import equities`, so the
    project root has to be on the import path. The `.env` file sets `PYTHONPATH` for tools that
    read it; a bare `python` invocation from a shell needs it given explicitly.

## What to read next

| If you want to | Read |
| --- | --- |
| Understand what an instrument object is and is not | [The instrument model](../architecture/instrument-model.md) |
| Know what UBI carries for a given family | [Asset classes](../asset-classes/index.md) |
| Fetch candles or a quote | [Candles and quotes](../guides/prices-and-quotes.md) |
| Run indicators over the candles | [Analysis](../guides/analysis.md) |
| Place, change or cancel an order | [Orders](../guides/orders.md) |
