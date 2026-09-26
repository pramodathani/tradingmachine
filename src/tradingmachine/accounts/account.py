"""The whole trading account behind UBI, and the kill switch that empties it.

`Account.flatten` sends `POST /api/orders/flatten`, which cancels every open order at every broker, waits until the brokers confirm the cancellations, and only then closes every position with limit orders. It acts on the whole account, not on one instrument; `TradeableInstrument.liquidate_all_positions` is the per-instrument equivalent.

Typical usage example:

  trading_account = account.Account()
  preview = trading_account.flatten(confirm="FLATTEN", dry_run=True)
  outcome = trading_account.flatten(confirm="FLATTEN")
"""

from tradingmachine.assets import instruments
from tradingmachine.ubi_client import client

FLATTEN_PATH = "/api/orders/flatten"

DEFAULT_FLATTEN_TIMEOUT_SECONDS = 120


class Account:
    """The trading account UBI trades for, across every broker it is connected to.

    Attributes:
        unified_broker_interface: The client.UnifiedBrokerInterface the account's requests are sent through.
    """

    def __init__(
        self,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Initialises the account with the client it sends requests through.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface to use, or None to share the one every instrument uses, which is almost always right because a second client would log the instruments out.

        Raises:
            ValueError: No client was given and the shared client's base url or MongoDB credentials are not configured.
        """
        if unified_broker_interface is None:
            unified_broker_interface = (
                instruments.Instrument.shared_unified_broker_interface()
            )
        self.unified_broker_interface = unified_broker_interface

    def flatten(
        self,
        confirm: str,
        dry_run: bool = False,
        timeout_seconds: float = DEFAULT_FLATTEN_TIMEOUT_SECONDS,
    ) -> dict:
        """Cancels every open order at every broker, then closes every position in the account.

        The cancellations go first and the closes wait for them to be confirmed, because a stop or a target still resting when its position is closed would fill afterwards and open a new position the other way. Positions are closed with limit orders, and each close is reported whether or not it was sent.

        Three things it does not do. It does not disarm UBI's own synthetic orders that are waiting for a price or a time, such as a hidden stop or a grid, so those can still trade afterwards. In engine mode, the broker each close goes to is chosen by UBI rather than taken from where the position is held, so check `broker` in each entry of `closed`. And a timeout does not mean nothing happened: read the orders and positions before calling it again, or a second flatten may close positions twice.

        Args:
            confirm: The str `FLATTEN`, typed by the caller, which UBI requires so that a stray call cannot unwind the account.
            dry_run: A bool that is True to report what would be cancelled and closed without sending anything.
            timeout_seconds: The float number of seconds to wait for UBI's answer, which takes one cancellation wait and one close per position.

        Returns:
            For a dry run, a dict with `dry_run`, `would_cancel` and `would_close`. Otherwise a dict with `cancelled`, `still_open_after_waiting`, `closed`, `flat` and `timing_ms`, where `flat` is False when any part was not done, which UBI answers with HTTP 207 rather than as an error.

        Raises:
            BadRequestError: `confirm` is not exactly `FLATTEN`.
            ServiceUnavailableError: UBI could not read the order books or positions.
            UnreachableError: No answer arrived within the timeout, so part of the flatten may have happened.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        body = {
            "confirm": confirm,
            "dry_run": bool(dry_run),
        }
        return self.unified_broker_interface.post(
            FLATTEN_PATH,
            body=body,
            timeout_seconds=timeout_seconds,
        )
