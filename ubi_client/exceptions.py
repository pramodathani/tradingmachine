"""Errors raised by the Unified Broker Interface client.

Every failed response from the Unified Broker Interface becomes one of the classes below, chosen by the HTTP status code, so callers can catch the base class or one specific failure.

Typical usage example:

  try:
      client.get("/api/users/details")
  except exceptions.NotFoundError as error:
      print(error.message, error.detail)
"""

from typing import Any


class UnifiedBrokerInterfaceError(Exception):
    """A failure reported by, or on the way to, the Unified Broker Interface.

    Attributes:
        message: A str describing the failure, taken from the response's `error` field when it has one.
        status_code: The int HTTP status code of the response, or None when no response arrived.
        detail: The parsed JSON body of the response as a dict, or an empty dict when there was none.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        detail: Any = None,
    ):
        """Initialises the error with its message, status code and body.

        Args:
            message: A str describing the failure.
            status_code: The int HTTP status code of the response, or None when no response arrived.
            detail: The parsed JSON body of the response, of any JSON type, or None when there was none.

        Raises:
            Nothing.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        if detail is None:
            self.detail = {}
        else:
            self.detail = detail


class BadRequestError(UnifiedBrokerInterfaceError):
    """The request was malformed, such as a missing or invalid parameter (HTTP 400)."""


class AuthenticationError(UnifiedBrokerInterfaceError):
    """The api key or secret was wrong, or the access token was missing, invalid or expired (HTTP 401)."""


class NotFoundError(UnifiedBrokerInterfaceError):
    """The requested instrument, profile or order does not exist (HTTP 404)."""


class ConflictError(UnifiedBrokerInterfaceError):
    """The order is no longer pending or open, so it cannot be changed (HTTP 409)."""


class OrderRejectedError(UnifiedBrokerInterfaceError):
    """The broker rejected the order, and the detail holds the order document (HTTP 422)."""


class RateLimitError(UnifiedBrokerInterfaceError):
    """The broker chosen for the order is at its order limit (HTTP 429)."""


class BrokerError(UnifiedBrokerInterfaceError):
    """No broker's data could be read for the request (HTTP 502)."""


class ServiceUnavailableError(UnifiedBrokerInterfaceError):
    """The requested data is stale or not being kept, or no broker can take the order (HTTP 503)."""


class OrderOutcomeUnknownError(UnifiedBrokerInterfaceError):
    """The order was sent but its outcome is unknown, and the detail holds the order document (HTTP 504)."""


class ServerError(UnifiedBrokerInterfaceError):
    """A failure status that has no more specific class, such as HTTP 500 or 405."""


class UnreachableError(UnifiedBrokerInterfaceError):
    """The Unified Broker Interface could not be reached, so no response arrived."""


EXCEPTION_FOR_STATUS_CODE = {
    400: BadRequestError,
    401: AuthenticationError,
    404: NotFoundError,
    409: ConflictError,
    422: OrderRejectedError,
    429: RateLimitError,
    502: BrokerError,
    503: ServiceUnavailableError,
    504: OrderOutcomeUnknownError,
}
