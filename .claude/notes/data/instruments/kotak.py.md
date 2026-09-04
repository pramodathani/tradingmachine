# data/instruments/kotak.py

Kotak publishes seven public CSV files under a URL path stamped with the day's date. Five sit under `transformed/` and two, the cash market files, under `transformed-v1/`.

## Only today's files exist

Kotak serves these under the current date only, so a backfill of an earlier date is not possible from this source. `download()` therefore takes no date argument and always uses today, which is honest about what the endpoint can do rather than accepting a date it would fail on.

## The header quirks are real

Kotak's own files ship `dTickSize ` and `dPriceNum   ` with trailing spaces and `dStrikePrice;` with a literal semicolon. These are baked into the published header, not a parsing artifact, and were confirmed present in the live files. The base class normalises them to `dticksize`, `dpricenum` and `dstrikeprice`.

## Eighty columns, not seventy-nine

The two `transformed-v1` cash files carry a `surveillanceMessage` column the five derivative files do not, so stacking the seven produces a union of eighty. Eleven columns arrive empty on every row. That was checked against Kotak's own file rather than assumed: `pSubGroup`, `pCombinedSymbol`, `pAmcCode`, `pNav`, `pSipSecurity` and the rest are genuinely empty at source.

## Scientific notation in strike prices

Kotak publishes some strikes as `6.16e+06`. That is what the file literally contains, confirmed by reading the raw CSV directly, not something pandas introduced. Storing as text preserves it.

Verified on 2026-09-04: 187,397 rows after dropping 4 duplicates.
