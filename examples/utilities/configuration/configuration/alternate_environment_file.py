"""Read settings from an environment file other than the project's `.env`.

The program writes a temporary environment file for a second machine, builds a `Configuration` that reads it, prints the settings it finds, then adds the MongoDB port to the file and calls `reload` so that the new variable is picked up. The temporary file is removed when the program ends.

A variable already set in the process environment is not replaced when a file is loaded or reloaded, which is why the program adds a variable rather than changing one.

Typical usage example:

  .venv/bin/python examples/utilities/configuration/configuration/alternate_environment_file.py
"""

import os
import tempfile

from tradingmachine.utilities import configuration


class AlternateEnvironmentFile:
    """Settings read from a temporary environment file.

    Attributes:
        path: The str path of the environment file, or None until the program runs.
    """

    def __init__(self):
        """Starts without a file, which run writes in a temporary directory.

        Raises:
            Nothing.
        """
        self.path = None

    def write_line(self, line: str) -> None:
        """Appends one `NAME=value` line to the environment file.

        Args:
            line: The str line to append, without a line ending.

        Returns:
            None.

        Raises:
            OSError: The file could not be written.
        """
        with open(self.path, "a") as environment_file:
            print(line, file=environment_file)

    def print_settings(
        self, project_configuration: configuration.Configuration
    ) -> None:
        """Prints the UBI address and the MongoDB host and port the configuration sees.

        Args:
            project_configuration: The tradingmachine.utilities.configuration.Configuration to read.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(f"  UBI base url: {project_configuration.ubi_base_url}")
        print(f"  MongoDB host: {project_configuration.mongodb_host}")
        print(f"  MongoDB port: {project_configuration.mongodb_port}")

    def run(self) -> None:
        """Writes the file in a temporary directory, reads it, extends it and reloads it.

        Returns:
            None.

        Raises:
            OSError: The file could not be written.
        """
        with tempfile.TemporaryDirectory() as directory:
            self.path = os.path.join(directory, "second_machine.env")
            self.write_line("TRADINGMACHINE_UBI_BASE_URL=http://192.168.1.20:8080")
            self.write_line("TRADINGMACHINE_MONGODB_HOST=192.168.1.20")
            project_configuration = configuration.Configuration(
                environment_file=self.path
            )
            print("First read:")
            self.print_settings(project_configuration)
            self.write_line("TRADINGMACHINE_MONGODB_PORT=2003")
            project_configuration.reload()
            print("After adding the port and reloading:")
            self.print_settings(project_configuration)


if __name__ == "__main__":
    AlternateEnvironmentFile().run()
