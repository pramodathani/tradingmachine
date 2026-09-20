# Errors

There are two exception hierarchies, and which one you catch depends on whether the problem is
UBI's or the instrument's.

| Hierarchy | Base class | Raised by | Means |
| --- | --- | --- | --- |
| `ubi_client.exceptions` | `UnifiedBrokerInterfaceError` | The REST client | UBI answered with a failure, or could not be reached |
| `assets.exceptions` | `InstrumentError` | The instrument classes | The request never reached UBI, or UBI's answer does not support what you asked for |

Both hierarchies are exactly one level deep. Every subclass inherits the base directly, so
catching the base catches everything in that family and there is no middle tier to remember.

## Failures from UBI

Each class matches one HTTP status code, and anything with no match becomes `ServerError`.

| Status | Class | What it usually means |
| --- | --- | --- |
| 400 | `BadRequestError` | A field is wrong: an incomplete lookup, a price on a market order, a quantity that is not a whole number of lots |
| 401 | `AuthenticationError` | The key or secret was refused, or a retried token was refused again |
| 404 | `NotFoundError` | No such instrument, order or broker mapping |
| 409 | `ConflictError` | The request conflicts with the current state |
| 422 | `OrderRejectedError` | The broker refused the order, and its answer is in `detail` |
| 429 | `RateLimitError` | Too many requests |
| 502 | `BrokerError` | The broker failed |
| 503 | `ServiceUnavailableError` | No broker could serve it: no recent quote, no broker able to take the order, or a contract whose size UBI does not trust today |
| 504 | `OrderOutcomeUnknownError` | The order was sent, and nobody knows what happened to it |
| anything else | `ServerError` | Including HTTP 405, which is what a `PATCH` gets today |
| no response at all | `UnreachableError` | A refused connection or a timeout, so nothing was sent |

Every one of them carries three attributes.

```python
from ubi_client import exceptions

try:
    price = contract.last_price()
except exceptions.ServiceUnavailableError as error:
    print(error.message)      # taken from the response's "error" field
    print(error.status_code)  # 503, or None when no response arrived
    print(error.detail)       # the parsed JSON body, or {} when there was none
```

`detail` is where the interesting part usually is. A rejected order carries the broker's own
wording there, and a commodity or currency order refused for its contract size carries a
`contract_size_status` of `conflict`, `undecided`, `no_source` or `single_source`.

!!! danger "`OrderOutcomeUnknownError` is not a failure"

    HTTP 504 means UBI sent the order to the broker and then lost the thread. The order may well be
    live. Read the order book with `orders()` before sending anything again, or you will place the
    same order twice.

## Failures from the instrument classes

`assets.exceptions` has `InstrumentError` and thirty-two subclasses. Five of them are about what
you asked for, and the rest are one per instrument class, raised when that class's own lookup
finds nothing or returns an instrument outside the class's segment.

| Class | Raised when |
| --- | --- |
| `InstrumentError` | UBI has no instrument matching the lookup. It is also the base of every class below |
| `TradeableInstrumentError` | You built a `TradeableInstrument` on an index segment |
| `NonTradeableInstrumentError` | You built a `NonTradeableInstrument` on something that is not an index |
| `OrderError` | A price-named order wrapper has no price to use, because the order book is empty on that side |
| `PositionError` | There is no position to act on, several are held and none was named, or a reduction is larger than the position |
| `HoldingError` | The share is not held, the sale is larger than the free quantity, or the whole holding is pledged |

The twenty-seven remaining classes are one per instrument class, named after it:
`EquityError`, `EquityFuturesError`, `EquityOptionError`, `EquityIndexError`,
`EquityIndexFuturesError`, `EquityIndexOptionError`, and the same six for fixed income,
commodities and currencies, plus `ExchangeTradedFundError`, `InvestmentTrustError` and
`MutualFundError`.

```python
from assets import exceptions
from assets import equities

try:
    share = equities.Equity(exchange="nse", symbol="NOTAREALSYMBOL")
except exceptions.EquityError as error:
    print(error)
```

Because each one names the class that raised it, a traceback says which lookup failed without
anybody having to read the arguments back.

## Catching both

The two hierarchies are unrelated, so code that has to survive either failure catches both bases.

```python
from assets import exceptions as asset_exceptions
from ubi_client import exceptions as ubi_exceptions

try:
    price = instrument.last_price()
except ubi_exceptions.UnifiedBrokerInterfaceError as error:
    ...
except asset_exceptions.InstrumentError as error:
    ...
```

The one place they meet is the constructor. A lookup that UBI answers with HTTP 404 is caught by
`_fetch_details` and re-raised as an `InstrumentError` naming the parameters that found nothing,
because "no such instrument" is a fact about the instrument rather than a transport failure. Every
other status code passes through as the UBI exception it was.
