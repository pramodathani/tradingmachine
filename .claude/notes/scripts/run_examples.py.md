# scripts/run_examples.py

This script runs every example in the documentation against the live UBI and reports which ones work. It was added on 2026-09-29, when the user asked for examples for every property and method and at least two working programs for every class, and chose that all of them, orders included, be run for real rather than as dry runs.

## What it runs

`DocstringExampleCollector` reads every module under `src/tradingmachine` with `ast`, finds each class's and function's docstring, takes the `Examples:` section up to the next section heading, and pulls out every fenced `python` block. Each block is named `<module>.<Class>.<member>#<n>`. `ProgramCollector` lists every `.py` file under `examples/`, named by its path. `--only` keeps the examples whose name starts with the given text, so one member, one class, one module or one program folder can be run.

Each example runs in a fresh interpreter from the project root, a block through `python -c` and a program by its path, so a block cannot lean on state from the one before it.

## Why everything runs one at a time

UBI holds a single access token for the whole application, and every `connect` replaces it, which logs out every other client. Each example is a new process with a new client, so two running at once keep logging each other out, and the client retries only once on HTTP 401. The runner therefore takes an exclusive `fcntl.flock` on `tradingmachine-examples.lock` in the system temporary directory around every run. The lock is shared by every copy of the script, which is what let ten agents write and run examples in parallel on 2026-09-29 without breaking each other's sessions.

## Why some examples are held back

An example that calls `flatten`, `liquidate_all_positions`, `add_to_holdings`, `reduce_holdings`, `liquidate_holdings` or `rebalance` is reported as `held back` and not run unless `--include-account-wide` is given. The first two close every position in the account, the holdings sales sell shares that were there before the example ran, `rebalance` trades the whole portfolio, and `add_to_holdings` on a mutual fund or a bond buys something that cannot simply be cancelled, since a broker may allot a mutual fund unit at the day's net asset value whatever the limit price. The check is a regular expression over the source, so it holds back a program that only mentions such a call too, which errs on the safe side.

## What was learned running the order examples

UBI chooses the broker for every order. An example that buys one share at market and sells one to close nets to zero across the account, but the sell often lands at a different broker from the buy, leaving one broker long and another short intraday until the brokers square off at the close; a closing sell can also be rejected. Examples therefore close positions with `reduce_position` or `liquidate_position`, which send a `quantity_reference` that UBI sizes against the position, and check `net_positions` afterwards.
