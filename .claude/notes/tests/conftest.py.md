# tests/conftest.py

The shared fixtures build a configuration from environment variables set with `monkeypatch.setenv`, and create it with `load_environment_file=False`. This keeps the developer's own `.env` out of every test: `Configuration` would otherwise load it with `python-dotenv`, and because `load_dotenv` never overrides a variable that is already set, the monkeypatched values win either way, but not loading the file at all means a test can never depend on it.
