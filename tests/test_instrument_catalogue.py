"""Tests for InstrumentCatalogue, InstrumentMasterStream, PricesDocument and the Instrument members built on them."""

import json

import pandas as pd
import pytest

from tests import fake_ubi_server
from tradingmachine.assets import instruments
from tradingmachine.ubi_client import client
from tradingmachine.ubi_client import exceptions
from tradingmachine.ubi_client import instrument_catalogue
from tradingmachine.ubi_client import prices_document
from tradingmachine.ubi_client import token_sources

INSTRUMENT_ID = "3f92570a-9924-5bf5-9f9d-e006cd9f4202"

PRICES = {
    "instrument_id": INSTRUMENT_ID,
    "interval": "day",
    "from": "2026-09-23",
    "to": "2026-09-26",
    "adjustable": True,
    "price_basis": "adjusted",
    "source": "cache",
    "known_as_of": None,
    "columns": [
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "oi",
        "price_factor",
    ],
    "candles": [
        ["2026-09-25T00:00:00+05:30", 101.0, 104.0, 100.0, 103.0, 2000, None, 1.0],
        ["2026-09-24T00:00:00+05:30", 100.0, 102.0, 99.0, 101.0, 1500, None, 1.0],
    ],
}

DETAILS = {
    "instrument_id": INSTRUMENT_ID,
    "exchange": "nse",
    "segment": "nse_equities",
    "shape": "security",
    "symbol": "RELIANCE",
    "underlying_symbol": None,
    "expiry_date": None,
    "strike_price": None,
    "option_type": None,
    "mapping_date": "2026-09-26",
    "first_seen_date": "2026-01-01",
    "last_seen_date": "2026-09-26",
    "lot_size": 1,
    "tick_size": "0.05",
    "carried_by": [],
}


def build_client(
    ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
) -> client.UnifiedBrokerInterface:
    """Builds a client for the fake server with the fake server's key and secret.

    Args:
        ubi_server: The running fake UBI server.

    Returns:
        A client.UnifiedBrokerInterface that needs no configuration.

    Raises:
        Nothing.
    """
    return client.UnifiedBrokerInterface(
        base_url=ubi_server.base_url,
        token_source=token_sources.CredentialTokenSource(
            fake_ubi_server.API_KEY,
            fake_ubi_server.API_SECRET,
        ),
    )


def master_chunks(text: str, size: int) -> list[bytes]:
    """Cuts a text into chunks of bytes of one size, which may split a character's bytes.

    Args:
        text: The str to cut.
        size: The int number of bytes in each chunk.

    Returns:
        A list of bytes chunks.

    Raises:
        Nothing.
    """
    content = text.encode()
    chunks = []
    for start in range(0, len(content), size):
        chunks.append(content[start : start + size])
    return chunks


class TestInstrumentMasterStream:
    """The master is read in batches, and an incomplete answer raises."""

    def test_batches_follow_catalogue_order(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks the batches, the mapping date and the request parameters.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: A batch, the mapping date or a parameter was wrong.
        """
        identities = []
        for index in range(12):
            identities.append({"instrument_id": f"id-{index}", "symbol": "₹ SYMBOL"})
        ubi_server.answer(
            "GET",
            "/api/instruments/master",
            200,
            headers={"X-Mapping-Date": "2026-09-26"},
            chunks=master_chunks(json.dumps(identities, ensure_ascii=False), 7),
        )
        catalogue = instrument_catalogue.InstrumentCatalogue(build_client(ubi_server))
        with catalogue.open_master() as stream:
            assert stream.mapping_date == "2026-09-26"
            batches = list(stream.batches(5))
        assert [len(batch) for batch in batches] == [5, 5, 2]
        received = []
        for batch in batches:
            received.extend(batch)
        assert received == identities
        request = ubi_server.requests_to("/api/instruments/master")[0]
        assert request.query == {"exchange": "all", "segment": "all"}

    def test_next_batch_returns_none_at_the_end(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks next_batch on an empty master.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: A batch was returned.
        """
        ubi_server.answer(
            "GET",
            "/api/instruments/master",
            200,
            headers={"X-Mapping-Date": "2026-09-26"},
            chunks=[b"[]"],
        )
        catalogue = instrument_catalogue.InstrumentCatalogue(build_client(ubi_server))
        with catalogue.open_master(exchange="nse", segment="nse_equities") as stream:
            assert stream.next_batch() is None
            assert stream.item_count == 0

    def test_truncated_master_raises(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that a master cut off before its closing bracket raises rather than returning a short list.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: No IncompleteResponseError was raised.
        """
        ubi_server.answer(
            "GET",
            "/api/instruments/master",
            200,
            headers={"X-Mapping-Date": "2026-09-26"},
            chunks=[b'[{"instrument_id": "a"}, {"instrument_id": "b"}'],
        )
        catalogue = instrument_catalogue.InstrumentCatalogue(build_client(ubi_server))
        with catalogue.open_master() as stream:
            with pytest.raises(exceptions.IncompleteResponseError, match="ended early"):
                list(stream.batches(1))

    def test_missing_mapping_date_raises(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that an answer without X-Mapping-Date raises.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: No IncompleteResponseError was raised.
        """
        ubi_server.answer(
            "GET",
            "/api/instruments/master",
            200,
            chunks=[b"[]"],
        )
        catalogue = instrument_catalogue.InstrumentCatalogue(build_client(ubi_server))
        with pytest.raises(exceptions.IncompleteResponseError, match="X-Mapping-Date"):
            catalogue.open_master()


class TestPricesDocument:
    """The prices answer keeps UBI's facts and gives the same frame Instrument.prices always gave."""

    def test_facts_are_kept(self) -> None:
        """Checks every attribute and that the raw answer is kept unchanged.

        Raises:
            AssertionError: An attribute was wrong.
        """
        document = prices_document.PricesDocument(PRICES)
        assert document.document is PRICES
        assert document.price_basis == "adjusted"
        assert document.adjustable is True
        assert document.source == "cache"
        assert document.from_date == "2026-09-23"
        assert document.to_date == "2026-09-26"
        assert document.interval == "day"
        assert document.columns[0] == "time"
        assert len(document.candles) == 2
        assert not document.is_empty

    def test_frame_is_sorted_and_labelled(self) -> None:
        """Checks the frame's columns, time zone, order and values.

        Raises:
            AssertionError: The frame was built differently.
        """
        frame = prices_document.PricesDocument(PRICES).frame(
            "nse", "nse_equities", "day"
        )
        assert list(frame.columns) == [
            "exchange",
            "segment",
            "interval",
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "oi",
            "price_factor",
        ]
        assert str(frame["datetime"].dt.tz) == "Asia/Kolkata"
        assert list(frame["close"]) == [101.0, 103.0]
        assert frame["exchange"][0] == "nse"
        assert frame.index.tolist() == [0, 1]

    def test_empty_answer_has_no_frame(self) -> None:
        """Checks that an answer without candles, or without the key at all, gives None.

        Raises:
            AssertionError: A frame was returned.
        """
        empty = dict(PRICES)
        empty["candles"] = []
        assert prices_document.PricesDocument(empty).frame("nse", "x", "day") is None
        assert prices_document.PricesDocument({}).is_empty


class TestInstrumentCatalogue:
    """Each catalogue method sends its route and parameters and returns UBI's answer."""

    def test_routes_and_parameters(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks details, additional details, quote, segments, mapping date, greeting and prices.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: A route, parameter or answer was wrong.
        """
        ubi_server.answer("GET", "/api/", 200, {"message": "Welcome"})
        ubi_server.answer(
            "GET",
            "/api/instruments/segments",
            200,
            {"mapping_date": "2026-09-26", "exchanges": [], "segments": []},
        )
        ubi_server.answer("GET", "/api/instruments/details", 200, DETAILS)
        ubi_server.answer(
            "GET",
            "/api/instruments/additional_details",
            200,
            {"attribute_names": ["isin"], "carried_by": []},
        )
        ubi_server.answer(
            "GET", "/api/instruments/quote", 200, {"last_price": 1.5, "source": "cache"}
        )
        ubi_server.answer("GET", "/api/instruments/prices", 200, PRICES)
        catalogue = instrument_catalogue.InstrumentCatalogue(build_client(ubi_server))
        assert catalogue.greeting == {"message": "Welcome"}
        assert catalogue.mapping_date == "2026-09-26"
        assert catalogue.details(INSTRUMENT_ID) == DETAILS
        assert catalogue.additional_details(INSTRUMENT_ID)["attribute_names"] == [
            "isin"
        ]
        assert catalogue.quote(INSTRUMENT_ID)["source"] == "cache"
        document = catalogue.prices_document(
            INSTRUMENT_ID, interval="5minute", days=30, adjusted=False
        )
        assert document.document == PRICES
        for path in [
            "/api/instruments/details",
            "/api/instruments/additional_details",
            "/api/instruments/quote",
        ]:
            assert ubi_server.requests_to(path)[0].query == {
                "instrument_id": INSTRUMENT_ID
            }
        assert ubi_server.requests_to("/api/instruments/prices")[0].query == {
            "instrument_id": INSTRUMENT_ID,
            "interval": "5minute",
            "adjusted": "false",
            "days": "30",
        }

    def test_unknown_instrument_raises_not_found(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that a 404 is raised as NotFoundError with UBI's message.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: No NotFoundError was raised.
        """
        ubi_server.answer(
            "GET", "/api/instruments/details", 404, {"error": "unknown instrument"}
        )
        catalogue = instrument_catalogue.InstrumentCatalogue(build_client(ubi_server))
        with pytest.raises(exceptions.NotFoundError, match="unknown instrument"):
            catalogue.details("missing")


class TestInstrumentMembers:
    """Instrument.prices, prices_document and additional_details go through the catalogue."""

    def test_prices_and_prices_document_agree(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that prices returns the document's frame and sends a date range.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The frame or the request differed.
        """
        ubi_server.answer("GET", "/api/instruments/details", 200, DETAILS)
        ubi_server.answer("GET", "/api/instruments/prices", 200, PRICES)
        ubi_server.answer(
            "GET",
            "/api/instruments/additional_details",
            200,
            {"attribute_names": [], "carried_by": [{"isin": "INE002A01018"}]},
        )
        instrument = instruments.Instrument(
            instrument_id=INSTRUMENT_ID,
            unified_broker_interface=build_client(ubi_server),
        )
        frame = instrument.prices(from_date="2026-09-23", to_date="2026-09-26")
        document = instrument.prices_document(
            from_date="2026-09-23", to_date="2026-09-26"
        )
        pd.testing.assert_frame_equal(
            frame, document.frame("nse", "nse_equities", "day"), check_exact=True
        )
        assert document.price_basis == "adjusted"
        assert ubi_server.requests_to("/api/instruments/prices")[0].query == {
            "instrument_id": INSTRUMENT_ID,
            "interval": "day",
            "adjusted": "true",
            "from": "2026-09-23",
            "to": "2026-09-26",
        }
        assert instrument.additional_details["carried_by"][0]["isin"] == "INE002A01018"

    def test_prices_returns_none_without_candles(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that an empty answer still gives None.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: A frame was returned.
        """
        empty = dict(PRICES)
        empty["candles"] = []
        ubi_server.answer("GET", "/api/instruments/details", 200, DETAILS)
        ubi_server.answer("GET", "/api/instruments/prices", 200, empty)
        instrument = instruments.Instrument(
            instrument_id=INSTRUMENT_ID,
            unified_broker_interface=build_client(ubi_server),
        )
        assert instrument.prices(days=5) is None
