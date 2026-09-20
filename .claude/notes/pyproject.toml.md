# pyproject.toml

This file turns the repository into an installable Python library named `tradingmachine`. Before 2026-09-20 it held only a name and a version, and nothing read it; the three packages `assets`, `ubi_client` and `utilities` sat at the repository root and were imported by putting that root on `PYTHONPATH`. The user asked on that date for the project to become a library, and chose each of the decisions recorded below.

## The `src/` layout

All library code moved under `src/tradingmachine`. Two things follow from that, and the second is the point of it.

The three packages became subpackages of one, so every import is a full path from `tradingmachine`. The old names were far too generic to claim on a machine that installs the library: a top-level package called `assets` or `utilities` would collide with anything else that had the same idea.

The repository root is no longer importable. A checkout that has not been installed fails at `from tradingmachine.assets import equities` rather than half-working, which is exactly what is wanted: it makes a packaging mistake visible during development instead of after the wheel is built. Running `pip install -e .` is now a required step, not a convenience.

## hatchling as the build backend

`hatchling` was chosen over `setuptools` because the `src/` layout needs no configuration beyond naming the package directory, and neither backend was already installed in `.venv`, so there was no existing tool to stay consistent with. `pip` fetches the backend into an isolated environment at build time.

`[tool.hatch.build.targets.wheel]` names `src/tradingmachine` so the wheel contains `tradingmachine/` and not `src/tradingmachine/`. `[tool.hatch.build.targets.sdist]` additionally includes `docs`, `scripts` and `mkdocs.yml`, so a source distribution can rebuild the documentation site, which a wheel has no business carrying.

## Dependencies are what the code imports, and nothing else

The user chose on 2026-09-20 to declare only the seven packages the source actually imports, against the alternative of carrying every pin from `requirements.txt` across.

| Declared | Imported by |
|---|---|
| `backtesting` | `src/tradingmachine/assets/analysis/strategy_backtests.py` |
| `numpy` | `src/tradingmachine/assets/analysis/signals.py` |
| `pandas` | Almost every module |
| `pymongo` | `src/tradingmachine/ubi_client/client.py`, to read the api key and secret |
| `python-dotenv` | `src/tradingmachine/utilities/configuration.py` |
| `requests` | `src/tradingmachine/ubi_client/client.py` |
| `TA-Lib` | Twelve of the thirteen analysis modules |

`requirements.txt` has around a hundred pins, most of them for features that do not exist yet: `streamlit`, `Flask` and `textual` for interfaces, `selenium` and `yfinance` for market data from outside UBI, `SQLAlchemy` and `peewee` for storage. Forcing those on anyone who installs the library would be absurd, so the file stays as the pinned development environment and is not referenced from here.

Lower bounds are used rather than exact pins, set to the versions the library was developed against. A library that pins exactly cannot be installed alongside anything else, and the reproducible environment is what `requirements.txt` is for.

Two extras cover the parts that are not library code. `docs` holds the MkDocs toolchain, pinned exactly because a documentation build is reproducible work and the versions are known to produce a clean strict build. `development` holds `ruff` and `build`.

## What is deliberately absent

There is no `LICENSE` file and no `license` field. One was drafted as MIT and removed again, because choosing a licence is the user's decision and not a packaging detail. Until one is added, the library is not safe to publish.

There is no `[tool.ruff]` section. `ruff` runs on its defaults, including its 88-character line length, and the tree is already formatted to that. Setting the project's 80-character rule here would reformat every file for no benefit.

There is no `[project.scripts]` entry, because the library has no command line interface.

`requires-python` is `>=3.14` and matches the virtual environment. Nothing in the source needs 3.14 specifically; the bound simply records what it has been run on.
