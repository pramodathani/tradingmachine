"""Turns rows that name instruments into basket members with one list request to UBI.

A stored basket, a CSV file and the account's holdings all describe their instruments as plain rows, each naming an instrument by `instrument_id` or by exchange, segment and identity fields, beside a weight or a quantity. `MemberResolver.resolve` sends every row to `POST /api/instruments/details` at once and builds each member's instrument from its entry of the answer, so a basket of five hundred instruments costs one request rather than five hundred.

Typical usage example:

  resolver = member_resolver.MemberResolver()
  members = resolver.resolve(
      [
          {"exchange": "nse", "segment": "equities", "symbol": "INFY", "weight": 0.6},
          {"exchange": "nse", "segment": "equities", "symbol": "TCS", "weight": 0.4},
      ]
  )
"""

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import exceptions
from tradingmachine.assets import instruments
from tradingmachine.unified_broker_interface import client

DETAILS_PATH = "/api/instruments/details"

IDENTITY_FIELDS = [
    "exchange",
    "segment",
    "symbol",
    "underlying_symbol",
    "expiry_date",
    "strike_price",
    "option_type",
]

SUCCESS_STATUS = 200


class MemberResolver:
    """A builder of basket members from rows that name their instruments.

    Attributes:
        unified_broker_interface: The client.UnifiedBrokerInterface the details request is sent through.
    """

    def __init__(
        self,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Initialises the resolver with the client it sends requests through.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface to use, or None to share the one every instrument uses.

        Raises:
            ValueError: No client was given and the shared client's base url or MongoDB credentials are not configured.
        """
        if unified_broker_interface is None:
            unified_broker_interface = (
                instruments.Instrument.shared_unified_broker_interface()
            )
        self.unified_broker_interface = unified_broker_interface

    def resolve(self, rows: list[dict]) -> list[basket_member.BasketMember]:
        """Looks every row's instrument up in UBI and returns one member per row.

        An index becomes a tradingmachine.assets.instruments.NonTradeableInstrument and anything else a tradingmachine.assets.instruments.TradeableInstrument. A row that names its instrument by `instrument_id` is looked up by that alone, and any other row by the identity fields it has.

        Args:
            rows: A list of dicts, each with `instrument_id` or `exchange`, `segment` and the identity fields its shape needs, and optionally `weight`, `quantity` and `average_price`.

        Returns:
            A list of basket_member.BasketMember, in the order of rows.

        Raises:
            BasketMemberError: rows is empty, or UBI could not find one or more of the instruments, all of which the message lists.
            UnifiedBrokerInterfaceError: The whole request was refused by, or failed on the way to, UBI.
        """
        if not rows:
            raise exceptions.BasketMemberError("There are no rows to resolve")
        instrument_lookups = []
        for row in rows:
            instrument_lookups.append(self._lookup_for(row))
        response = self.unified_broker_interface.post(
            DETAILS_PATH,
            body={
                "instruments": instrument_lookups,
            },
        )
        members = []
        failures = []
        for row, result in zip(rows, response["results"]):
            if result["status"] != SUCCESS_STATUS:
                failures.append(
                    f"{instrument_lookups[result['request_index']]}: {result.get('error')}"
                )
                continue
            instrument = self._instrument_from(result["data"])
            members.append(
                basket_member.BasketMember(
                    instrument,
                    weight=row.get("weight"),
                    quantity=row.get("quantity"),
                    average_price=row.get("average_price"),
                )
            )
        if failures:
            raise exceptions.BasketMemberError(
                f"UBI could not find {len(failures)} of {len(rows)} instruments: {'; '.join(failures)}"
            )
        return members

    def resolve_one(self, row: dict) -> instruments.Instrument:
        """Looks one row's instrument up in UBI.

        Args:
            row: A dict with `instrument_id` or `exchange`, `segment` and the identity fields its shape needs.

        Returns:
            The tradingmachine.assets.instruments.NonTradeableInstrument for an index, or the tradingmachine.assets.instruments.TradeableInstrument for anything else.

        Raises:
            BasketMemberError: UBI could not find the instrument.
            UnifiedBrokerInterfaceError: The request was refused by, or failed on the way to, UBI.
        """
        members = self.resolve(
            [
                row,
            ]
        )
        return members[0].instrument

    @staticmethod
    def _lookup_for(row: dict) -> dict:
        """Picks the fields of a row that name its instrument.

        Args:
            row: A dict naming one instrument, possibly with other keys such as `weight`.

        Returns:
            A dict holding only `instrument_id` when the row has one, and otherwise every identity field the row gives a value for.

        Raises:
            BasketMemberError: The row has neither an `instrument_id` nor an `exchange` and a `segment`.
        """
        if row.get("instrument_id") is not None:
            return {
                "instrument_id": row["instrument_id"],
            }
        lookup = {}
        for field in IDENTITY_FIELDS:
            if row.get(field) is not None:
                lookup[field] = row[field]
        if "exchange" not in lookup or "segment" not in lookup:
            raise exceptions.BasketMemberError(
                f"A row must give an instrument_id, or an exchange and a segment: {row=}"
            )
        return lookup

    def _instrument_from(self, details: dict) -> instruments.Instrument:
        """Builds an instrument object from its details without asking UBI again.

        Args:
            details: The dict UBI returned for one instrument from `/api/instruments/details`.

        Returns:
            A tradingmachine.assets.instruments.NonTradeableInstrument for an index, or a tradingmachine.assets.instruments.TradeableInstrument for anything else.

        Raises:
            KeyError: details lacks a field every UBI details answer carries.
        """
        if details["segment"].endswith(instruments.INDEX_SEGMENT_SUFFIX):
            return instruments.NonTradeableInstrument(
                unified_broker_interface=self.unified_broker_interface,
                details=details,
            )
        return instruments.TradeableInstrument(
            unified_broker_interface=self.unified_broker_interface,
            details=details,
        )
