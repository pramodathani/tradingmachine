# data/instruments/fyers.py

Fyers publishes seven public CSV files, one per exchange and segment. None carries a header row, so the twenty-one column names are declared in the module and applied with `names=` as each file is read.

The symbol ticker is unique across all seven files, so it is the natural key on its own.

Fyers publishes `-1.0` as the strike price for instruments that have no strike. That is stored exactly as published rather than converted to a null, in keeping with the landing table holding what the broker actually sent. Interpreting it belongs to the later stage.

Verified on 2026-09-04: 158,943 rows, no duplicates, and the twenty-one declared names matched the files' actual field count.
