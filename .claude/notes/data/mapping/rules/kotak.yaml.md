# data/mapping/rules/kotak.yaml

Ported from UBI's `back_office/instruments_v2/adapters/rules/kotak.yaml`, reordered into the canonical segment order and with all collections in block style. `raw_table` points at this project's `instruments.kotak`.

## Two expiry epochs on one broker

Kotak reports expiry as an epoch, but not the same epoch everywhere. NSE contracts count seconds from **1980-01-01**, which is what the `kotak_expiry_epoch` transform exists for and why it is named after this broker; BSE and MCX contracts are plain Unix epochs and use `unix_epoch_date`. Mixing the two silently shifts every affected expiry by ten years.

## Two strike scales, one of them per row

Most option strikes divide by ten raised to the row's own `lprecision`, which is two for equity and MCX commodity contracts and four for currency ones. That is why those segments use the `{columns: [dstrikeprice, lprecision], transform: dynamic_precision_strike}` form, which only this broker's adapter implements.

NSE commodity options are the exception: their true scale is always four decimal places even though the row reports a precision of two, so they name the fixed `divide_by_10_thousand` transform instead. Trusting the reported precision there would put every strike out by a factor of a hundred.

## The blank-group rule, made explicit

UBI's file relied on listing order for `bse_equity_indices`: its condition was a bare `pexchseg: bse_cm` with no group filter at all, placed last among the BSE cash segments so every other segment claimed its own group first. The canonical order puts equity indices before the exchange traded funds and investment trusts, which would invert that and let the catch-all steal their rows.

Rather than depend on order at all, this file states the real condition: `pgroup: null`. Kotak stores a genuinely NULL group on exactly those rows — verified on the 2026-09-04 snapshot, where three BSE cash rows have a NULL group and 12,774 have a value — so the rule is both precise and order-independent.

## The constant field form

`nse_commodities` and `nse_currencies` have no usable lot or tick columns at all, so their `broker_fields` use `{constant: null}`, another form only this broker's adapter implements.

## The two rules-free segments

`nse_fixed_income` and `nse_exchange_traded_funds` carry no rules. The first is a negative condition — any NSE cash group not already claimed, with a real non-fund ISIN — and the second shares its condition exactly with `nse_equities` and is separated from it only by the ISIN prefix. UBI expressed the first as a deliberately unreachable placeholder rule; here an empty rules list says the same thing plainly.
