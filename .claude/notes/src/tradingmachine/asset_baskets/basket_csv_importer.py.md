# src/tradingmachine/asset_baskets/basket_csv_importer.py

The user chose on 2026-09-28 a generic CSV importer now, with scripts in `bin/` to download constituents and weights later, and those scripts are meant to call this importer rather than write to MongoDB themselves.

## Columns

Only `symbol` is required, or `instrument_id` instead. Column names are lower-cased and stripped, so the NSE's constituent files, whose headers are `Company Name, Industry, Symbol, Series, ISIN Code`, import without editing; their extra columns are ignored. A row's `exchange` and `segment` default to the arguments, `nse` and `equities`, because most files list one exchange's shares.

## Weights

The NSE's free constituent files carry no weights; weights are in the monthly factsheet PDFs. A file without a `weight` column therefore makes an equally weighted index and is stored with `weighting` set to `equal`, so the missing weights are visible in the document rather than silently assumed. A weight may be a fraction or a percentage, with thousands separators or a trailing `%`, because every basket normalises its weights. A file that gives a weight or a quantity to only some rows is refused, because filling the gaps would be a guess.
