# data/mapping/flattrade.py

Ported from UBI's `back_office/instruments_v2/adapters/flattrade.py`, classification side only. The rules file is `rules/flattrade.yaml`.

## The fetch is part of the classification

This is the first adapter to override `read_raw_rows`, the base class hook for exactly this case, and it uses it for two things at once.

**Duplicate series.** Around 884 NSE symbols are listed twice, once under EQ and once under BE, and the EQ row should win. The rows are read with the EQ rows last, so the run's own last-write-wins collapse onto one instrument id prefers them. No separate dedup pass is needed.

**Blank-exchange recovery.** About 101 rows ship with both exchange and instrument blank — a gap in Flattrade's own file, confirmed present on the 2026-09-04 snapshot. Their tokens are matched against the BSE equity token space of Dhan and Stoxkart, whose files are complete and which share the same exchange-assigned numbering, and almost all are recovered as real BSE equities. They are read separately, tagged with a flag column, and placed **first**, so a symbol present in both batches keeps its real row rather than the recovered one. Getting that order backwards silently gives a handful of symbols the wrong token.

## The three-way split

An NSE EQ or BE row, or a BSE A or B row, is one of three things: a plain equity, a real exchange traded fund, or a fund to leave alone. Nothing in the row says which. It is decided by cross-broker allowlists, and it is a priority decision between two segments matching the same predicate, which is why it lives here rather than in the rules.

## The two data faults

BSE option rows mis-round half-point strikes: a real 102.5 is reported as 103.0. The true value is re-extracted from the trading symbol, whose suffix carries the strike exactly. And Flattrade's file has no tick size column at all, so `tick_size` in the rules points at a column that does not exist and resolves to nothing for every segment — deliberate, and preferable to pointing it at an unrelated column and nulling it afterwards.

## Verified counts

On the 2026-09-04 snapshot this adapter classified 148,867 of 149,081 raw rows into 148,183 distinct instruments — the difference being the EQ and BE duplicates collapsing — with 214 uncategorised and no errors. Its BSE equity count of 4,898 sits above the roughly 4,725 the other brokers report, which is the recovered rows showing up.
