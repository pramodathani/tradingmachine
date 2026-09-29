"""The whole trading account behind UBI, and the kill switch that empties it.

`Account.flatten` sends `POST /api/orders/flatten`, which stops every synthetic order UBI's order engine is running, cancels every open order at every broker, waits until the brokers confirm the cancellations, and only then closes every position with market orders. It acts on the whole account, not on one instrument; `TradeableInstrument.liquidate_all_positions` is the per-instrument equivalent. `Account.parents` lists every synthetic order the engine has not finished, and `Account.intent` reads the engine's answer to an order whose placement stopped waiting for it.

Typical usage example:

  trading_account = account.Account()
  preview = trading_account.flatten(confirm="FLATTEN", dry_run=True)
  outcome = trading_account.flatten(confirm="FLATTEN")
"""

import pandas as pd

from tradingmachine.assets import instruments
from tradingmachine.unified_broker_interface import client

FLATTEN_PATH = "/api/orders/flatten"

PARENTS_PATH = "/api/orders/parents"

INTENT_PATH = "/api/orders/intents/{intent_id}"

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
        """Stops every synthetic order, cancels every open order at every broker, then closes every position in the account.

        UBI first halts every parent its order engine has not finished, so no armed trigger, trailing stop or grid can place anything afterwards; a halted parent's resting orders are left for the cancellations. The cancellations go next and the closes wait for them to be confirmed, because a stop or a target still resting when its position is closed would fill afterwards and open a new position the other way. Each position is then closed with a market order at the broker that holds it, all of them at once, and UBI waits again until the brokers' positions show zero before answering that the account is flat.

        A timeout does not mean nothing happened: read the orders and positions before calling it again, or a second flatten may close positions twice.

        Args:
            confirm: The str `FLATTEN`, typed by the caller, which UBI requires so that a stray call cannot unwind the account.
            dry_run: A bool that is True to report what would be cancelled and closed without sending anything.
            timeout_seconds: The float number of seconds to wait for UBI's answer, which takes one wait for the cancellations and one for the closed positions to show zero.

        Returns:
            For a dry run, a dict with `dry_run`, `would_cancel` and `would_close`. Otherwise a dict with `halted`, `cancelled`, `still_open_after_waiting`, `closed`, `positions_still_open_after_waiting`, `flat` and `timing_ms`, where `flat` is False when any part was not done or a closed position was still held when the wait ended, which UBI answers with HTTP 207 rather than as an error.

        Raises:
            BadRequestError: `confirm` is not exactly `FLATTEN`.
            ServiceUnavailableError: UBI could not read the order books or positions.
            UnreachableError: No answer arrived within the timeout, so part of the flatten may have happened.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Preview what a flatten would cancel and close, without sending anything:

            ```python
            from tradingmachine.accounts import account

            trading_account = account.Account()
            preview = trading_account.flatten(confirm="FLATTEN", dry_run=True)
            print(f"Would cancel: {preview['would_cancel']}")
            print(f"Would close: {preview['would_close']}")
            ```

            See UBI refuse a flatten whose confirmation word is not typed exactly:

            ```python
            from tradingmachine.accounts import account
            from tradingmachine.unified_broker_interface import exceptions

            trading_account = account.Account()
            try:
                trading_account.flatten(confirm="flatten", dry_run=True)
            except exceptions.BadRequestError as error:
                print(f"Refused: {error.message}")
            ```

            Flatten the whole account for real and check that it ended flat, which closes every position and cancels every order:

            ```python
            from tradingmachine.accounts import account

            trading_account = account.Account()
            outcome = trading_account.flatten(confirm="FLATTEN")
            if outcome["flat"]:
                print(f"The account is flat after {outcome['timing_ms']} ms.")
            else:
                print(outcome["still_open_after_waiting"])
                print(outcome["positions_still_open_after_waiting"])
            ```
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

    @property
    def parents(self) -> pd.DataFrame | None:
        """Every synthetic order and held order that UBI's order engine has not finished, in every instrument.

        A parent is one order the engine was asked for, such as a bracket, a trailing stop or a limit order it is holding until the book reaches its price, and its legs are the broker orders it placed. `TradeableInstrument.parents` gives one instrument's.

        Returns:
            A pandas.DataFrame with one row per parent, holding UBI's parent fields, among them `parent_order_id`, `synthetic_type`, `state`, `instrument_id`, `body`, `parameters` and `legs`, or None when no parent is open.

        Raises:
            ServiceUnavailableError: UBI's parents could not be read.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Print every parent the order engine is still working, or None when there is none:

            ```python
            from tradingmachine.accounts import account

            trading_account = account.Account()
            print(trading_account.parents)
            ```

            Count the open parents of each synthetic order type:

            ```python
            from tradingmachine.accounts import account

            trading_account = account.Account()
            parents = trading_account.parents
            if parents is None:
                print("No parent is open.")
            else:
                print(parents["synthetic_type"].value_counts())
            ```
        """
        rows = self.unified_broker_interface.get(PARENTS_PATH)["parents"]
        if not rows:
            return None
        return pd.DataFrame(rows)

    def intent(self, intent_id: str) -> dict:
        """Reads what UBI's order engine did with one order after its placement stopped waiting for the answer.

        Every answer to placing an order carries an `intent_id`, and so does the detail of an OrderOutcomeUnknownError raised when the engine did not answer in time. UBI keeps each answer for five minutes by default after the engine gives it.

        Args:
            intent_id: The str `intent_id` from the placement's answer or error detail.

        Returns:
            A dict with `intent_id`, the HTTP `status` the placement would have answered with, and the `response` body it would have answered with.

        Raises:
            NotFoundError: The engine has not answered this intent yet, the id is not one, or its answer has expired.
            ServiceUnavailableError: UBI could not read its store.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Read the engine's stored answer to a held limit order by its `intent_id`, then cancel the order:

            ```python
            from tradingmachine.accounts import account
            from tradingmachine.assets import equities

            idea = equities.Equity(exchange="nse", symbol="IDEA")
            price = round(idea.last_price * 0.97, 2)
            answer = idea.buy_at_limit_price(price=price, quantity=1, product="mis")
            try:
                trading_account = account.Account()
                engine_answer = trading_account.intent(answer["intent_id"])
                print(engine_answer["status"], engine_answer["response"]["outcome"])
            finally:
                idea.cancel_parent(answer["parent_id"])
            ```

            Handle an intent id the engine has no answer for:

            ```python
            from tradingmachine.accounts import account
            from tradingmachine.unified_broker_interface import exceptions

            trading_account = account.Account()
            try:
                trading_account.intent("00000000-0000-0000-0000-000000000000")
            except exceptions.NotFoundError as error:
                print(error.message)
            ```
        """
        return self.unified_broker_interface.get(
            INTENT_PATH.format(intent_id=intent_id),
        )
