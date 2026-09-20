# utilities/gen_ref_pages.py

This module builds the API reference section of the documentation site, one page per module, while MkDocs is building. It was added on 2026-09-20 alongside `mkdocs.yml`, adapted from the sibling project's `utilities/gen_ref_pages.py`.

It is build tooling rather than project code. Nothing imports it; the `gen-files` plugin points at it by path and runs it with `runpy.run_path`, which is why the work is started by a bare `ReferencePageBuilder().build()` at the bottom of the file rather than under an `if __name__ == "__main__":` guard. `runpy.run_path` gives the module the run name `<run_path>`, so such a guard would never fire.

## What it produces

For each `.py` file under `assets`, `ubi_client` and `utilities`, it writes a one-line page holding the mkdocstrings identifier, such as `::: assets.equities`, and records the page in an `mkdocs_gen_files.Nav`. At the end it writes that navigation to `reference/SUMMARY.md`, which `mkdocs-literate-nav` reads because `mkdocs.yml` says `- API reference: reference/` rather than listing pages.

Nothing is written into the repository. `mkdocs_gen_files.open` holds the pages in memory for the length of the build, so the working tree stays clean and the generated pages can never drift from the source.

`set_edit_path` points each generated page's edit link at the source file it documents rather than at a file that does not exist. It has no visible effect until `repo_url` and `edit_uri` are set in `mkdocs.yml`, which they are not yet.

## Why it is a class

The sibling's version is a module-level script, with the loop and the conditionals at top level. This one is `ReferencePageBuilder`, with `build`, `_build_page_for` and `_write_navigation`, because this project's standing rule is that behaviour lives in classes rather than in free-standing module-level code. The logic is the same.

## What is skipped, and why

| Skipped | Reason |
|---|---|
| Anything under `__pycache__` | Compiled output |
| `gen_ref_pages` | This file: it is part of the documentation build, not the project being documented |
| `documentation_hooks` | The same |
| An empty `__init__.py` | There is no docstring to render, and mkdocstrings would emit an empty page |
| A dunder module other than `__init__` | Such as `__main__`, which has no public surface |

`assets/__init__.py`, `assets/analysis/__init__.py`, `ubi_client/__init__.py` and `utilities/__init__.py` are all empty today, so all four are skipped and no package index page appears. A package that gains a docstring later will get one without any edit here.

## Adding a package

The `PACKAGES` tuple at the top is the only thing to change when a new top-level package arrives. Everything under it appears in the reference on the next build.
