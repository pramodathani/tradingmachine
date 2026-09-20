# scripts/documentation_hooks.py

This module exists for one reason: to stop a single griffe warning from failing `mkdocs build --strict`. It was added on 2026-09-20 with the rest of the documentation toolchain. The sibling project has no equivalent, because it does not share the docstring convention that provokes the warning.

## The warning

Every docstring in this project carries a `Raises:` section, and a member that raises nothing says so with the single word `Nothing.`:

```python
    Raises:
        Nothing.
```

Griffe's Google-style parser expects every line of a `Raises:` section to be an `exception: description` pair, so it logs:

```
WARNING -  griffe: src/tradingmachine/assets/instruments.py:477: Failed to get 'exception: description' pair from 'Nothing.'
```

Sixteen docstrings in the project are written this way, of which four are on public members that the reference renders, so four warnings were produced and `--strict` aborted the build.

## Why the warning is filtered rather than the docstrings changed

The convention is the user's, it is applied consistently across `assets`, `ubi_client` and `utilities`, and it satisfies the project's own rule that every docstring has a `Raises:` section. Rewriting sixteen docstrings to suit a parser would be changing the source to please the documentation build, which is the wrong way round. Dropping `--strict` instead would give up the check on broken cross-references, which is the main thing `--strict` is worth having for.

So exactly one message is filtered, matched by its text, and every other warning still fails a strict build.

## Why the filter goes on handlers and not on a logger

This was got wrong on the first attempt and is worth recording.

A filter added to a logger only sees the records logged through that logger. Griffe's messages are logged through a logger that mkdocstrings names, under `mkdocs.plugins.`, and they reach MkDocs's output by propagating up. Propagation skips ancestor loggers' filters and runs only their handlers, so a filter on the `mkdocs` logger would never see them. A filter on a handler does see everything that reaches it.

The first attempt added the filter to the root logger's handlers, and nothing changed, because MkDocs attaches both its stream handler and its `CountHandler` warning counter to the `mkdocs` logger rather than to the root logger. `FILTERED_LOGGER_NAMES` therefore covers both `mkdocs` and the root, so the hook keeps working if that ever moves.

## How MkDocs runs it

`mkdocs.yml` lists the file under `hooks:`. MkDocs imports it as a module and calls any module-level function named after a build event. `on_config` is the one used here, because it runs long before mkdocstrings renders anything, and it returns the config unchanged.

`on_config` is a free-standing function, which this project otherwise avoids, because the plugin API requires a module-level name. It is kept to two statements that create a `DocumentationHooks` and call its `install` method, in the same spirit as an `if __name__ == "__main__":` block that only builds the application object.

## Verified on 2026-09-20

Before the hook, `mkdocs build --strict` aborted with four warnings. After it, the build completed with none, and no other warning was suppressed: adding a deliberate broken cross-reference still failed the build.
