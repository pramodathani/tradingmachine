"""Runs every documented example against the live UBI and reports which ones work.

There are two kinds of example. Each property and method carries code blocks in the `Examples:` section of its docstring, and each class has example programs under `examples/`. Every docstring code block and every program is run on its own, in a fresh interpreter from the project root, one at a time. A lock file shared by every copy of this script keeps two examples from running at once, because every new client replaces UBI's single access token and would log the other one out.

An example that acts on the account as a whole rather than on what it created itself, which is any call to `flatten`, `liquidate_all_positions`, `add_to_holdings`, `reduce_holdings`, `liquidate_holdings` or `rebalance`, is held back unless `--include-account-wide` is given, because running it closes positions or sells holdings that were there before, or buys into a holding that cannot simply be cancelled.

Typical usage example:

  .venv/bin/python scripts/run_examples.py --only tradingmachine.accounts --only examples/accounts
  .venv/bin/python scripts/run_examples.py --report /tmp/examples.json
"""

import argparse
import ast
import dataclasses
import fcntl
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
import time

PROJECT_ROOT = pathlib.Path(__file__).parent.parent

SOURCE_ROOT = PROJECT_ROOT / "src"

EXAMPLES_ROOT = PROJECT_ROOT / "examples"

PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

LOCK_PATH = pathlib.Path(tempfile.gettempdir()) / "tradingmachine-examples.lock"

DEFAULT_TIMEOUT_SECONDS = 300

OUTPUT_TAIL_CHARACTERS = 3000

ACCOUNT_WIDE_PATTERN = re.compile(
    r"\.(flatten|liquidate_all_positions|add_to_holdings|reduce_holdings|liquidate_holdings|rebalance)\("
)

SECTION_HEADING_PATTERN = re.compile(r"^[A-Z][A-Za-z ]*:$")

CODE_BLOCK_PATTERN = re.compile(r"```python\n(.*?)```", re.DOTALL)


@dataclasses.dataclass
class Example:
    """One piece of example code to run.

    Attributes:
        identifier: The str name of the example, such as `tradingmachine.accounts.account.Account.parents#1` or `examples/accounts/account/account/open_parents_report.py`.
        code: The str Python source to run, or None for a program that is run from its file.
        path: The pathlib.Path of the program, or None for a docstring code block.
        result: The str outcome once run: `passed`, `failed`, `timed out` or `held back`, or None before it runs.
        seconds: The float time the run took.
        output: The str tail of the run's standard output.
        errors: The str tail of the run's standard error.
    """

    identifier: str
    code: str | None = None
    path: pathlib.Path | None = None
    result: str | None = None
    seconds: float = 0.0
    output: str = ""
    errors: str = ""

    def source(self) -> str:
        """The example's Python source, read from its file when it is a program.

        Returns:
            The str source.

        Raises:
            OSError: The program's file cannot be read.
        """
        if self.code is not None:
            return self.code
        return self.path.read_text()

    def is_account_wide(self) -> bool:
        """Whether the example acts on the account as a whole rather than on what it created.

        Returns:
            True when the source calls one of the account-wide members, otherwise False.

        Raises:
            OSError: The program's file cannot be read.
        """
        return ACCOUNT_WIDE_PATTERN.search(self.source()) is not None


class DocstringExampleCollector:
    """A reader of the code blocks in the `Examples:` sections of the library's docstrings."""

    def collect(self) -> list[Example]:
        """Reads every module under `src/tradingmachine`.

        Returns:
            A list of Example, in the order of the files and then of the code within each file.

        Raises:
            SyntaxError: A module cannot be parsed.
        """
        examples = []
        for path in sorted((SOURCE_ROOT / "tradingmachine").rglob("*.py")):
            module_parts = list(path.relative_to(SOURCE_ROOT).with_suffix("").parts)
            if module_parts[-1] == "__init__":
                module_parts = module_parts[:-1]
            module_name = ".".join(module_parts)
            tree = ast.parse(path.read_text())
            self._collect_from_body(tree.body, module_name, examples)
        return examples

    def _collect_from_body(
        self, body: list, prefix: str, examples: list[Example]
    ) -> None:
        """Reads the classes and functions in one block of code, and the classes' own bodies.

        Args:
            body: The list of ast statements to read.
            prefix: The str dotted name the statements belong to.
            examples: The list of Example the found code blocks are appended to.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for node in body:
            if not isinstance(
                node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            name = f"{prefix}.{node.name}"
            docstring = ast.get_docstring(node) or ""
            blocks = self.code_blocks(docstring)
            for index, block in enumerate(blocks, start=1):
                examples.append(Example(identifier=f"{name}#{index}", code=block))
            if isinstance(node, ast.ClassDef):
                self._collect_from_body(node.body, name, examples)

    @staticmethod
    def code_blocks(docstring: str) -> list[str]:
        """Finds the Python code blocks in a docstring's `Examples:` section.

        Args:
            docstring: The str docstring, with its indentation already removed.

        Returns:
            A list of str, the dedented code of each block.

        Raises:
            Nothing.
        """
        section_lines = []
        inside = False
        for line in docstring.splitlines():
            if line.strip() == "Examples:" and not line.startswith(" "):
                inside = True
                continue
            if inside and SECTION_HEADING_PATTERN.match(line):
                inside = False
            if inside:
                section_lines.append(line)
        section = textwrap.dedent("\n".join(section_lines))
        blocks = []
        for match in CODE_BLOCK_PATTERN.finditer(section):
            blocks.append(textwrap.dedent(match.group(1)))
        return blocks


class ProgramCollector:
    """A finder of the example programs under `examples/`."""

    def collect(self) -> list[Example]:
        """Lists every program.

        Returns:
            A list of Example, sorted by path.

        Raises:
            Nothing.
        """
        examples = []
        if not EXAMPLES_ROOT.is_dir():
            return examples
        for path in sorted(EXAMPLES_ROOT.rglob("*.py")):
            identifier = path.relative_to(PROJECT_ROOT).as_posix()
            examples.append(Example(identifier=identifier, path=path))
        return examples


class ExampleRunner:
    """A runner of examples, one at a time, that records how each one ended.

    Attributes:
        timeout_seconds: The int number of seconds an example may run before it is stopped.
        include_account_wide: A bool, True to run the account-wide examples instead of holding them back.
        show_output: A bool, True to print each example's output as it finishes.
    """

    def __init__(
        self, timeout_seconds: int, include_account_wide: bool, show_output: bool
    ):
        """Stores how the examples are to be run.

        Args:
            timeout_seconds: The int number of seconds an example may run.
            include_account_wide: A bool, True to run account-wide examples.
            show_output: A bool, True to print each example's output.

        Raises:
            Nothing.
        """
        self.timeout_seconds = timeout_seconds
        self.include_account_wide = include_account_wide
        self.show_output = show_output

    def run(self, example: Example) -> None:
        """Runs one example and records its result on it.

        Args:
            example: The Example to run.

        Returns:
            None.

        Raises:
            OSError: The lock file or the program cannot be opened.
        """
        if example.is_account_wide() and not self.include_account_wide:
            example.result = "held back"
            return
        if example.path is None:
            command = [
                str(PYTHON),
                "-c",
                example.code,
            ]
        else:
            command = [
                str(PYTHON),
                str(example.path),
            ]
        with open(LOCK_PATH, "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            started = time.monotonic()
            try:
                completed = subprocess.run(
                    command,
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as error:
                example.result = "timed out"
                example.output = self._tail(error.stdout)
                example.errors = self._tail(error.stderr)
            else:
                if completed.returncode == 0:
                    example.result = "passed"
                else:
                    example.result = "failed"
                example.output = self._tail(completed.stdout)
                example.errors = self._tail(completed.stderr)
            example.seconds = time.monotonic() - started

    @staticmethod
    def _tail(text: str | bytes | None) -> str:
        """Keeps the end of a run's output, which is where an error's cause is printed.

        Args:
            text: The str or bytes output, or None when there was none.

        Returns:
            The str last characters of the output.

        Raises:
            Nothing.
        """
        if text is None:
            return ""
        if isinstance(text, bytes):
            text = text.decode(errors="replace")
        return text[-OUTPUT_TAIL_CHARACTERS:]


class ExamplesApplication:
    """The command line program that collects, filters, runs and reports the examples.

    Attributes:
        arguments: The argparse.Namespace of the parsed command line.
    """

    def __init__(self, argument_list: list[str] | None = None):
        """Parses the command line.

        Args:
            argument_list: A list of str arguments, or None to read `sys.argv`.

        Raises:
            SystemExit: The command line is not valid, or `--help` was given.
        """
        parser = argparse.ArgumentParser(
            description="Run the documented examples against the live UBI."
        )
        parser.add_argument(
            "--only",
            action="append",
            default=[],
            help="Run only examples whose identifier starts with this text; may be given more than once.",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List the matching examples without running them.",
        )
        parser.add_argument(
            "--include-account-wide",
            action="store_true",
            help="Also run examples that act on the whole account's positions or holdings.",
        )
        parser.add_argument(
            "--show-output",
            action="store_true",
            help="Print every example's output, not only the failures'.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=DEFAULT_TIMEOUT_SECONDS,
            help="Seconds an example may run before it is stopped.",
        )
        parser.add_argument(
            "--report", type=pathlib.Path, help="Write every result to this JSON file."
        )
        self.arguments = parser.parse_args(argument_list)

    def _selected(self) -> list[Example]:
        """Collects every example and keeps the ones the command line asked for.

        Returns:
            A list of Example.

        Raises:
            SyntaxError: A module cannot be parsed.
        """
        examples = DocstringExampleCollector().collect() + ProgramCollector().collect()
        if not self.arguments.only:
            return examples
        selected = []
        for example in examples:
            for prefix in self.arguments.only:
                if example.identifier.startswith(prefix):
                    selected.append(example)
                    break
        return selected

    def run(self) -> int:
        """Runs the selected examples and prints a line for each and a summary.

        Returns:
            The int exit status: 0 when nothing failed or timed out, otherwise 1.

        Raises:
            SyntaxError: A module cannot be parsed.
            OSError: The lock file, a program or the report cannot be opened.
        """
        examples = self._selected()
        if self.arguments.list:
            for example in examples:
                print(example.identifier)
            print(f"{len(examples)} examples")
            return 0
        runner = ExampleRunner(
            self.arguments.timeout,
            self.arguments.include_account_wide,
            self.arguments.show_output,
        )
        counts = {}
        for example in examples:
            runner.run(example)
            counts[example.result] = counts.get(example.result, 0) + 1
            print(
                f"{example.result:>10}  {example.seconds:6.1f}s  {example.identifier}",
                flush=True,
            )
            if example.result in ("failed", "timed out") or self.arguments.show_output:
                if example.output:
                    print(textwrap.indent(example.output.rstrip(), "            | "))
                if example.errors and example.result != "passed":
                    print(textwrap.indent(example.errors.rstrip(), "            ! "))
        summary = []
        for result, count in sorted(counts.items()):
            summary.append(f"{count} {result}")
        print(f"{len(examples)} examples: {', '.join(summary)}")
        if self.arguments.report is not None:
            rows = []
            for example in examples:
                rows.append(
                    {
                        "identifier": example.identifier,
                        "result": example.result,
                        "seconds": round(example.seconds, 1),
                        "output": example.output,
                        "errors": example.errors,
                    }
                )
            self.arguments.report.write_text(json.dumps(rows, indent=2))
        if counts.get("failed", 0) or counts.get("timed out", 0):
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(ExamplesApplication().run())
