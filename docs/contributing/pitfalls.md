# Pitfalls

Things that have caught someone out, collected in one place. Each one is also stated where it
applies; this page is for reading before you start rather than after.

## Testing means placing real orders

!!! danger "There is no dry run except `dry_run=True`"

    Exercising the order routes against UBI sends live orders to a real broker account. There is no
    paper trading mode, no simulator and no sandbox. `place_order(dry_run=True)` asks UBI to build
    the broker's request and hand it back unsent, which is the only rehearsal available, and it does
    not cover the wrappers.

    Where order methods have been checked, it was done by replacing `place_order` with a recorder
    and fabricating a holdings or positions row. The sidecar notes under `.claude/notes/src/tradingmachine/assets/`
    record exactly which orders were recorded and state plainly that none was sent.

## Nothing is validated locally

Prices are not rounded to the tick size and quantities are not checked against the lot size. Both
go to UBI exactly as written. This is a rule rather than an oversight: UBI and the broker behind it
hold those rules, and a check here would duplicate them and then drift.

The practical consequence is that a mistake surfaces as a `BadRequestError` from UBI rather than as
a `ValueError` from this project, and the error message is the authoritative statement of what the
right number was.

## `lot_size` is not the lot an order is measured against

The attribute is the plurality of the brokers' own figures. Orders are measured against UBI's own
contract-size decision, taken each morning from the exchanges' fields. For NSE `USDINR` those two
numbers are 1 and 1000.

Never divide by `lot_size` to compute an order quantity. See
[Currencies](../asset-classes/currencies.md#lot_size-is-not-the-lot-an-order-is-measured-against).

## A quantity means different things in different families

| Family | `quantity` means |
| --- | --- |
| Equities, fixed income, funds, mutual funds | A plain count of units |
| Commodities, currencies | Quotation units, and it must be a whole number of lots |

`quantity=1` on an MCX gold future is refused; `quantity=100` is one lot.

## Having a method does not mean the method works

`Commodity`, `Currency` and `FixedIncome` are all `TradeableInstrument` subclasses, so they carry
`place_order`, the thirty-two price wrappers and the order-book properties. None of those can
succeed, because UBI has no cash market for those asset classes. `hasattr(pair, "bids")` is `True`
while `pair.bids` raises.

The same applies to the analysis methods, which are present on every instrument and have data to
work on for only some of them.

## `None` from `prices` is the normal answer, not an edge case

Whole families have no candles at all: nothing in fixed income or currencies, no investment trust,
no mutual fund. Every analysis method returns `None` in that case, so `frame["rsi_14"]` fails on a
`None` rather than on a missing column.

## `ServiceUnavailableError` often means "no broker carries this"

For a cash bond, a rate index, a commodity, a currency pair or a mutual fund, it is the permanent
answer to `quote`, `last_price`, `ohlc` and every order-book value, not a transient outage.

For a commodity or currency **order**, a 503 means something different again: UBI does not trust
the contract's size today. Read `error.detail["contract_size_status"]` to tell them apart.

## Connecting logs everyone else out

UBI holds one access token for the whole application, so every `connect` replaces the one in force.
That includes UBI's own REST API test page in a browser tab. If a long-running script starts seeing
401s, something else connected.

## `accepted` is not the end of the story

`place_order` returning `outcome: "accepted"` means the broker took the order. The exchange can
still refuse it afterwards, which is what happens to an ordinary order sent while the market is
closed. Neither this project nor UBI checks market hours. Read the order's real fate from
`orders`.

## HTTP 504 means the order may be live

`OrderOutcomeUnknownError` means UBI sent the order and then lost track of it. Read the order book
before sending anything again, or you will place the same order twice.

## Three position products cannot be closed through UBI

A position under `margin_trading`, `cover` or `bracket` is invisible to `add_to_position`,
`reduce_position` and `liquidate_position`. Only `liquidate_all_positions` sees it, and it reports
it as ignored. `positions_value` and `positions_pnl` do count it, because it is still real money.

## The product name changes between reading and ordering

UBI reports a position's product as `delivery`, `intraday` or `carry`, and accepts orders as `cnc`,
`mis` or `nrml`. The position methods translate for you; printing a position row will still
surprise you.

## A holding's profit and loss is shaped differently from a position's

A holding gives `day_change`, `day_change_percentage` and `unrealized`. A position gives
`realized`, `unrealized` and `total`. Code walking both has to branch.

## A bond's symbol is an ISIN

`IN000126C010`, not a ticker. The eighty-odd exceptions on the nse are rate codes such as
`633GS2035`, and those are what the futures and options are written on. Sovereign gold bonds are
in this family rather than with commodities.

## The library has to be installed, not just checked out

The source lives under `src/`, which is deliberately not importable from the repository root. A
checkout you have not run `pip install -e .` in fails at `from tradingmachine.assets import
equities`, and adding the root to `PYTHONPATH` will not rescue it, because there is no
`tradingmachine` directory there to find.

## `.env` is found relative to the working directory, not the library

`Configuration` asks `dotenv` for a file named `.env` in the working directory or one of its
parents. A script run from your home directory therefore gets `None` for the UBI base url and
fails with `UBI base url is not configured`, even though the file exists in the repository. Pass
`Configuration(environment_file=...)` or export the variables instead.
