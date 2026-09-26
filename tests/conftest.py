"""Shared pytest fixtures: a running fake UBI server and a configuration pointing at it."""

import collections.abc

import pymongo
import pytest

from tests import fake_ubi_server
from tests import fakes
from tradingmachine.utilities import configuration

DATABASE_NAME = "tradingmachine_test"


@pytest.fixture
def ubi_server() -> collections.abc.Iterator[
    fake_ubi_server.FakeUnifiedBrokerInterfaceServer
]:
    """Runs a fake UBI server for one test.

    Yields:
        The running fake_ubi_server.FakeUnifiedBrokerInterfaceServer.

    Raises:
        OSError: No local port could be opened.
    """
    with fake_ubi_server.FakeUnifiedBrokerInterfaceServer() as server:
        yield server


@pytest.fixture
def mongo_factory(monkeypatch: pytest.MonkeyPatch) -> fakes.FakeMongoClientFactory:
    """Replaces pymongo.MongoClient with a factory whose settings hold the fake server's key and secret.

    Args:
        monkeypatch: The pytest.MonkeyPatch for this test.

    Returns:
        The fakes.FakeMongoClientFactory now standing in for pymongo.MongoClient.

    Raises:
        Nothing.
    """
    factory = fakes.FakeMongoClientFactory(
        fakes.SettingsDatabase.with_credentials(DATABASE_NAME)
    )
    monkeypatch.setattr(pymongo, "MongoClient", factory)
    return factory


@pytest.fixture
def project_configuration(
    monkeypatch: pytest.MonkeyPatch,
    ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
) -> configuration.Configuration:
    """Builds a configuration from environment variables that point at the fake server and a fake MongoDB.

    Args:
        monkeypatch: The pytest.MonkeyPatch for this test.
        ubi_server: The running fake UBI server.

    Returns:
        A configuration.Configuration that never loads a `.env` file.

    Raises:
        Nothing.
    """
    monkeypatch.setenv(configuration.UBI_BASE_URL_VARIABLE, ubi_server.base_url)
    monkeypatch.setenv(configuration.MONGODB_HOST_VARIABLE, "127.0.0.1")
    monkeypatch.setenv(configuration.MONGODB_PORT_VARIABLE, "2003")
    monkeypatch.setenv(configuration.MONGODB_DATABASE_NAME_VARIABLE, DATABASE_NAME)
    monkeypatch.setenv(configuration.MONGODB_USERNAME_VARIABLE, "user")
    monkeypatch.setenv(configuration.MONGODB_PASSWORD_VARIABLE, "password")
    return configuration.Configuration(load_environment_file=False)
