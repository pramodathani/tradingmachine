"""Configuration for the services the library talks to, read from the environment.

`Configuration` is the one place that knows which environment variable holds which setting. Nothing is read when this module is imported: the first property access loads the `.env` file, if there is one, and every value is read from the process environment at that moment. A caller that keeps its settings somewhere else can point the object at a different file, or export the variables itself and never let a file be loaded at all.

Typical usage example:

  from tradingmachine.utilities import configuration

  project_configuration = configuration.Configuration()
  base_url = project_configuration.ubi_base_url
"""

import os
import urllib.parse

import dotenv

UBI_BASE_URL_VARIABLE = "TRADINGMACHINE_UBI_BASE_URL"

MONGODB_HOST_VARIABLE = "TRADINGMACHINE_MONGODB_HOST"
MONGODB_PORT_VARIABLE = "TRADINGMACHINE_MONGODB_PORT"
MONGODB_DATABASE_NAME_VARIABLE = "TRADINGMACHINE_MONGODB_DB"
MONGODB_USERNAME_VARIABLE = "TRADINGMACHINE_MONGODB_USERNAME"
MONGODB_PASSWORD_VARIABLE = "TRADINGMACHINE_MONGODB_PASSWORD"


class Configuration:
    """The settings for one process, read from the environment on first use.

    Attributes:
        environment_file: The str path of the `.env` file to load, or None to search the working directory and its parents for a file named `.env`.
    """

    def __init__(
        self,
        environment_file: str | None = None,
        load_environment_file: bool = True,
    ):
        """Prepares the configuration without reading anything yet.

        Args:
            environment_file: The str path of the `.env` file to load, or None to search the working directory and its parents for a file named `.env`.
            load_environment_file: Whether to load a `.env` file at all. Pass False when the variables are already exported into the process environment and no file should be looked for.

        Raises:
            Nothing.
        """
        self.environment_file = environment_file
        self._load_environment_file = load_environment_file
        self._environment_file_loaded = False

    def reload(self) -> None:
        """Forgets that the environment file was loaded, so the next read loads it again.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._environment_file_loaded = False

    @property
    def ubi_base_url(self) -> str | None:
        """The str address of the Unified Broker Interface, or None if it is not set."""
        return self._read(UBI_BASE_URL_VARIABLE)

    @property
    def mongodb_host(self) -> str | None:
        """The str host MongoDB is reachable on, or None if it is not set."""
        return self._read(MONGODB_HOST_VARIABLE)

    @property
    def mongodb_port(self) -> str | None:
        """The str port MongoDB listens on, or None if it is not set."""
        return self._read(MONGODB_PORT_VARIABLE)

    @property
    def mongodb_database_name(self) -> str | None:
        """The str name of the project's MongoDB database, or None if it is not set."""
        return self._read(MONGODB_DATABASE_NAME_VARIABLE)

    @property
    def mongodb_username(self) -> str | None:
        """The str MongoDB user to authenticate as, or None if it is not set."""
        return self._read(MONGODB_USERNAME_VARIABLE)

    @property
    def mongodb_password(self) -> str | None:
        """The str password for the MongoDB user, or None if it is not set."""
        return self._read(MONGODB_PASSWORD_VARIABLE)

    @property
    def mongodb_connection_string(self) -> str:
        """The str MongoDB URI built from the host, port, username and password."""
        username = urllib.parse.quote_plus(self.mongodb_username or "")
        password = urllib.parse.quote_plus(self.mongodb_password or "")
        return (
            f"mongodb://{username}:{password}"
            f"@{self.mongodb_host}:{self.mongodb_port}"
            "/?authSource=admin"
        )

    def _read(self, variable_name: str) -> str | None:
        """Reads one environment variable, loading the environment file first if needed.

        Args:
            variable_name: The str name of the environment variable to read.

        Returns:
            The str value of the variable, or None when it is not set.

        Raises:
            Nothing.
        """
        self._ensure_environment_file_loaded()
        return os.getenv(variable_name)

    def _ensure_environment_file_loaded(self) -> None:
        """Loads the environment file once, if loading it was asked for.

        Returns:
            None.

        Raises:
            Nothing.
        """
        if self._environment_file_loaded:
            return
        self._environment_file_loaded = True
        if not self._load_environment_file:
            return
        dotenv.load_dotenv(self.environment_file)
