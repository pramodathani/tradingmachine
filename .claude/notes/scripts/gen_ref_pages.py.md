# scripts/gen_ref_pages.py

This module builds the API reference section of the documentation site, one page per module, while MkDocs is building. It was added on 2026-09-20 alongside `mkdocs.yml`, adapted from the sibling project's `scripts/gen_ref_pages.py`, and moved from `src/tradingmachine/utilities/` to `scripts/` later the same day when the project became an installable library.

It is build tooling rather than project code, and moving it out of the package is what makes that literally true: it is no longer shipped to anyone who installs the library, and it no longer has to exclude itself from the reference it generates. Nothing imports it; the `gen-files` plugin points at it by path and runs it with `runpy.run_path`, which is why the work is started by a bare `ReferencePageBuilder().build()` at the bottom of the file rather than under an `if __name__ == "__main__":` guard. `runpy.run_path` gives the module the run name `<run_path>`, so such a guard would never fire.

## What it produces

For each `.py` file under `src/tradingmachine`, it writes a one-line page holding the mkdocstrings identifier, such as `::: tradingmachine.assets.equities`, and records the page in an `mkdocs_gen_files.Nav`. At the end it writes that navigation to `reference/SUMMARY.md`, which `mkdocs-literate-nav` reads because `mkdocs.yml` says `- API reference: reference/` rather than listing pages.

Nothing is written into the repository. `mkdocs_gen_files.open` holds the pages in memory for the length of the build, so the working tree stays clean and the generated pages can never drift from the source.

`set_edit_path` points each generated page's edit link at the source file it documents rather than at a file that does not exist. It has no visible effect until `repo_url` and `edit_uri` are set in `mkdocs.yml`, which they are not yet.

## Why it is a class

The sibling's version is a module-level script, with the loop and the conditionals at top level. This one is `ReferencePageBuilder`, with `build`, `_build_page_for` and `_write_navigation`, because this project's standing rule is that behaviour lives in classes rather than in free-standing module-level code. The logic is the same.

## What is skipped, and why

| Skipped | Reason |
|---|---|
| Anything under `__pycache__` | Compiled output |
| An empty `__init__.py` | There is no docstring to render, and mkdocstrings would emit an empty page |
| A dunder module other than `__init__` | Such as `__main__`, which has no public surface |

`EXCLUDED_PARTS` used to list `gen_ref_pages` and `documentation_hooks` as well. Both entries went away when the two files moved to `scripts/`, because a file outside the tree being walked cannot be found in the first place.

`src/tradingmachine/assets/__init__.py`, `src/tradingmachine/assets/analysis/__init__.py`, `src/tradingmachine/ubi_client/__init__.py` and `src/tradingmachine/utilities/__init__.py` are all empty today, so all four are skipped and no subpackage index page appears. `src/tradingmachine/__init__.py` does have a docstring, so `tradingmachine` gets an index page. A subpackage that gains a docstring later will get one without any edit here.

## Two roots, not one

The builder keeps two paths, and the difference matters. `root` is the repository root, which is what `set_edit_path` needs so an edit link reads `src/tradingmachine/assets/equities.py`. `source_root` is `src` under it, which is what the module's dotted path is computed against so the identifier comes out as `tradingmachine.assets.equities` rather than `src.tradingmachine.assets.equities`. Using one path for both was the mistake to avoid when the `src/` layout arrived.

## Adding a package

`PACKAGES` holds the single entry `tradingmachine`, and everything under it appears in the reference on the next build. A second top-level package would be added there, but there is unlikely ever to be one, since the point of the `src/` layout is that the library claims exactly one importable name.
