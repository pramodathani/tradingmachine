# stream/shoonya/verify_stream.py

## Two modes, two different kinds of proof

`--synthetic` builds frames field by field from known values and asserts the decoder returns exactly those values. It needs no network and no market, so it runs on any day at any hour. Its weakness is structural: every byte it reads was written by this same file, so it can only prove the decoder agrees with this file's idea of the format.

`--against-rest` uses the broker as the oracle. It captures live ticks, prices the same instruments through `GetQuotes`, and compares every value the two share. This is what catches a field that both the parser and the synthetic checks are wrong about in the same direction, and it is the only thing that settles the price scale.

## The REST base URL is Shoonya's own, not Noren's usual one

Most Noren deployments serve REST under `NorenWClientTP/`. Shoonya's Python SDK page shows `NorenApi(host="https://api.shoonya.com/NorenWClientAPI/")`, and `login_to_shoonya` in `utilities/broker_login.py` already calls `NorenWClientAPI/GenAcsTok` successfully every morning, so `NorenWClientAPI` is the path with two independent confirmations behind it. `GetQuotes` hangs off the same base.

## `--feed` exists because depth is undocumented

Flattrade's equivalent always captures on the depth feed, because depth is the superset — it carries everything the touchline does plus the five levels a side the quote endpoint also reports — and Flattrade documents depth so there is nothing to hedge.

Shoonya documents no depth feed at all. So a depth capture that comes back empty has two possible causes that matter enormously and look identical: the market is closed, or Shoonya will not serve `d` on this socket. `--feed touchline` is what separates them, and the empty-capture message says so rather than leaving the operator to work it out. The default stays depth, because when it works it compares three times as many values per instrument.

## What the synthetic checks are actually aimed at

Each is aimed at a specific way the decoder could be wrong, not at the happy path:

- **`check_wire_message_type_strings`** pins every message type and wire key to its literal. The builders and the decoder share `packets`'s constants, so a renamed key would leave every other check self-consistent and silently agree with itself. This is the check that would catch Shoonya's `om` being written back to Flattrade's `o`.
- **`check_connection_message_builders`** pins the outgoing messages, because the connection writes what the server reads while the decoder reads what the server writes — the two halves never touch the same code path. It is also where the one known wire difference between the two Noren brokers is pinned: Shoonya's connect message keys the task as `t`, Flattrade's as `ta`.
- **`check_connect_acknowledgement_status`** exercises both documented spellings of success and every spelling of refusal, which is what keeps the deliberately case-insensitive comparison from drifting into accepting a refusal.
- **`check_non_numeric_token_survives`** exists because Shoonya's own subscribe example includes `NSE|NIFTY`. Coercing tokens to integers is a tempting tidy-up that would fail outright on that key, and this is what stops it coming back.
- **`check_last_trade_time_reads_both_forms`** pins that `ltt` decodes from a clock string and from epoch seconds alike, since neither its presence nor its format is documented anywhere for Shoonya.
- **`check_exchange_code_translation`** covers NCX, which no other broker's stream reaches, and pins that mutual funds and fixed income translate to None rather than being subscribed.

## Mutation testing

Thirteen mistakes were planted one at a time and all thirteen were caught: counting `hk` as data, reading the bid prices from the ask keys, scaling by a fixed hundred, initialising never-seen fields as zeros, replacing instead of merging on update, trimming the zero at depth level five, coercing the token to an integer, spelling the order update type as Flattrade's `o`, reading `Not_Ok` as a successful connect, sending the connect task under Flattrade's `ta` key, pointing the socket at Flattrade's host, dropping the NCDEX branch, and feeding mutual funds to the subscription.

Run the mutation exercise with `PYTHONDONTWRITEBYTECODE=1`. A stale `.pyc` silently resurrects the unmutated code and every mutant appears to survive.

## What only a live run can settle

The synthetic battery is complete about the things this file can know. It says nothing about whether the wire behaves as documented, which is the live run's job:

1. Does the connect acknowledgement accept `settings["ucc_code"]` as the uid?
2. Does one `tk` arrive per subscribed scrip, as Shoonya states it should?
3. Does `{"t":"h"}` draw an `hk` back, confirming the undocumented heartbeat?
4. Does a `d` subscribe produce `dk` frames at all?
5. Is the implied price scale one on every exchange code, NCX included?
