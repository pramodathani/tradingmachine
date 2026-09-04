# data/mapping/indmoney.py

Ported from UBI's `back_office/instruments_v2/adapters/indmoney.py`, classification side only. The rules file is `rules/indmoney.yaml`.

## A deliberate deviation from UBI: this project's file has ISINs

UBI's IND Money download carried no ISIN column at all, so its adapter leaned on three cross-broker lookups to compensate: a shared security identifier to ISIN map to give the bond segments an identity, and two name allowlists to detect fund contamination in the equity segments.

This project's IND Money download captures the `isin` column, and it is populated on **every** cash-market row — verified on the 2026-09-04 snapshot, where all 22,640 rows in segment E carry one and the 80,000 without are derivatives, which need none. So this adapter reads the row's own ISIN instead: fixed income is identified and named by it, and fund contamination is detected by its INF prefix. Three cross-broker dependencies disappear, and the identity comes from the row rather than from another broker's file.

The two exchange traded fund allowlists are kept. An ISIN says a row is a fund; it does not say whether that fund is a listed exchange traded fund or a mutual fund scheme, and no column in this file does either.

## Classification by exclusion

An index row is anything whose `segment` is neither `E` nor `D`, with the seven government securities index names excluded — those are bond indices, and no broker in this build covers that segment. The name in that column is then resolved to the canonical symbol through a fixed alias table and, on the NSE side, the day's already-written master index rows, which is why IND Money runs after the index-listing brokers in the processing order.

## The reroutes

An equity row whose symbol the other brokers confirm as an exchange traded fund is redirected to the fund segment rather than dropped. UBI originally dropped them, which left `nse_exchange_traded_funds` permanently empty on the NSE side: the equity rule and the fund condition match the same series list, and the equity rule ran first. A mutual fund row that is actually a confirmed exchange traded fund is dropped from the mutual fund segment to avoid counting it twice.

## Verified counts

On the 2026-09-04 snapshot this adapter classified 102,571 of 102,949 raw rows, leaving 378 uncategorised and no errors.
