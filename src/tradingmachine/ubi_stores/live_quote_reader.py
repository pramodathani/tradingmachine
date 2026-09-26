"""Reads many instruments' live quotes at once from UBI's Redis, never writing to it.

UBI's REST quote routes answer for one instrument per request. For an application that follows hundreds of instruments twice a second, or colours a map of 43,000, that is too slow, and UBI itself reads its quotes for many instruments straight from the Redis hash `unified:quotes:live`, whose field is the instrument id and whose value is the unified quote as JSON. This reader does the same, a few hundred fields per round trip.

Typical usage example:

  reader = LiveQuoteReader(redis_settings)
  quotes = reader.read(instrument_ids)
  reader.close()
"""

import json

import redis

from tradingmachine.ubi_client import exceptions
from tradingmachine.ubi_stores import store_settings

LIVE_QUOTES_HASH = "unified:quotes:live"

DEFAULT_BATCH_SIZE = 500


class LiveQuoteReader:
    """Read-only access to the live quotes UBI keeps in Redis.

    Attributes:
        hash_name: The str name of the Redis hash read.
        batch_size: The int largest number of instruments read in one round trip.
    """

    def __init__(
        self,
        redis_settings: store_settings.RedisSettings,
        hash_name: str = LIVE_QUOTES_HASH,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        """Initialises the reader; Redis is not contacted until the first read.

        Args:
            redis_settings: The store_settings.RedisSettings of UBI's Redis.
            hash_name: The str name of the hash holding one quote per instrument id.
            batch_size: The int largest number of instruments to read in one round trip.

        Raises:
            ValueError: The batch size is less than one.
        """
        if batch_size < 1:
            raise ValueError(f"The batch size must be at least one: {batch_size=}")
        self.hash_name = hash_name
        self.batch_size = batch_size
        self._redis_client = redis.Redis(
            host=redis_settings.host,
            port=redis_settings.port,
            db=redis_settings.database,
            username=redis_settings.username,
            password=redis_settings.password,
            decode_responses=True,
            socket_timeout=redis_settings.timeout_seconds,
            socket_connect_timeout=redis_settings.timeout_seconds,
        )

    def read(self, instrument_ids: list[str]) -> dict[str, dict]:
        """Reads the live quotes of the given instruments.

        Args:
            instrument_ids: A list of str UBI instrument ids; repeated ids are read once.

        Returns:
            A dict mapping each instrument id that has a quote to that quote as a dict, the unified quote UBI documents, with `last_price`, `ohlc`, `depth`, `received_at` and the other fields. Instruments without a quote, or whose stored value is not a JSON object, are left out.

        Raises:
            UnreachableError: Redis could not be read.
        """
        unique_ids = list(dict.fromkeys(instrument_ids))
        quotes = {}
        for start in range(0, len(unique_ids), self.batch_size):
            batch = unique_ids[start : start + self.batch_size]
            try:
                texts = self._redis_client.hmget(self.hash_name, batch)
            except (redis.RedisError, OSError) as error:
                raise exceptions.UnreachableError(
                    f"UBI Redis could not be read for live quotes: {error}"
                ) from error
            for instrument_id, text in zip(batch, texts, strict=True):
                if text is None:
                    continue
                try:
                    quote = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(quote, dict):
                    quotes[instrument_id] = quote
        return quotes

    def close(self) -> None:
        """Closes the connection to Redis.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._redis_client.close()
