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

## The recovery bug that reading twice caused

The first version of `read_raw_rows` read the blank-exchange rows a second time as their own frame, tagged that copy, and concatenated it in front of the main one — the shape UBI used. That puts every blank-exchange row through the classification **twice**: once as the tagged copy, which recovers correctly into `bse_equities`, and once as the untagged original still sitting in the main frame, which has no exchange and therefore falls into the plain `uncategorised` bucket. UBI never saw it because it dropped unclassified rows silently; here they were written and counted, and the verification report's uncategorised profile is what surfaced them.

The fix marks rows in place instead of reading them twice, so each row is classified exactly once. The ordering guarantee that made the concatenation attractive is kept in SQL: blank-exchange rows sort first, then non-EQ rows, then EQ rows last.

Verified on the 2026-09-04 snapshot after the fix: 148,982 raw rows produce exactly 148,982 segment memberships, uncategorised falls from 214 to 115, `bse_equities` still holds all 4,898 rows including the recovered ones, and the plain `uncategorised` bucket holds the 2 blank-exchange rows whose token genuinely is not in the other brokers' BSE token space — 99 of the 101 recovered, which is what UBI reported too.
