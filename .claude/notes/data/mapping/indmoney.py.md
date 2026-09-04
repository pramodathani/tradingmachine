# data/mapping/indmoney.py

Ported from UBI's `back_office/instruments_v2/adapters/indmoney.py`, classification side only. The rules file is `rules/indmoney.yaml`.

## The ISIN, read from the row when there is one and resolved when there is not

UBI's IND Money download carried no ISIN column at all, so its adapter leaned on the cross-broker security identifier map to give the bond segments an identity.

This project's download does capture an `isin` column — but only from **2026-09-02** onwards. Every stored snapshot before that has it entirely empty: 0 of 98,945 rows on 2026-08-27, against 22,640 of 102,949 on 2026-09-04. An earlier version of this adapter read the column directly and treated its absence as "not a bond", which quietly cost 13,900 rows a day on fifteen of the eighteen stored dates, all of them landing in the uncategorised buckets. It looked correct because it was only ever checked against a recent date.

`resolved_isin` now reads the row's own ISIN where there is one and falls back to the shared security identifier map where there is not, and every use goes through it: the bond segments' identity, and the fund-contamination check in both equity segments. On 2026-08-28 that moved IND Money from 85,876 classified and 13,900 uncategorised to 99,391 and 385, which is the same profile as the ISIN-bearing dates, while 2026-09-04 came out unchanged at 102,571 and 378.

The lesson generalises: a broker's file is not the same file on every date, so an adapter verified only against the newest snapshot is only verified for the newest snapshot.

The two exchange traded fund allowlists are kept regardless. An ISIN says a row is a fund; it does not say whether that fund is a listed exchange traded fund or a mutual fund scheme, and no column in this file does either.

## Classification by exclusion

An index row is anything whose `segment` is neither `E` nor `D`, with the seven government securities index names excluded — those are bond indices, and no broker in this build covers that segment. The name in that column is then resolved to the canonical symbol through a fixed alias table and, on the NSE side, the day's already-written master index rows, which is why IND Money runs after the index-listing brokers in the processing order.

## The reroutes

An equity row whose symbol the other brokers confirm as an exchange traded fund is redirected to the fund segment rather than dropped. UBI originally dropped them, which left `nse_exchange_traded_funds` permanently empty on the NSE side: the equity rule and the fund condition match the same series list, and the equity rule ran first. A mutual fund row that is actually a confirmed exchange traded fund is dropped from the mutual fund segment to avoid counting it twice.

## Verified counts

On the 2026-09-04 snapshot this adapter classified 102,571 of 102,949 raw rows, leaving 378 uncategorised and no errors.
