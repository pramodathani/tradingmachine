"""UBI's instrument master read in batches as it arrives.

`GET /api/instruments/master` answers with one JSON array of every instrument's identity, over half a million of them and more than a hundred megabytes when every exchange and segment is asked for. This class reads that answer piece by piece and hands out batches, so the whole array is never held in memory, and it raises rather than returning a short list when the answer stops early.

Typical usage example:

  with catalogue.open_master() as stream:
      print(stream.mapping_date)
      for batch in stream.batches(5000):
          store(batch)
"""

import codecs
from collections.abc import Iterator
from typing import Any

import requests

from tradingmachine.ubi_client import exceptions
from tradingmachine.ubi_client import json_array_stream_parser

MAPPING_DATE_HEADER = "X-Mapping-Date"

DEFAULT_BATCH_SIZE = 5000

CHUNK_SIZE = 65536


class InstrumentMasterStream:
    """One open answer from UBI's instrument master route, read in batches.

    Attributes:
        mapping_date: The str mapping date the catalogue belongs to, from the `X-Mapping-Date` header, such as `2026-09-26`.
    """

    def __init__(self, response: requests.Response):
        """Initialises the stream over an open, successful response.

        Args:
            response: The open requests.Response from `UnifiedBrokerInterface.stream_get`, whose body has not been read.

        Raises:
            IncompleteResponseError: The response has no `X-Mapping-Date` header; the response is closed.
        """
        self._response = response
        mapping_date = response.headers.get(MAPPING_DATE_HEADER)
        if not mapping_date:
            response.close()
            raise exceptions.IncompleteResponseError(
                "UBI answered the instrument master without an X-Mapping-Date header."
            )
        self.mapping_date = mapping_date
        self._chunks = response.iter_content(chunk_size=CHUNK_SIZE)
        self._decoder = codecs.getincrementaldecoder("utf-8")()
        self._parser = json_array_stream_parser.JsonArrayStreamParser()
        self._pending = []
        self._exhausted = False

    @property
    def item_count(self) -> int:
        """The int number of instruments parsed so far, including any not yet handed out."""
        return self._parser.item_count

    def next_batch(self, batch_size: int = DEFAULT_BATCH_SIZE) -> list[dict] | None:
        """Reads until one batch is complete, or the array ends.

        Each call reads only as much of the answer as the batch needs, so a caller in an event loop can hand one call at a time to a worker thread.

        Args:
            batch_size: The int number of instruments in each batch except the last.

        Returns:
            A list of up to batch_size identity dicts, in catalogue order, or None once every instrument has been handed out.

        Raises:
            IncompleteResponseError: The answer ended before its closing bracket, or is not a JSON array.
            UnreachableError: The connection failed while the answer was being read.
        """
        while len(self._pending) < batch_size and not self._exhausted:
            self._read_more()
        if not self._pending:
            return None
        batch = self._pending[:batch_size]
        self._pending = self._pending[batch_size:]
        return batch

    def batches(self, batch_size: int = DEFAULT_BATCH_SIZE) -> Iterator[list[dict]]:
        """Hands out every batch in turn.

        Args:
            batch_size: The int number of instruments in each batch except the last.

        Yields:
            A list of up to batch_size identity dicts, in catalogue order.

        Raises:
            IncompleteResponseError: The answer ended before its closing bracket, or is not a JSON array.
            UnreachableError: The connection failed while the answer was being read.
        """
        while True:
            batch = self.next_batch(batch_size)
            if batch is None:
                return
            yield batch

    def close(self) -> None:
        """Closes the answer, releasing its connection, whether or not it was read to the end.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._response.close()

    def __enter__(self) -> "InstrumentMasterStream":
        """Returns the stream for a `with` block, which closes it at the end.

        Returns:
            This InstrumentMasterStream.

        Raises:
            Nothing.
        """
        return self

    def __exit__(self, *exception_information: Any) -> None:
        """Closes the stream at the end of a `with` block.

        Args:
            *exception_information: The exception type, value and traceback, or three Nones.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.close()

    def _read_more(self) -> None:
        """Reads one more chunk of the answer into the pending values, or checks the ending once there are no more chunks.

        Returns:
            None.

        Raises:
            IncompleteResponseError: The answer ended before its closing bracket, or is not a JSON array.
            UnreachableError: The connection failed while the answer was being read.
        """
        try:
            chunk = next(self._chunks, None)
        except requests.RequestException as error:
            raise exceptions.UnreachableError(
                f"The instrument master download from UBI failed after {self.item_count} instruments: {error}"
            ) from error
        try:
            if chunk is None:
                self._exhausted = True
                text = self._decoder.decode(b"", final=True)
                self._pending.extend(self._parser.feed(text))
                self._parser.finish()
                return
            text = self._decoder.decode(chunk)
            self._pending.extend(self._parser.feed(text))
        except ValueError as error:
            raise exceptions.IncompleteResponseError(
                f"UBI's instrument master is incomplete: {error}"
            ) from error
