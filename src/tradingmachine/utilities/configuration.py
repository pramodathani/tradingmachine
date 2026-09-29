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

        Examples:
            Make the configuration read the `.env` file again after a variable was removed from the process environment:

            ```python
            import os

            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            print(project_configuration.ubi_base_url)
            del os.environ["TRADINGMACHINE_UBI_BASE_URL"]
            print(project_configuration.ubi_base_url)
            project_configuration.reload()
            print(project_configuration.ubi_base_url)
            ```

            Pick up a variable that was added to an environment file after the first read:

            ```python
            import os
            import tempfile

            from tradingmachine.utilities import configuration

            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "example.env")
                with open(path, "w") as environment_file:
                    print(
                        "TRADINGMACHINE_UBI_BASE_URL=http://127.0.0.1:8080",
                        file=environment_file,
                    )
                project_configuration = configuration.Configuration(
                    environment_file=path
                )
                print(f"Host before: {project_configuration.mongodb_host}")
                with open(path, "a") as environment_file:
                    print(
                        "TRADINGMACHINE_MONGODB_HOST=127.0.0.1",
                        file=environment_file,
                    )
                project_configuration.reload()
                print(f"Host after reload: {project_configuration.mongodb_host}")
            ```
        """
        self._environment_file_loaded = False

    @property
    def ubi_base_url(self) -> str | None:
        """The str address of the Unified Broker Interface, or None if it is not set.

        Examples:
            Print the address of UBI that the project's `.env` file names:

            ```python
            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            print(project_configuration.ubi_base_url)
            ```

            Read the address from a variable exported by the caller, without loading any file:

            ```python
            import os

            from tradingmachine.utilities import configuration

            os.environ["TRADINGMACHINE_UBI_BASE_URL"] = "http://127.0.0.1:8080"
            project_configuration = configuration.Configuration(
                load_environment_file=False
            )
            print(project_configuration.ubi_base_url)
            ```

            Stop early with a clear message when the address is not configured:

            ```python
            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            if project_configuration.ubi_base_url is None:
                print("Set TRADINGMACHINE_UBI_BASE_URL in .env first.")
            else:
                print(f"UBI is expected at {project_configuration.ubi_base_url}")
            ```
        """
        return self._read(UBI_BASE_URL_VARIABLE)

    @property
    def mongodb_host(self) -> str | None:
        """The str host MongoDB is reachable on, or None if it is not set.

        Examples:
            Print the host MongoDB is reached on:

            ```python
            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            print(project_configuration.mongodb_host)
            ```

            Read the host from a separate environment file, such as one for another machine:

            ```python
            import os
            import tempfile

            from tradingmachine.utilities import configuration

            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "other_machine.env")
                with open(path, "w") as environment_file:
                    print(
                        "TRADINGMACHINE_MONGODB_HOST=192.168.1.20",
                        file=environment_file,
                    )
                project_configuration = configuration.Configuration(
                    environment_file=path
                )
                print(project_configuration.mongodb_host)
            ```
        """
        return self._read(MONGODB_HOST_VARIABLE)

    @property
    def mongodb_port(self) -> str | None:
        """The str port MongoDB listens on, or None if it is not set.

        Examples:
            Print the port MongoDB listens on:

            ```python
            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            print(project_configuration.mongodb_port)
            ```

            Turn the port into a number, because every setting is read as text:

            ```python
            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            port = int(project_configuration.mongodb_port)
            in_range = 2000 <= port < 3000
            print(f"MongoDB port {port} is in the project's range: {in_range}")
            ```
        """
        return self._read(MONGODB_PORT_VARIABLE)

    @property
    def mongodb_database_name(self) -> str | None:
        """The str name of the project's MongoDB database, or None if it is not set.

        Examples:
            Print the name of the project's database:

            ```python
            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            print(project_configuration.mongodb_database_name)
            ```

            Count the stored baskets in the project's database:

            ```python
            import pymongo

            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            connection_string = project_configuration.mongodb_connection_string
            database_name = project_configuration.mongodb_database_name
            with pymongo.MongoClient(connection_string) as mongo_client:
                collection = mongo_client[database_name]["asset_baskets"]
                print(f"Stored baskets: {collection.count_documents({})}")
            ```
        """
        return self._read(MONGODB_DATABASE_NAME_VARIABLE)

    @property
    def mongodb_username(self) -> str | None:
        """The str MongoDB user to authenticate as, or None if it is not set.

        Examples:
            Print the user the library authenticates to MongoDB as:

            ```python
            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            print(project_configuration.mongodb_username)
            ```

            Check that a user is configured before connecting:

            ```python
            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            if project_configuration.mongodb_username:
                print("A MongoDB user is configured.")
            else:
                print("Set TRADINGMACHINE_MONGODB_USERNAME in .env first.")
            ```
        """
        return self._read(MONGODB_USERNAME_VARIABLE)

    @property
    def mongodb_password(self) -> str | None:
        """The str password for the MongoDB user, or None if it is not set.

        Examples:
            Check that a password is configured without printing it:

            ```python
            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            password = project_configuration.mongodb_password
            print(f"A MongoDB password is set: {password is not None}")
            ```

            Report the password's length only, so that it never appears in a log:

            ```python
            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            password = project_configuration.mongodb_password or ""
            print(f"The MongoDB password has {len(password)} characters.")
            ```
        """
        return self._read(MONGODB_PASSWORD_VARIABLE)

    @property
    def mongodb_connection_string(self) -> str:
        """The str MongoDB URI built from the host, port, username and password.

        Examples:
            Print the part of the connection string after the credentials, which is safe to show:

            ```python
            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            connection_string = project_configuration.mongodb_connection_string
            print(connection_string.split("@")[1])
            ```

            Connect to MongoDB with it and ask the server whether it is alive:

            ```python
            import pymongo

            from tradingmachine.utilities import configuration

            project_configuration = configuration.Configuration()
            connection_string = project_configuration.mongodb_connection_string
            with pymongo.MongoClient(connection_string) as mongo_client:
                print(mongo_client.admin.command("ping"))
            ```
        """
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
