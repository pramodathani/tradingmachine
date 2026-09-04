# data/mapping/segments.py

## Where the vocabulary comes from

The segment list is ported from `unified_broker_interface`'s `back_office/instruments/master/schema.py` (`SEGMENTS` and `EXCHANGES`), which UBI v2 treated as the single source of truth for its segment vocabulary. The names and shapes are unchanged; what is new here is the enforcement of ordering and the exchange-prefixed values.

## The ordering is a user decision

The user asked that segments in every rules YAML be listed by asset class first — fixed income, equities, currencies, commodities — and within each class by kind: simple instruments, futures, options, indices, index futures, index options. UBI's own `SEGMENTS` list already happens to be in exactly this order, so the canonical order and UBI's list order agree; the difference is that here `segment_rank` makes the order a hard requirement that `BrokerMappingAdapter._validate_config` enforces at adapter-load time, rather than a convention.

Order matters beyond readability: `classify()` is first-match-wins over the segments in file order, so the file order is the matching precedence. The ordering is safe because where rules overlap, fixed-income rules are narrower than equities rules and specific-before-general is preserved throughout.

## Prefixed values, bare names in the lists

`CANONICAL_SEGMENTS` holds bare names (`equities`), and `segment_value` builds the exchange-prefixed form (`nse_equities`) that is stored in `instruments.master.segment` and used in the rules YAMLs. The user chose the prefixed form to mirror UBI's table-name convention (`master.nse_equities` in v1, `nse_equities` values in v2). The `exchange` column exists in `instruments.master` alongside the prefixed segment, mirroring UBI v2's schema, even though the prefix already encodes it — it keeps exchange filtering direct and it is what the per-shape unique indexes are keyed on.

## `uncategorised` stays in the vocabulary

UBI v1 had an `uncategorised` segment; v2 dropped it and silently discarded unmatched rows. Here it is kept, extended into per-exchange buckets (`nse_uncategorised` and so on) plus the unprefixed `uncategorised` for rows whose exchange cannot be determined. This was the user's design: catch unmatched rows per exchange, and catch exchange-missing rows in one extra category. The consequence to remember: uncategorised identities are keyed on the broker's own symbol, so ids in these buckets will not converge across brokers — inherent, since an unmatched row's real identity is by definition unknown.