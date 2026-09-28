# src/tradingmachine/asset_baskets/mutual_fund_constituents.py

This basket is the only way to measure a mutual fund, because UBI has no quote, no candles and no net asset value for one; `MutualFund.sharpe_ratio` returned None on 2026-09-28, as expected. The basket's weights come from the fund's monthly portfolio disclosure, so they are up to a month old, and the fund's cash, fees and anything UBI cannot price are left out.

`estimated_day_change_percent` multiplies the holdings' weighted day move by one minus `unmapped_weight`, because the unpriced part, mostly cash and money-market instruments, barely moves in a day. It is an estimate, which the name says. Verified on 2026-09-28: with a five-stock stand-in and an unmapped weight of 0.05, the holdings moved -1.688 percent and the estimate was -1.604 percent.
