"""Where UBI's own Redis and MongoDB are, and how to log in to them.

These settings are filled in by the calling program, which usually reads them from UBI's `.env`. Nothing here reads the environment, so a program can point at UBI's stores without taking on tradingmachine's own configuration.

Typical usage example:

  redis_settings = RedisSettings(host="127.0.0.1", port=1002, database=0, username="default", password="...")
"""


class RedisSettings:
    """The address and login of UBI's Redis.

    Attributes:
        host: The str host Redis listens on, such as `127.0.0.1`.
        port: The int port Redis listens on.
        database: The int Redis database number.
        username: The str user to log in as, or None.
        password: The str password, or None.
        timeout_seconds: The float number of seconds a connection or command may take before it fails.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: int = 0,
        username: str | None = None,
        password: str | None = None,
        timeout_seconds: float = 30.0,
    ):
        """Initialises the settings.

        Args:
            host: The str host Redis listens on.
            port: The int port Redis listens on.
            database: The int Redis database number.
            username: The str user to log in as, or None.
            password: The str password, or None.
            timeout_seconds: The float number of seconds a connection or command may take.

        Raises:
            Nothing.
        """
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds

    def __repr__(self) -> str:
        """Describes the settings without revealing the password.

        Returns:
            A str with the host, port, database and user.

        Raises:
            Nothing.
        """
        return (
            f"RedisSettings(host={self.host!r}, port={self.port!r}, "
            f"database={self.database!r}, username={self.username!r})"
        )


class MongoSettings:
    """The address and login of UBI's MongoDB.

    Attributes:
        host: The str host MongoDB listens on, such as `127.0.0.1`.
        port: The int port MongoDB listens on.
        database_name: The str name of UBI's database.
        username: The str user to log in as, or None.
        password: The str password, or None.
        timeout_seconds: The float number of seconds server selection, connecting or a query may take before it fails.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database_name: str,
        username: str | None = None,
        password: str | None = None,
        timeout_seconds: float = 30.0,
    ):
        """Initialises the settings.

        Args:
            host: The str host MongoDB listens on.
            port: The int port MongoDB listens on.
            database_name: The str name of UBI's database.
            username: The str user to log in as, or None.
            password: The str password, or None.
            timeout_seconds: The float number of seconds each MongoDB operation may take.

        Raises:
            Nothing.
        """
        self.host = host
        self.port = port
        self.database_name = database_name
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds

    def __repr__(self) -> str:
        """Describes the settings without revealing the password.

        Returns:
            A str with the host, port, database and user.

        Raises:
            Nothing.
        """
        return (
            f"MongoSettings(host={self.host!r}, port={self.port!r}, "
            f"database_name={self.database_name!r}, username={self.username!r})"
        )
