# data/mapping/kotak.py

Ported from UBI's `back_office/instruments_v2/adapters/kotak.py`, classification side only. The rules file is `rules/kotak.yaml`, whose note covers the epoch, strike-scale, and blank-group details.

## Why this adapter extends `_field`

Two field forms exist only for Kotak, so they live here rather than in the shared transform registry: `{constant: <value>}`, which supplies a fixed value where the raw file has no column at all, and `{columns: [...], transform: dynamic_precision_strike}`, which divides the strike by ten raised to a precision read from the row itself. The shared registry holds transforms that take one column and one value; a per-row precision needs two columns, and a constant needs none.

## The ISIN splits

- An NSE cash row whose ISIN is INF-prefixed is a fund, so it is redirected from `nse_equities` to `nse_exchange_traded_funds`. The two segments share the same group list, so no rule can separate them.
- A BSE row in group B whose symbol the other brokers confirm as an exchange traded fund is redirected there. A BSE row with a fund ISIN that is *not* independently confirmed is left uncategorised rather than guessed at.
- `bse_exchange_traded_funds` drops rows whose description begins "INAV" — those are net asset value reference rows, not tradeable funds.
- Both bond segments require a real non-fund ISIN, since the ISIN is the identity.

## Dual membership

`classify_extra` is implemented here, and Kotak is one of only two brokers that need it. UBI ran each segment as an independent, non-exclusive query, so a BSE row could legitimately appear in two segments at once: a group B or F row with a real non-fund ISIN whose symbol is also a confirmed exchange traded fund is genuinely both a security and a fund. `classify` picks the fund as the primary classification, being the more specific signal, and `classify_extra` restores the equity or bond membership rather than silently losing it.

## The trading symbol suffix

Kotak appends the group to its NSE cash trading symbols, so "NBIFIN-EQ" has to become "NBIFIN" before it can converge with the other brokers' plain symbol. This applies to all four NSE cash segments, not only equities — an early version of UBI's adapter stripped it for equities alone, which quietly kept the fund and trust segments from merging across brokers.

## Verified counts

On the 2026-09-04 snapshot this adapter classified 187,006 of 187,397 raw rows, leaving 391 uncategorised and no errors. Its per-segment counts track Dhan's closely across the equity, currency, and commodity families, which is the expected shape: both brokers list the same exchanges in similar depth.
