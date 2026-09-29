"""Check two sets of credentials before trading, catching UnifiedBrokerInterfaceError.

A program that trades should find out at the start whether its credentials work, rather than on its first order. The program checks the real credentials and a wrong set written to a temporary database, by sending one request through a client built on each. The wrong set raises AuthenticationError, which is caught through the base class UnifiedBrokerInterfaceError and recognised by its status code 401. The temporary database is dropped at the end whatever happens.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/authentication_error/check_credentials_before_trading.py
"""

import os

import pymongo

from tradingmachine.unified_broker_interface import client
from tradingmachine.unified_broker_interface import exceptions
from tradingmachine.utilities import configuration


class CredentialCheck:
    """A check of whether each of two sets of credentials is accepted by UBI.

    Attributes:
        project_configuration: The configuration.Configuration of the real project.
        real_database_name: The str name of the project's own MongoDB database.
        temporary_database_name: The str name of the database the wrong credentials are written to.
    """

    def __init__(self):
        """Creates the check with the project's configuration.

        Raises:
            Nothing.
        """
        self.project_configuration = configuration.Configuration()
        self.real_database_name = self.project_configuration.mongodb_database_name
        self.temporary_database_name = "tradingmachine_examples_wrong_credentials"

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
                    "api_key": "a-key-that-was-rotated",
                    "api_secret": "a-secret-that-was-rotated",
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

    def credentials_work(self, database_name: str) -> bool:
        """Sends one request through a client whose credentials come from a database.

        Args:
            database_name: The str name of the MongoDB database holding the settings document.

        Returns:
            True when UBI accepted the credentials, False when it refused them with HTTP 401.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI failed for a reason other than the credentials.
        """
        os.environ["TRADINGMACHINE_MONGODB_DB"] = database_name
        checked_client = client.UnifiedBrokerInterface(
            project_configuration=configuration.Configuration(),
        )
        try:
            checked_client.status()
        except exceptions.UnifiedBrokerInterfaceError as error:
            if error.status_code != 401:
                raise
            print(
                f"{database_name}: refused with {type(error).__name__}: {error.message}"
            )
            return False
        print(f"{database_name}: accepted")
        return True

    def run(self) -> None:
        """Checks both sets of credentials and prints whether trading can start.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI failed for a reason other than the credentials.
        """
        self.write_wrong_credentials()
        try:
            real_works = self.credentials_work(self.real_database_name)
            wrong_works = self.credentials_work(self.temporary_database_name)
        finally:
            os.environ["TRADINGMACHINE_MONGODB_DB"] = self.real_database_name
            self.drop_temporary_database()
        print(f"Real credentials can trade: {real_works}")
        print(f"Rotated credentials can trade: {wrong_works}")


if __name__ == "__main__":
    CredentialCheck().run()
