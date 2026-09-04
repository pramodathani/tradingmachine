# data/instruments/shoonya.py

Shoonya publishes seven public ZIP archives, one per exchange, each holding a single comma-separated text file. Each archive is fetched with `requests`, opened with `zipfile`, and the member read as CSV.

## The per-exchange files have different columns

The cash files carry seven columns, the equity derivative files ten, the commodity files eleven and the currency file twelve. Stacking them produces the union of thirteen, with nulls where a file did not have that column. Nothing is lost; the exchange column already says which shape each row came from.

## Provenance columns

Each row carries `source_zip_url` and `source_file_name`, naming the archive and the member inside it the row came from. The exchange column narrows a row to one of seven shapes but not to one specific file, and the historical snapshots imported from `unified_broker_interface`'s database came with these two columns filled, so the table gained them and the download populates them to keep future days shaped the same.

## Decoded as latin-1

Latin-1 never fails on a byte sequence, and the content is plain ASCII in practice, so a single decoding attempt replaces the encoding fallback chain this would otherwise need.

## Trailing delimiters

Every one of the seven files ends its lines with a trailing comma, producing four distinct empty artifact columns once the differing widths are stacked. The base class drops all four after confirming each is empty.

Flattrade and Shoonya both sit on the Noren platform. They are deliberately kept as two separate modules rather than sharing one implementation.

Verified on 2026-09-04: 162,247 rows after dropping four artifact columns and 20 duplicates.
