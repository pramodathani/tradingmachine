"""Report the project's settings and check that MongoDB answers with them.

The program reads every setting `Configuration` knows from the environment and the `.env` file, prints each one with the password hidden, and then connects to MongoDB with the connection string to confirm that the settings work.

Typical usage example:

  .venv/bin/python examples/utilities/configuration/configuration/configuration_report.py
"""

import pymongo

from tradingmachine.utilities import configuration


class ConfigurationReport:
    """A report of the settings one process would use.

    Attributes:
        project_configuration: The tradingmachine.utilities.configuration.Configuration being reported.
    """

    def __init__(self):
        """Creates the configuration, which reads nothing until the first setting is asked for.

        Raises:
            Nothing.
        """
        self.project_configuration = configuration.Configuration()

    def settings(self) -> dict:
        """Collects every setting, with the password replaced by a note of whether it is set.

        Returns:
            A dict mapping each str setting name to its str value, or to None when it is not set.

        Raises:
            Nothing.
        """
        password_note = "not set"
        if self.project_configuration.mongodb_password:
            password_note = "set, hidden"
        return {
            "UBI base url": self.project_configuration.ubi_base_url,
            "MongoDB host": self.project_configuration.mongodb_host,
            "MongoDB port": self.project_configuration.mongodb_port,
            "MongoDB database": self.project_configuration.mongodb_database_name,
            "MongoDB user": self.project_configuration.mongodb_username,
            "MongoDB password": password_note,
        }

    def check_mongodb(self) -> None:
        """Connects to MongoDB and prints its answer to a ping and the project's collections.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached or refused the credentials.
        """
        connection_string = self.project_configuration.mongodb_connection_string
        print(f"Connecting to {connection_string.split('@')[1]}")
        database_name = self.project_configuration.mongodb_database_name
        with pymongo.MongoClient(connection_string) as mongo_client:
            print(f"Ping: {mongo_client.admin.command('ping')}")
            names = sorted(mongo_client[database_name].list_collection_names())
            print(f"Collections in {database_name}: {names}")

    def run(self) -> None:
        """Prints the settings, then checks MongoDB.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached or refused the credentials.
        """
        for name, value in self.settings().items():
            print(f"{name:<18} {value}")
        self.check_mongodb()


if __name__ == "__main__":
    ConfigurationReport().run()
