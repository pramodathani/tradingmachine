"""UBI's access token and its expiry, as UBI stores them or as its connect route answers.

Typical usage example:

  login = StoredLogin.from_document({"access_token": "...", "expires_at": "2026-09-27 08:40:30.859909"})
  if login.is_usable(clock.now(), 30):
      token = login.access_token
"""

import datetime
from typing import Any, Self

TIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
]


class StoredLogin:
    """UBI's access token and when it expires.

    Attributes:
        access_token: The str token, or None after UBI's session was disconnected.
        expires_at_text: The str expiry exactly as UBI wrote it, in local time, or None.
        expires_at_epoch: The float expiry in seconds since the Unix epoch, or None when it is missing or unreadable.
    """

    def __init__(self, access_token: str | None, expires_at_text: str | None):
        """Initialises the login from its token and expiry text.

        Args:
            access_token: The str token, or None.
            expires_at_text: The str expiry as UBI writes it, such as `2026-09-27 08:40:30.859909`, or None.

        Raises:
            Nothing.
        """
        self.access_token = access_token
        self.expires_at_text = expires_at_text
        self.expires_at_epoch = self._parse_expiry(expires_at_text)

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> Self:
        """Builds the login from a stored document or a connect answer.

        Args:
            document: A dict with `access_token` (as stored) or `access-token` (as the connect route answers), and `expires_at`.

        Returns:
            The StoredLogin.

        Raises:
            Nothing.
        """
        access_token = document.get("access_token")
        if access_token is None:
            access_token = document.get("access-token")
        if access_token is not None:
            access_token = str(access_token)
        expires_at = document.get("expires_at")
        if expires_at is not None:
            expires_at = str(expires_at)
        return cls(access_token, expires_at)

    def is_usable(self, now: float, margin_seconds: float) -> bool:
        """Says whether there is a token that stays valid for a while longer.

        Args:
            now: The float current time in seconds since the Unix epoch.
            margin_seconds: The float number of seconds the token must still be valid for.

        Returns:
            A bool that is True when there is a token that expires more than the margin from now.

        Raises:
            Nothing.
        """
        if not self.access_token or self.expires_at_epoch is None:
            return False
        return self.expires_at_epoch - now > margin_seconds

    def __repr__(self) -> str:
        """Describes the login without revealing the token.

        Returns:
            A str with the expiry and whether a token is present.

        Raises:
            Nothing.
        """
        has_token = bool(self.access_token)
        return (
            f"StoredLogin(has_token={has_token}, expires_at={self.expires_at_text!r})"
        )

    @staticmethod
    def _parse_expiry(text: str | None) -> float | None:
        """Reads an expiry written in local time.

        Args:
            text: The str expiry, or None.

        Returns:
            The float expiry in seconds since the Unix epoch, or None when the text is missing or in no known format.

        Raises:
            Nothing.
        """
        if text is None:
            return None
        for time_format in TIME_FORMATS:
            try:
                moment = datetime.datetime.strptime(text, time_format)  # noqa: DTZ007
            except ValueError:
                continue
            return moment.timestamp()
        return None
