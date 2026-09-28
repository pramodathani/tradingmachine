# src/tradingmachine/asset_baskets/exchange_traded_fund_constituents.py

The user asked on 2026-09-28 for a way to fold the existing `ExchangeTradedFund` together with the new basket. The chosen design keeps them as two classes linked both ways: `ExchangeTradedFund.constituents` returns this basket, and this basket's `fund` is the ETF. The name `...Constituents` avoids clashing with the instrument class's name and says what the class is.

## Premium or discount needs an iNAV row

An ETF's indicative net asset value is published by the exchange, and UBI carries some as index rows with names such as `HANGSENG BEES-NAV`. A search of the nse equity indices on 2026-09-28 found none for NIFTYBEES, so `premium_or_discount` could not be checked live; it returns None whenever the fund, the iNAV row or either price is missing. The iNAV row's id is stored with the basket as `indicative_net_asset_value_instrument_id`.

## Tracking difference

`tracking_difference` is the fund's cumulative return minus its holdings' over a range. The holdings' return assumes today's weights all through the range, so it drifts from the fund's real history when the fund changed its holdings; the docstring says so. Verified on 2026-09-28 with five NIFTY stocks standing in for NIFTYBEES' holdings: the difference over a year was 0.0952 and the tracking error 0.0681, large because five stocks are a poor copy of fifty, which is the kind of gap the measure exists to show.
