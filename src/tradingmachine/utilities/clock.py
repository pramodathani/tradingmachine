"""The source of the current time, replaceable in tests.

Typical usage example:

  now = SystemClock().now()
"""

import time


class SystemClock:
    """The computer's own clock."""

    def now(self) -> float:
        """Reads the current time.

        Returns:
            The float number of seconds since the Unix epoch.

        Raises:
            Nothing.
        """
        return time.time()
