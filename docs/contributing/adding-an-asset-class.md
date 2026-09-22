# Adding an asset class

Every family module in `assets` was written the same way, and the next one should be too. The
pattern is deliberately repetitive: `src/tradingmachine/assets/fixed_income.py` is a copy of `src/tradingmachine/assets/equities.py`,
`src/tradingmachine/assets/commodities.py` is a copy of that, and `src/tradingmachine/assets/currencies.py` is a copy of that again.
Nothing was factored out and no existing module was touched when each one arrived.

## Why the duplication is the design

The alternative was offered each time and turned down each time. Lifting the holdings mechanism
onto a base class, the way the discovery mechanism already sits on `Instrument`, would have saved
the free-to-sell arithmetic being written once per holdable family. It would also have meant that
a fact true only of bonds could not be written into the bond file without checking what else
inherits it.

So each family module reads as one self-contained file, and the only mechanism that is shared is
the mechanism that is genuinely identical for every instrument, which lives in
`tradingmachine.assets.instruments`.

## The steps

1. **Find the segments.** They come from UBI's canonical segment list. Take the names exactly as
   UBI spells them, including irregularities: the fixed income cash segment is `fixed_income`, not
   pluralised, and it cannot be tidied because the string is baked into UBI's cash segment list,
   its Redis keys and its instrument table.

2. **Copy the nearest existing module.** Start from `src/tradingmachine/assets/equities.py` if the family is holdable
   and from `src/tradingmachine/assets/commodities.py` if it is not.

3. **Write one class per segment.** Put each on the right base: the index class on
   `NonTradeableInstrument`, everything else on `TradeableInstrument`.

4. **Give each constructor exactly its own identity fields.** A security takes `exchange` and
   `symbol`, a future adds `underlying_symbol` and `expiry_date`, an option adds `strike_price`
   and `option_type`. Never a segment string.

5. **Add a segment constant per segment and one exception class per class**, in
   `src/tradingmachine/assets/exceptions.py`, inheriting `InstrumentError` directly.

6. **Re-raise the not-found error.** Catch `InstrumentError` from `super().__init__` and raise the
   class's own error naming what was looked for, then check that the resolved segment is the
   prefixed name this class owns.

7. **Add holdings only if UBI can report one.** The test is whether the segment is in UBI's cash
   segment list. If it is not, leave the six members out entirely rather than adding ones that
   always return `None`.

8. **Add the discovery class methods** that make sense for each class, each supplying its own
   segment: `search` on the security and index classes, `expiries` and `contracts` on the futures
   classes, `expiries`, `strikes` and `chain` on the option classes.

9. **Write the sidecar note** at `.claude/notes/src/tradingmachine/assets/<module>.py.md`, and verify the whole thing
   against a running UBI.

## Write the empty segments anyway

Four segments in UBI hold no rows at all today, and classes were written for every one of them, so
that each family has the same shape and so that the classes work the moment UBI gains a mapping
rule.

They need no special case, because an empty segment degrades on its own. This is worth checking
rather than assuming:

| Call | Answer on an empty segment |
| --- | --- |
| The constructor | UBI answers 404, which becomes the class's own error |
| `expiries`, `strikes` | `[]` |
| `search`, `contracts`, `chain` | `None` |

A genuinely misspelt segment gives `BadRequestError` instead, which is how you tell the two apart.

## Do not validate locally

It is tempting to reject, in a constructor, an exchange that has no market for the family — UBI
has no commodity market on the `bse`, for instance. That was considered and deliberately not done.

A lookup that UBI has no rows for already raises the class's own error by the ordinary not-found
path, and a local check would duplicate UBI's rules and then drift from them. The same reasoning
covers tick sizes and lot sizes: prices and quantities reach UBI exactly as given. See
[Pitfalls](pitfalls.md).

## The style rules that apply

These are the project's rules rather than anything specific to asset classes, but they are what a
new module will be read against.

- Every function, method and class gets a Google-style docstring with `Args:`, `Returns:` and
  `Raises:`, including the type of each parameter and of the return value.
- No explanatory comments in the source. Reasoning goes into the sidecar note under
  `.claude/notes/`, one file per source file, mirroring the tree.
- Names are spelled out in full: `segment_configuration`, not `seg_cfg`.
- One element per line in a list or dictionary literal, with a trailing comma.
- A sentence in a docstring is never split across lines, even past 80 characters.
- Behaviour lives in classes rather than in free-standing functions.
