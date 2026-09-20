# mkdocs.yml

This file configures the project's documentation site, built with Material for MkDocs from `docs/`. It was added on 2026-09-20 at the user's request to mirror the sibling project `unified_broker_interface`, whose own `mkdocs.yml` it was adapted from. The theme, the markdown extension list, the plugin stack and the mkdocstrings options are the sibling's, with the site name, the palette colour, the logo icon, the watched packages and the navigation changed for this project.

## What was kept from the sibling and what was changed

| Setting | Sibling | Here | Why |
|---|---|---|---|
| `site_name` | Unified Broker Interface | Trading Machine | |
| `palette` primary and accent | indigo | teal | So the two sites are distinguishable at a glance when both are open |
| `theme.icon.logo` | `material/swap-horizontal-bold` | `material/chart-line` | The sibling normalises between brokers; this project analyses prices |
| `watch` | `stock_brokers`, `utilities` | `assets`, `ubi_client`, `utilities` | This project's packages |
| `repo_url` | commented out | absent | Neither project has the remote wired into the site yet |
| `inherited_members` | `true` | `false` | See below, this is the one substantive difference |

The sibling's `mkdocs.yml` carries explanatory comments. They are left out here, because this project does not put explanatory comments in configuration files; their content is in this note instead.

## Why `inherited_members` is false

This is the only mkdocstrings option that differs from the sibling, and it is not a matter of taste.

`assets.instruments.Instrument` inherits thirteen analysis classes, which is about 190 methods, and all twenty-seven classes in the six family modules inherit from it. With `inherited_members: true`, every one of those classes reprinted the whole analysis surface on its own reference page.

Measured on 2026-09-20, on the same content:

| `inherited_members` | Whole site | Build time | Largest page |
|---|---|---|---|
| `true` | 151 MB | 112 seconds | 23.8 MB, `assets/fixed_income` |
| `false` | 13 MB | 5.9 seconds | 1.0 MB, `assets/analysis/candlestick_patterns` |

A 24 MB HTML page is not usable in a browser, so the setting was turned off. The analysis methods are still documented once each, on the `assets/analysis/*` pages where they are defined, and each class page names its base classes, so nothing is lost except the repetition.

The sibling can afford `true` because its classes have shallow inheritance.

## Why `returns_named_value` is false

Kept from the sibling, and needed for the same reason. Docstrings in both projects write `Returns:` followed by a type, such as `A pandas.DataFrame sorted by time ...`. Griffe's Google parser would otherwise read the leading words as a value's name, decide the return has no type, and warn. Under `--strict` that warning fails the build.

## Why there is a `hooks` entry

`utilities/documentation_hooks.py` silences one griffe warning that this project's docstring convention provokes. The reasoning is in `.claude/notes/utilities/documentation_hooks.py.md`.

## The navigation

Five sections plus the generated reference. `- API reference: reference/` with a trailing slash rather than a list of pages is what hands that section to `mkdocs-literate-nav`, which reads the `reference/SUMMARY.md` that `utilities/gen_ref_pages.py` writes during the build.

MkDocs logs `Doc file 'index.md' contains an unrecognized relative link 'reference/'` at INFO level on every build, because that link points at a directory the generator creates rather than at a file on disk. It is informational, does not fail `--strict`, and the sibling logs the same line.

## Verified on 2026-09-20

`mkdocs build --strict` completed with no warnings, producing 53 HTML pages, of which 26 are generated reference pages: fourteen for `assets.analysis`, seven for the rest of `assets`, two for `ubi_client`, one for `utilities.configuration`, plus the literate-nav summary and the section index. `ruff check` and `ruff format --check` pass on the two new Python files.
