# data/mapping/shoonya.py

Ported from UBI's `back_office/instruments_v2/adapters/shoonya.py`, classification side only. The rules file is `rules/shoonya.yaml`.

## No ISIN, so the identity is borrowed

Shoonya's file carries no ISIN column. Both fixed income segments therefore take their identity from `security_id_to_isin`, the cross-broker map that pools the ISIN-bearing brokers' files for the same date and is keyed on the exchange-assigned security identifier that Shoonya's `token` shares. A row the map cannot resolve is left uncategorised rather than written under its ticker: a ticker-keyed bond identity would never converge with the same bond seen through Dhan or Kotak, which is the precise failure the whole design exists to prevent.

## Checks that must precede the rules

Genuine exchange traded funds sit inside the same instrument codes as plain equities, so both fund segments are decided by cross-broker name allowlists checked before the rules engine runs. NSE bonds are matched by a code list, a blank code, or a code beginning with N, Y, or Z — a condition with no equality-rule equivalent — and are also checked first.

## The stale BSE symbol column

BSE derivative rows carry a `symbol` column that does not track renames, so the underlying is extracted from the trading symbol instead. Three patterns are needed rather than one: index options allow a weekly expiry code where stock options have a month name.

## Expiry

Every derivative segment names the `day_month_name_year_date` transform for its `DD-MON-YYYY` expiry text. UBI applied the equivalent parse generically in code; stating it per segment in the rules keeps the format visible where the column is read.

## Verified counts

On the 2026-09-04 snapshot this adapter classified 162,157 of 162,247 raw rows, leaving 90 uncategorised and no errors — the lowest uncategorised share of any broker in the build.
