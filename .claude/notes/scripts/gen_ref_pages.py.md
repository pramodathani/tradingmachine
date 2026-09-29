# scripts/gen_ref_pages.py

This module builds the API reference section of the documentation site, one page per module, while MkDocs is building. It was added on 2026-09-20 alongside `mkdocs.yml`, adapted from the sibling project's `scripts/gen_ref_pages.py`, and moved from `src/tradingmachine/utilities/` to `scripts/` later the same day when the project became an installable library.

It is build tooling rather than project code, and moving it out of the package is what makes that literally true: it is no longer shipped to anyone who installs the library, and it no longer has to exclude itself from the reference it generates. Nothing imports it; the `gen-files` plugin points at it by path and runs it with `runpy.run_path`, which is why the work is started by a bare `ReferencePageBuilder().build()` at the bottom of the file rather than under an `if __name__ == "__main__":` guard. `runpy.run_path` gives the module the run name `<run_path>`, so such a guard would never fire.

## What it produces

For each `.py` file under `src/tradingmachine`, it writes a one-line page holding the mkdocstrings identifier, such as `::: tradingmachine.assets.equities`, and records the page in an `mkdocs_gen_files.Nav`. At the end it writes that navigation to `reference/SUMMARY.md`, which `mkdocs-literate-nav` reads because `mkdocs.yml` says `- API reference: reference/` rather than listing pages.

Nothing is written into the repository. `mkdocs_gen_files.open` holds the pages in memory for the length of the build, so the working tree stays clean and the generated pages can never drift from the source.

`set_edit_path` points each generated page's edit link at the source file it documents rather than at a file that does not exist. Since the rebuild of 2026-09-26 `mkdocs.yml` sets `repo_url` and `edit_uri`, so every generated reference page carries an edit button that opens its source file on GitHub.

## Why it is a class

The sibling's version is a module-level script, with the loop and the conditionals at top level. This one is `ReferencePageBuilder`, with `build`, `_build_page_for` and `_write_navigation`, because this project's standing rule is that behaviour lives in classes rather than in free-standing module-level code. The logic is the same.

## What is skipped, and why

| Skipped | Reason |
|---|---|
| Anything under `__pycache__` | Compiled output |
| An empty `__init__.py` | There is no docstring to render, and mkdocstrings would emit an empty page |
| A dunder module other than `__init__` | Such as `__main__`, which has no public surface |

`EXCLUDED_PARTS` used to list `gen_ref_pages` and `documentation_hooks` as well. Both entries went away when the two files moved to `scripts/`, because a file outside the tree being walked cannot be found in the first place.

`src/tradingmachine/assets/__init__.py`, `src/tradingmachine/assets/analysis/__init__.py`, `src/tradingmachine/unified_broker_interface/__init__.py` and `src/tradingmachine/utilities/__init__.py` are all empty today, so all four are skipped and get no index page. `src/tradingmachine/__init__.py`, `src/tradingmachine/accounts/__init__.py` and `src/tradingmachine/orders/__init__.py` have docstrings, so `tradingmachine`, `accounts` and `orders` each get an index page. A subpackage that gains a docstring later will get one without any edit here.

## Two roots, not one

The builder keeps two paths, and the difference matters. `root` is the repository root, which is what `set_edit_path` needs so an edit link reads `src/tradingmachine/assets/equities.py`. `source_root` is `src` under it, which is what the module's dotted path is computed against so the identifier comes out as `tradingmachine.assets.equities` rather than `src.tradingmachine.assets.equities`. Using one path for both was the mistake to avoid when the `src/` layout arrived.

## Adding a package

`PACKAGES` holds the single entry `tradingmachine`, and everything under it appears in the reference on the next build. A second top-level package would be added there, but there is unlikely ever to be one, since the point of the `src/` layout is that the library claims exactly one importable name.

## Inherited discovery calls on the family pages, since 2026-09-28

On 2026-09-28 the discovery class methods `expiries`, `contracts`, `strikes` and `chain` moved from the sixteen family derivative classes onto `Futures` and `Option` in `src/tradingmachine/assets/instruments.py`. With the global `inherited_members: false`, they would then have vanished from the pages of `EquityOption` and its siblings, which is where a reader looks for them.

`_directive_for` therefore writes a per-page option for the four family modules named in `FAMILY_MODULES`:

```
::: tradingmachine.assets.equities
    options:
      inherited_members:
        - expiries
        - contracts
        - strikes
        - chain
```

mkdocstrings merges an `options:` mapping under a `:::` line over the global options (`mkdocstrings/_internal/extension.py`), and mkdocstrings-python 1.16.12 accepts a list of names for `inherited_members`, keeping an inherited member only when its name is on the list (`mkdocstrings_handlers/python/_internal/config.py` and `_internal/rendering.py`). So the four names come through and the 190 analysis methods and the new derivative members do not. `Equity` and `EquityIndex` inherit none of the four, so they show nothing extra. Every other module keeps the bare one-line directive.

The inherited members render with the base classes' docstrings, which is why those are written for any family, saying "the class's segment" rather than naming one.

The first build on 2026-09-28 confirmed it. `EquityIndexOption.expiries`, `strikes` and `chain`, `EquityIndexFutures.contracts`, `EquityFutures.expiries` and `EquityOption.chain` all rendered on the equities page, and `EquityIndexOption.relative_strength_index`, `EquityIndexOption.greeks` and `Equity.expiries` did not. The site measured 22 MB against 21 MB for `main` built the same way, and the equities page 404 KB against 380 KB.

## A module named `index`, since 2026-09-28

Adding `src/tradingmachine/asset_baskets/index.py` made `mkdocs build` spin forever at full CPU, with no warning. The builder writes a package's `__init__.py` to `index.md`, and wrote the module `index.py` to `index.md` in the same folder, so two navigation entries pointed at one page. `mkdocs-section-index` then looped in its `on_nav` hook, which a stack dump taken 40 seconds into the build showed. The builder now writes a module named `index` to `index_module.md`, keeping `index` as its title in the navigation. The module kept its natural name, because the problem was the page path and not the module.

The cause was found by bisecting in a temporary worktree of `main`: `main` built in 11.5 seconds, `main` with this branch's `src` did not finish in 100 seconds, `main`'s `assets` with the new package still hung, and a build without `watchlist.py` still hung, which ruled out a name clash in that file.

## The hierarchy layout and the example programs, since 2026-09-29

On 2026-09-29 the user asked for a menu on the right that organises the API by module and class hierarchy, with every property and method in source order, and at least two example programs per class. The user chose the generated API reference as the place for this, over the hand-written Python API tab, after being told that professional sites such as pandas and Pydantic keep the complete hierarchy in a generated reference and the task guides separate.

Each page used to be one `::: module` line at the global `heading_level: 2`, which made the module a second-level heading, each class a third and each member a fourth. `toc_depth` is 3 in `mkdocs.yml`, so the menu on the right listed classes but never their members. The page is now built from one `::: module` line at `heading_level: 1`, with `members` limited to the module's upper-case constants (or `false` when there are none), followed by one `::: module.Class` line per public class at `heading_level: 2`. Members become third-level headings and appear in the menu. Classes are listed in source order, which is always a valid hierarchy order inside one module, because Python requires a base class to be defined before a subclass that names it.

The classes and constants are read with `ast` rather than by importing the module, so the build still needs neither TA-Lib nor UBI. `ModuleSource` does the reading, and `resolve_base` turns a base written as `instruments.TradeableInstrument` into its dotted path through the module's `from ... import` statements.

The per-class directive is what makes room for the example programs, because a single `::: module` line gives no place to insert anything after one class. Each program is included with a `--8<--` snippet line inside a fenced `python` block, so the page shows the file as it is on disk; `pymdownx.snippets` resolves the path against the project root, where `mkdocs build` runs. The title is the first line of the program's module docstring, read with `ast`.

`ClassHierarchyPage` writes `reference/index.md`. A class with exactly one base in the library hangs under it. `Instrument` and `AssetBasket` each inherit all fourteen analysis classes side by side, and hanging them under the first, `PriceStatistics`, would misrepresent them, so a class with several library bases, or none, starts its own branch and names its bases beside it. Links use mkdocs-autorefs identifiers such as `[Equity][tradingmachine.assets.equities.Equity]`, which resolve to the class's heading on its module page.

`mkdocs.yml` also gained `group_by_category: false` the same day. With the default of true, mkdocstrings-python puts attributes, which includes properties, before functions, so `Account.parents` came before `Account.flatten` although the code defines `flatten` first.

The first full build with every example on 2026-09-29 took 20 seconds and made a 51 MB site, against 13 MB before, and the `instruments` page grew to 4.9 MB because it holds about 100 members, each with its source and its examples. `show_source: false` would roughly halve it if that ever matters.
