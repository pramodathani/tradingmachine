"""The shared base of every synthetic order type UBI's order engine runs.

A synthetic order is one ordinary order body, the template, plus a `synthetic` object naming the type and holding that type's own settings. UBI's order engine then places, watches, changes and cancels the real orders the type is made of. `SyntheticOrder` holds the template and sends it through `TradeableInstrument.place_order`; each subclass in `tradingmachine.orders` adds its own settings.

Typical usage example:

  share = equities.Equity(exchange="nse", symbol="RELIANCE")
  order = bracket.BracketOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=1000.0,
      stop_price=990.0,
      stop_limit_price=988.0,
      target_price=1010.0,
      dry_run=True,
  )
  answer = order.place()
"""

import pandas as pd

from tradingmachine.assets import instruments


class SyntheticOrder:
    """One order for UBI's order engine: an order template and the synthetic type that works it.

    The template is validated by UBI exactly as a plain order is, and most types use it for every real order they send, changing only what they must. Nothing is checked here before sending.

    Attributes:
        instrument: The instruments.TradeableInstrument the order is placed in.
        transaction_type: The str side of the order, `buy` or `sell`.
        product: The str product, `cnc`, `mis` or `nrml`.
        order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
        quantity: The int quantity in underlying units, or None when a quantity reference supplies it.
        price: The float limit price in rupees, or None.
        trigger_price: The float trigger price in rupees of the order itself, or None.
        validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
        disclosed_quantity: The int quantity to show on the exchange, or None.
        after_market: A bool that is True to send the order as an after-market order.
        tag: A str of up to twenty letters and digits to label the order with, or None.
        price_reference: A dict describing the price for UBI to work out, or None.
        quantity_reference: A dict describing the quantity for UBI to work out, or None.
        closes_position: A bool that is True when every order this type sends closes a position, so it may use the share of a broker's daily order cap kept for exits.
        reduce_only: A bool that is True to have UBI check every leg against the net position held in the leg's instrument and product just before sending it, and refuse with HTTP 409 any leg that is not on the closing side or is bigger than the position.
        dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.
        parent_id: The str id UBI's order engine gave this order when `place()` sent it, or None before then and after a dry run, which records nothing.
    """

    SYNTHETIC_TYPE = "simple"

    def __init__(
        self,
        instrument: instruments.TradeableInstrument,
        *,
        transaction_type: str,
        product: str,
        order_type: str,
        quantity: int | None,
        price: float | None = None,
        trigger_price: float | None = None,
        validity: str | None = None,
        disclosed_quantity: int | None = None,
        after_market: bool = False,
        tag: str | None = None,
        price_reference: dict | None = None,
        quantity_reference: dict | None = None,
        closes_position: bool = False,
        reduce_only: bool = False,
        dry_run: bool = False,
    ):
        """Initialises the order template.

        Args:
            instrument: The instruments.TradeableInstrument to place the order in.
            transaction_type: The str side of the order, `buy` or `sell`.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            price: The float limit price in rupees, or None for an order type that takes no price or when a price reference supplies it.
            trigger_price: The float trigger price in rupees of the order itself, or None for an order type that takes no trigger.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            disclosed_quantity: The int quantity to show on the exchange, or None to disclose the whole order.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.
            price_reference: A dict describing the price for UBI to work out, such as `{"kind": "mid"}`, or None.
            quantity_reference: A dict describing the quantity for UBI to work out, such as `{"kind": "liquidate_position"}`, or None.
            closes_position: A bool that is True when every order this type sends closes a position.
            reduce_only: A bool that is True to have UBI refuse, with HTTP 409, any leg that is not on the closing side of the net position held when it is sent or is bigger than that position.
            dry_run: A bool that is True to have UBI build the first broker request and return it without recording or sending anything.

        Raises:
            Nothing.
        """
        self.instrument = instrument
        self.transaction_type = transaction_type
        self.product = product
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.trigger_price = trigger_price
        self.validity = validity
        self.disclosed_quantity = disclosed_quantity
        self.after_market = after_market
        self.tag = tag
        self.price_reference = price_reference
        self.quantity_reference = quantity_reference
        self.closes_position = closes_position
        self.reduce_only = reduce_only
        self.dry_run = dry_run
        self.parent_id = None

    def synthetic_fields(self) -> dict:
        """Gives this type's own settings, the fields of the `synthetic` object besides `type`.

        Returns:
            A dict of UBI field names to values, where a value of None means the field is left out. The base type has no settings, so this is empty.

        Raises:
            Nothing.

        Examples:
            Print the settings of the base type, which has none of its own:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
            )
            print(order.synthetic_fields())
            ```

            Compare the settings of the base type with those of a bracket order:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import bracket
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            plain_order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
            )
            bracket_order = bracket.BracketOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
                stop_price=12.5,
                stop_limit_price=12.45,
            )
            print(f"{plain_order.SYNTHETIC_TYPE}: {plain_order.synthetic_fields()}")
            print(f"{bracket_order.SYNTHETIC_TYPE}: {bracket_order.synthetic_fields()}")
            ```
        """
        return {}

    @property
    def synthetic(self) -> dict:
        """The `synthetic` object sent with the order, holding `type`, this type's settings that are not None, and `closes_position` and `reduce_only` when each is True.

        Examples:
            Print the synthetic object of an order of the base type, which names only the type:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
            )
            print(order.synthetic)
            ```

            Show that `closes_position` and `reduce_only` are added only when they are True:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="sell",
                product="mis",
                order_type="limit",
                quantity=1,
                price=14.0,
                closes_position=True,
                reduce_only=True,
            )
            print(order.synthetic)
            order.reduce_only = False
            print(order.synthetic)
            ```
        """
        document = {
            "type": self.SYNTHETIC_TYPE,
        }
        for field, value in self.synthetic_fields().items():
            if value is not None:
                document[field] = value
        if self.closes_position:
            document["closes_position"] = True
        if self.reduce_only:
            document["reduce_only"] = True
        return document

    def place(self) -> dict:
        """Sends the order to UBI's order engine through `TradeableInstrument.place_order`, and keeps the `parent_id` the engine answers with.

        Returns:
            The dict `place_order` returns. A type that acts at once answers with the broker's answer and a `parent_id`; a type that waits for a price or a time answers with an `outcome` of `armed` or `scheduled`, a `broker` and `order_id` of None, and a `parent_id`, which is the only handle on the order until it reaches a broker. The types that send several orders at once, `freeze_slicer`, `ladder`, `grid`, `two_sided_quote`, `basket`, `oco`, `bracket` and `two_sided_breakout`, answer with one combined `outcome`: `accepted` when every order was accepted, `partial` with HTTP 207 when only some were, which is returned rather than raised, and otherwise `unknown` or `rejected`, which are raised.

        Raises:
            BadRequestError: A template field is invalid, or one of this type's own settings is missing or wrong.
            LossLockoutError: The day's loss is past UBI's daily loss limit.
            ConflictError: The engine refused to act on the account's state, such as a post-only order that would cross the book or a reduce-only leg that would not reduce the position, or the engine had already started this order before a restart.
            RateLimitError: The broker's daily order cap has no room for this order.
            ServiceUnavailableError: No broker could take the order, a price UBI needed could not be read, or the order engine is not running.
            OrderOutcomeUnknownError: The engine did not answer in time, so the order may still be placed.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Preview the broker request for a limit buy with a dry run, which sends and records nothing:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=round(share.last_price * 0.97, 2),
                dry_run=True,
            )
            answer = order.place()
            print(answer)
            print(order.parent_id)
            ```

            Place a buy 3% below the market, print the engine's answer and cancel it at once:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
            )
            answer = order.place()
            try:
                print(answer["outcome"], answer["order_id"], order.parent_id)
            finally:
                print(order.cancel()["state"])
            ```

            Send a reduce-only sell far bigger than any position it could reduce, which UBI refuses with HTTP 409:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order
            from tradingmachine.unified_broker_interface import exceptions

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="sell",
                product="mis",
                order_type="limit",
                quantity=100000,
                price=round(share.last_price * 1.03, 2),
                reduce_only=True,
            )
            try:
                order.place()
            except exceptions.ConflictError as error:
                print(f"Refused: {error}")
            finally:
                if order.parent_id is not None:
                    print(order.cancel()["state"])
            ```
        """
        answer = self.instrument.place_order(
            transaction_type=self.transaction_type,
            order_type=self.order_type,
            quantity=self.quantity,
            product=self.product,
            price=self.price,
            trigger_price=self.trigger_price,
            validity=self.validity,
            disclosed_quantity=self.disclosed_quantity,
            after_market=self.after_market,
            tag=self.tag,
            dry_run=self.dry_run,
            price_reference=self.price_reference,
            quantity_reference=self.quantity_reference,
            synthetic=self.synthetic,
        )
        if isinstance(answer, dict) and answer.get("parent_id") is not None:
            self.parent_id = answer["parent_id"]
        return answer

    def cancel(self) -> dict:
        """Cancels this order in UBI's order engine, with every leg it still has resting at a broker.

        A position the order has already opened is not closed.

        Returns:
            The dict `TradeableInstrument.cancel_parent` returns, with `parent_id`, `synthetic_type`, `state` and a `cancelled_legs` list. Its `state` is `cancelling` rather than `cancelled` when a broker refused a leg's cancel, so that leg may still be live.

        Raises:
            ValueError: The order has not been placed, so there is no parent to cancel.
            NotFoundError: The engine holds no parent with this id.
            ConflictError: The parent has already finished.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Place a buy 3% below the market and cancel it, printing each leg that was cancelled:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
            )
            order.place()
            answer = order.cancel()
            print(answer["state"])
            for leg in answer["cancelled_legs"]:
                print(leg["broker"], leg["order_id"], leg["outcome"])
            ```

            Try to cancel an order that was never placed, which raises ValueError before UBI is asked:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=13.0,
            )
            try:
                order.cancel()
            except ValueError as error:
                print(error)
            ```
        """
        return self.instrument.cancel_parent(self._placed_parent_id())

    @property
    def parent(self) -> dict:
        """The order as UBI's order engine holds it now, with its `state`, the caller's `body`, the type's `parameters` and one entry per leg, read from UBI on every access.

        Raises:
            ValueError: The order has not been placed, so there is no parent to read.
            NotFoundError: The engine holds no parent with this id.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Place a buy 3% below the market and print the state and legs the engine holds for it:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
            )
            order.place()
            try:
                parent = order.parent
                print(parent["synthetic_type"], parent["state"])
                print(f"{len(parent['legs'])} legs")
            finally:
                order.cancel()
            ```

            Read the parent again after cancelling, to see the state it finished in:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
            )
            order.place()
            try:
                print(f"before: {order.parent['state']}")
            finally:
                order.cancel()
            print(f"after: {order.parent['state']}")
            ```
        """
        return self.instrument.parent(self._placed_parent_id())

    @property
    def orders(self) -> pd.DataFrame | None:
        """Today's broker orders this order has placed, as a pandas.DataFrame shaped like `TradeableInstrument.orders`, or None when it has placed none yet.

        Raises:
            ValueError: The order has not been placed, so it has no orders.
            UnifiedBrokerInterfaceError: The order book could not be read.

        Examples:
            Place a buy 3% below the market and print the broker orders it has placed:

            ```python
            import time

            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
            )
            order.place()
            try:
                time.sleep(2)
                print(order.orders)
            finally:
                order.cancel()
            ```

            Print the status of each broker order once the parent has been cancelled:

            ```python
            import time

            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
            )
            order.place()
            try:
                time.sleep(2)
            finally:
                order.cancel()
            time.sleep(2)
            broker_orders = order.orders
            if broker_orders is None:
                print("No broker order was placed.")
            else:
                print(broker_orders[["order_id", "status"]])
            ```
        """
        return self.instrument.parent_orders(self._placed_parent_id())

    @property
    def trades(self) -> pd.DataFrame | None:
        """Today's fills of the broker orders this order has placed, as a pandas.DataFrame shaped like `TradeableInstrument.trades`, or None when nothing has filled yet.

        Raises:
            ValueError: The order has not been placed, so it has no trades.
            UnifiedBrokerInterfaceError: The trade book could not be read.

        Examples:
            Place a buy 3% below the market, which does not fill, and see that it has no trades:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            limit_price = round(share.last_price * 0.97, 2)
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                price=limit_price,
            )
            order.place()
            try:
                print(order.trades)
            finally:
                order.cancel()
            ```

            Buy one share at the best offer, print its fill, then sell it back at the broker that holds it:

            ```python
            import time

            from tradingmachine.assets import equities
            from tradingmachine.orders import synthetic_order

            share = equities.Equity(exchange="nse", symbol="IDEA")
            order = synthetic_order.SyntheticOrder(
                share,
                transaction_type="buy",
                product="mis",
                order_type="limit",
                quantity=1,
                validity="ioc",
                price_reference={
                    "kind": "marketable",
                },
            )
            order.place()
            fills = None
            try:
                for attempt in range(10):
                    fills = order.trades
                    if fills is not None:
                        break
                    time.sleep(1)
                print(fills)
            finally:
                if fills is not None:
                    share.reduce_position(
                        quantity=1,
                        product="mis",
                        price=round(share.last_price * 0.995, 2),
                    )
            ```
        """
        return self.instrument.parent_trades(self._placed_parent_id())

    def _placed_parent_id(self) -> str:
        """Gives the engine's id for this order, refusing when it has not been placed.

        Returns:
            The str `parent_id` that `place()` kept.

        Raises:
            ValueError: `place()` has not been called, was a dry run, or was answered without a `parent_id`.
        """
        if self.parent_id is None:
            raise ValueError(
                f"This {self.SYNTHETIC_TYPE} order has no parent_id, because place() has not sent it to UBI's order engine yet, or sent it only as a dry run"
            )
        return self.parent_id
