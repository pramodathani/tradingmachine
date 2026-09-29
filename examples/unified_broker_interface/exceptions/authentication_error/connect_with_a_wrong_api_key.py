"""Connect to UBI with a wrong api key and handle the AuthenticationError.

The client reads its api key and secret from a settings document in MongoDB. The program writes a settings document with a wrong key and secret into a separate, temporary database, points a client at that database, and connects. UBI answers HTTP 401 without touching the access token other clients are using, the client raises AuthenticationError, and the program prints it. The temporary database is dropped at the end whatever happens.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/authentication_error/connect_with_a_wrong_api_key.py
"""

import os

import pymongo

from tradingmachine.unified_broker_interface import client
from tradingmachine.unified_broker_interface import exceptions
from tradingmachine.utilities import configuration


class WrongApiKeyConnection:
    """A connection attempt with credentials UBI does not accept.

    Attributes:
        project_configuration: The configuration.Configuration of the real project, used to reach MongoDB.
        temporary_database_name: The str name of the database the wrong credentials are written to.
    """

    def __init__(self):
        """Creates the attempt with the project's configuration.

        Raises:
            Nothing.
        """
        self.project_configuration = configuration.Configuration()
        self.temporary_database_name = "tradingmachine_examples_wrong_api_key"

    def write_wrong_credentials(self) -> None:
        """Writes a settings document with a wrong api key and secret to the temporary database.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached or refused the write.
        """
        with pymongo.MongoClient(
            self.project_configuration.mongodb_connection_string
        ) as mongo_client:
            mongo_client[self.temporary_database_name]["settings"].insert_one(
                {
                    "broker_name": "unified_broker_interface",
                    "api_key": "not-the-real-api-key",
                    "api_secret": "not-the-real-api-secret",
                }
            )

    def drop_temporary_database(self) -> None:
        """Drops the temporary database.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.
        """
        with pymongo.MongoClient(
            self.project_configuration.mongodb_connection_string
        ) as mongo_client:
            mongo_client.drop_database(self.temporary_database_name)

    def run(self) -> None:
        """Connects with the wrong credentials and prints UBI's refusal.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI failed for a reason other than the credentials.
        """
        self.write_wrong_credentials()
        try:
            os.environ["TRADINGMACHINE_MONGODB_DB"] = self.temporary_database_name
            wrong_client = client.UnifiedBrokerInterface(
                project_configuration=configuration.Configuration(),
            )
            try:
                wrong_client.connect()
            except exceptions.AuthenticationError as error:
                print(f"AuthenticationError ({error.status_code}): {error.message}")
                return
            print("Unexpectedly connected with the wrong credentials.")
        finally:
            self.drop_temporary_database()


if __name__ == "__main__":
    WrongApiKeyConnection().run()
