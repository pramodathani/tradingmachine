# data/instruments/wisdom_capital.py

Wisdom Capital serves its master through a public POST endpoint on Symphony Fintech's platform, one call per exchange segment across nine segments. No authentication.

## The response shape

The response is JSON whose `result` field holds pipe-delimited text with no header line. The number of fields depends on the row: equities carry twenty-two, options twenty-three, futures twenty-one. The module holds all three header lists and decides per row, using the instrument type in field three and the series in field six.

A `data_category` column records which shape each row was parsed as, so a later stage can tell how a row was interpreted rather than having to re-derive it.

## Why lines are padded or rejoined

A description containing a pipe character splits into more fields than its shape expects. `pad_or_join_fields` joins the surplus back into the final field rather than dropping it, and pads a short line with empty strings, so no line is discarded for being the wrong width.

Verified on 2026-09-04: 209,385 rows across twenty-eight columns, the union of the three shapes plus `data_category`.
