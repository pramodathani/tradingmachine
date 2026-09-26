# .github/workflows/docs.yml

This workflow builds the MkDocs site and publishes it on GitHub Pages at `https://pramodathani.github.io/tradingmachine/`. It was added on 2026-09-26, copied from the sibling project's `.github/workflows/docs.yml`, which has published `https://pramodathani.github.io/unified_broker_interface/` since the day before.

## When it runs

| Event | Build | Publish |
|---|:---:|:---:|
| Push to `main` (including a merged pull request) | Yes | Yes |
| Pull request | Yes | No |
| Started by hand from the Actions tab (`workflow_dispatch`) | Yes | Only when started on `main` |

Building on pull requests means `mkdocs build --strict` checks every change for broken links and unresolvable code references before it is merged. The `deploy` job's `if:` keeps a pull request from publishing an unmerged site.

## Why only the documentation packages are installed

This is the one line that differs from the sibling. The sibling greps `requirements.txt` for lines starting with `mkdocs` or `pymdown`. Here the documentation packages are the `docs` extra in `pyproject.toml`, so the workflow reads that list with `tomllib` and installs only it.

It deliberately does not run `pip install ".[docs]"`. That would install the library itself and its dependencies, including TA-Lib, a wrapper around a native C library that GitHub's Ubuntu runner does not have, so the install would fail. The site does not need the library installed: mkdocstrings reads the source files under `src` with griffe instead of importing them (`paths: [src]` in `mkdocs.yml`), `scripts/gen_ref_pages.py` only walks the directory tree, and `scripts/documentation_hooks.py` imports only the standard library.

No Redis, MongoDB, TimescaleDB, `.env`, UBI or broker credential is needed, and none is available to the workflow.

## Permissions and concurrency

`pages: write` and `id-token: write` are what `actions/deploy-pages` needs to publish. `contents: read` is all the build needs. The `pages` concurrency group with `cancel-in-progress: false` lets a running deployment finish, rather than cancelling it halfway when a second push arrives.

## Repository setting

GitHub Pages must be set to deploy from GitHub Actions (Settings → Pages → Source: "GitHub Actions"). Without that, the `deploy` job fails. It was switched on with `gh api -X POST repos/pramodathani/tradingmachine/pages -f build_type=workflow`.
