"""Silences one griffe warning so that `mkdocs build --strict` stays useful.

Every docstring in this project carries a `Raises:` section, and a member that raises nothing says so with the single word `Nothing.`. Griffe's Google-style parser expects every line of a `Raises:` section to be an `exception: description` pair, so it warns once per such docstring, and `--strict` turns each warning into a failed build. The convention is the project's and is not going to change, so the warning is filtered here instead.

Nothing else is suppressed. The filter matches only that one message, and every other warning still fails a strict build.

Typical usage example:

  hooks:
    - utilities/documentation_hooks.py
"""

import logging
from typing import Any

SUPPRESSED_MESSAGE_FRAGMENT = (
    "Failed to get 'exception: description' pair from 'Nothing.'"
)

FILTERED_LOGGER_NAMES = (
    "",
    "mkdocs",
)


class NothingRaisedFilter(logging.Filter):
    """A logging filter that drops griffe's complaint about a `Raises: Nothing.` section."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Decides whether one log record should be kept.

        Args:
            record: The logging.LogRecord to judge.

        Returns:
            A bool that is False for the suppressed griffe warning and True for everything else.

        Raises:
            Nothing.
        """
        return SUPPRESSED_MESSAGE_FRAGMENT not in record.getMessage()


class DocumentationHooks:
    """The MkDocs build hooks this project installs.

    Attributes:
        log_filter: The NothingRaisedFilter added to every handler on the root logger.
    """

    def __init__(self):
        """Prepares the filter that the hooks install.

        Raises:
            Nothing.
        """
        self.log_filter = NothingRaisedFilter()

    def install(self) -> None:
        """Adds the filter to the handlers that MkDocs prints and counts warnings with.

        The filter goes on the handlers rather than on a named logger, because griffe's messages reach those handlers by propagating up from a logger whose name mkdocstrings chooses, and a filter on a logger only sees the records logged through it. MkDocs attaches both its stream handler and its warning counter to the `mkdocs` logger, and the root logger is covered as well in case that changes.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for logger_name in FILTERED_LOGGER_NAMES:
            for handler in logging.getLogger(logger_name).handlers:
                handler.addFilter(self.log_filter)


def on_config(config: Any, **kwargs: Any) -> Any:
    """Installs the hooks when MkDocs has loaded its configuration.

    Args:
        config: The mkdocs.config.defaults.MkDocsConfig being built with.
        **kwargs: The other keyword arguments MkDocs passes to this event, which are not used.

    Returns:
        The config as given, unchanged.

    Raises:
        Nothing.
    """
    del kwargs
    DocumentationHooks().install()
    return config
