# src/tradingmachine/ubi_client/prices_document.py

`PricesDocument` keeps UBI's whole answer from `/api/instruments/prices`. It was added on 2026-09-26 for instruments_explorer, whose chart route passes UBI's `price_basis`, `adjustable`, `source` and `to` on to the browser: the chart labels adjusted and unadjusted prices, and uses `to`, the last day UBI actually read, to trim the extra warm-up history it asked for so indicators have values from the first candle shown. `Instrument.prices` returned only a DataFrame and dropped all of that.

`frame` holds the DataFrame code that used to be inside `Instrument.prices`, moved without change: the `time` column renamed to `datetime` and converted to India time, `exchange`, `segment` and `interval` inserted at the front, sorted by time, index reset. On 2026-09-26 the old and the new code were run on nine prices documents (four real ones read from UBI, including adjusted, unadjusted, an index and a commodity future, and five synthetic ones) and `pandas.testing.assert_frame_equal(..., check_exact=True)` found them identical.

Two small differences from the old code, both only for malformed answers: a missing `candles` key now counts as empty and gives None, where the old code raised `KeyError`, and a missing `columns` key gives an empty column list.

`document` is the very dict UBI answered with, not a copy, so a caller that passes it on sends exactly what UBI sent.
