# data/mapping/rules/wisdom_capital.yaml

Ported from UBI's `back_office/instruments_v2/adapters/rules/wisdom_capital.yaml`, reordered into the canonical segment order and with all collections in block style. `raw_table` points at this project's `instruments.wisdom_capital`. At 46 entries this is the second largest rules file in the project.

## Numeric instrument types

`instrumenttype` is a numeric code stored as text: 1 for futures, 2 for options, 16 for underlying references. Every rule quotes it. The codes carry no information about what the contract is *on*, which is why so much of this broker's separation happens by underlying name.

## Why so many segments have no rules

Fourteen entries carry no rules. They fall into two groups.

The first is the segments UBI separated by listing order alone — the index derivatives, the currency derivatives sharing the rate derivative code, and the MCX index spot rows. The canonical order inverts every one of those pairs, so the general segment now carries the rule and the specific one is reached through the adapter's redirect table. Leaving the specific rule in place as well would be misleading: it would look live while never firing.

The second is the BSE cash-market segments and `nse_fixed_income`, whose real conditions are cross-broker allowlists, ISIN tests, and description suffixes.

## Expiry and strikes

`contractexpiration` is an ISO timestamp, which the generic parser reads correctly, so no transform is named. Option types are numeric codes remapped in the adapter rather than by a transform, since the mapping is a value substitution rather than a scale conversion.

## The segments with no meaningful sizes

`nse_commodities`, `nse_currencies`, `nse_fixed_income_indices`, and the currency-segment half of `nse_fixed_income` name the ordinary lot and tick columns here, and the adapter forces them to nothing: those rows are underlying references rather than tradeable contracts, so whatever the columns contain is not a real lot or tick size.
