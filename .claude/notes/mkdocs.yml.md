# mkdocs.yml

This file configures the project's documentation site, built with Material for MkDocs from `docs/`. It was added on 2026-09-20 at the user's request to mirror the sibling project `unified_broker_interface`, whose own `mkdocs.yml` it was adapted from. The theme, the markdown extension list, the plugin stack and the mkdocstrings options are the sibling's, with the site name, the palette colour, the logo icon, the watched packages and the navigation changed for this project.

## What was kept from the sibling and what was changed

| Setting | Sibling | Here | Why |
|---|---|---|---|
| `site_name` | Unified Broker Interface | Trading Machine | |
| `palette` primary and accent | deep orange | deep orange | Teal until the rebuild of 2026-09-26, when the user chose to match the sibling so both sites and the user's diagram palette are one family |
| `theme.icon.logo` | `material/swap-horizontal-bold` | `material/chart-line` | The sibling normalises between brokers; this project analyses prices |
| `watch` | `stock_brokers`, `utilities` | `src` | This project's one package tree |
| `site_url`, `repo_url`, `edit_uri` | set | set | Both sites are published on GitHub Pages, and the repository link gives every page an edit button |
| `inherited_members` | `true` | `false` | See below, this is the one substantive difference |

The sibling's `mkdocs.yml` carries explanatory comments. They are left out here, because this project does not put explanatory comments in configuration files; their content is in this note instead.

## Why `inherited_members` is false

This is the only mkdocstrings option that differs from the sibling, and it is not a matter of taste.

`tradingmachine.assets.instruments.Instrument` inherits thirteen analysis classes, which is about 190 methods, and all twenty-seven classes in the six family modules inherit from it. With `inherited_members: true`, every one of those classes reprinted the whole analysis surface on its own reference page.

Measured on 2026-09-20, on the same content:

| `inherited_members` | Whole site | Build time | Largest page |
|---|---|---|---|
| `true` | 151 MB | 112 seconds | 23.8 MB, `src/tradingmachine/assets/fixed_income` |
| `false` | 13 MB | 5.9 seconds | 1.0 MB, `src/tradingmachine/assets/analysis/candlestick_patterns` |

A 24 MB HTML page is not usable in a browser, so the setting was turned off. The analysis methods are still documented once each, on the `src/tradingmachine/assets/analysis/*` pages where they are defined, and each class page names its base classes, so nothing is lost except the repetition.

The sibling can afford `true` because its classes have shallow inheritance.

## Why `returns_named_value` is false

Kept from the sibling, and needed for the same reason. Docstrings in both projects write `Returns:` followed by a type, such as `A pandas.DataFrame sorted by time ...`. Griffe's Google parser would otherwise read the leading words as a value's name, decide the return has no type, and warn. Under `--strict` that warning fails the build.

## What the `src/` layout changed

Three entries moved when the project became an installable library on 2026-09-20, and a strict build fails if any of them is wrong.

| Setting | Before | After |
|---|---|---|
| `hooks` | `scripts/documentation_hooks.py` | `scripts/documentation_hooks.py` |
| `gen-files` `scripts` | `scripts/gen_ref_pages.py` | `scripts/gen_ref_pages.py` |
| mkdocstrings `paths` | `[.]` | `[src]` |
| `watch` | `assets`, `unified_broker_interface`, `utilities` | `src` |

`paths: [src]` is the one that is easy to get wrong. It is the import path mkdocstrings resolves an identifier such as `tradingmachine.assets.equities` against. Leaving it at `[.]` happens to keep working while the library is installed editable, because the identifier then resolves through the installed package instead, and it fails on a machine where it is not installed. Naming `src` makes the build depend on the source tree rather than on the state of the environment.

## Why there is a `hooks` entry

`scripts/documentation_hooks.py` silences one griffe warning that this project's docstring convention provokes. The reasoning is in `.claude/notes/scripts/documentation_hooks.py.md`.

## The charts plugin

`mkdocs-charts-plugin` renders ```` ```vegalite ```` fences as Vega-Lite charts, and the three `extra_javascript` entries load vega, vega-lite and vega-embed from jsdelivr, which the plugin needs in the browser. The `vega_theme_light` and `vega_theme_dark` options make the charts follow the palette toggle. Both the plugin and `pymdown-extensions` are pinned in the `docs` extra of `pyproject.toml` at the versions the sibling uses.

## The navigation

The site was rebuilt from scratch on 2026-09-26, following the sibling's rebuild of the day before. It has seven tabs plus the generated reference, and the Python API tab sits second from the left, laid out like Zerodha's Kite Connect documentation, because it is what a reader of a library comes for. The old Pitfalls and Known issues pages were not carried over, at the user's choice; they survive in git history at `b5761c0`.

`- API reference: reference/` with a trailing slash rather than a list of pages is what hands that section to `mkdocs-literate-nav`, which reads the `reference/SUMMARY.md` that `scripts/gen_ref_pages.py` writes during the build.

MkDocs logs `Doc file 'index.md' contains an unrecognized relative link 'reference/'` at INFO level on every build, because that link points at a directory the generator creates rather than at a file on disk. It is informational and does not fail `--strict`.

## Verified on 2026-09-20

`mkdocs build --strict` completed with no warnings, producing 53 HTML pages, of which 26 are generated reference pages: fourteen for `tradingmachine.assets.analysis`, seven for the rest of `assets`, two for `ubi_client`, one for `tradingmachine.utilities.configuration`, plus the literate-nav summary and the section index. `ruff check` and `ruff format --check` pass on the two new Python files.
