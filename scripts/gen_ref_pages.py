"""Builds the API reference pages from the source tree, at documentation build time.

There is one page per module and every page is generated, so a module added anywhere under `src/tradingmachine` appears in the reference without anyone remembering to list it. Nothing produced here is written into the project: `mkdocs_gen_files` holds the pages in memory for the length of the build, and the section's navigation is written to `reference/SUMMARY.md` for the literate-nav plugin to read.

Typical usage example:

  plugins:
    - gen-files:
        scripts:
          - scripts/gen_ref_pages.py
"""

import pathlib

import mkdocs_gen_files

SOURCE_DIRECTORY = "src"

PACKAGES = ("tradingmachine",)

EXCLUDED_PARTS = ("__pycache__",)


class ReferencePageBuilder:
    """A builder of one reference page per module in the project's packages.

    Attributes:
        root: The pathlib.Path of the project root, which is the parent of this file's directory.
        source_root: The pathlib.Path of the directory the packages are imported from, which is `src` under the project root.
        navigation: The mkdocs_gen_files.Nav the reference section's navigation is collected into.
    """

    def __init__(self, root: pathlib.Path | None = None):
        """Prepares the builder with the root to walk and an empty navigation.

        Args:
            root: The pathlib.Path of the project root, or None to use the parent of this file's directory.

        Raises:
            Nothing.
        """
        if root is None:
            root = pathlib.Path(__file__).parent.parent
        self.root = root
        self.source_root = root / SOURCE_DIRECTORY
        self.navigation = mkdocs_gen_files.Nav()

    def build(self) -> None:
        """Writes a reference page for every module, then the section's navigation file.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for package in PACKAGES:
            for path in sorted((self.source_root / package).rglob("*.py")):
                self._build_page_for(path)
        self._write_navigation()

    def _build_page_for(self, path: pathlib.Path) -> None:
        """Writes the reference page for one module, unless the module is excluded.

        Args:
            path: The pathlib.Path of the module's source file.

        Returns:
            None.

        Raises:
            Nothing.
        """
        module_path = path.relative_to(self.source_root).with_suffix("")
        for part in module_path.parts:
            if part in EXCLUDED_PARTS:
                return
        parts = tuple(module_path.parts)
        documentation_path = module_path.with_suffix(".md")
        if parts[-1] == "__init__":
            parts = parts[:-1]
            documentation_path = documentation_path.with_name("index.md")
            if not path.read_text().strip():
                return
        elif parts[-1].startswith("__"):
            return
        if not parts:
            return
        self.navigation[parts] = documentation_path.as_posix()
        page_path = pathlib.Path("reference") / documentation_path
        with mkdocs_gen_files.open(page_path, "w") as page:
            dotted_path = ".".join(parts)
            page.write(f"::: {dotted_path}\n")
        mkdocs_gen_files.set_edit_path(
            page_path,
            path.relative_to(self.root),
        )

    def _write_navigation(self) -> None:
        """Writes the reference section's navigation to `reference/SUMMARY.md`.

        Returns:
            None.

        Raises:
            Nothing.
        """
        with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as summary:
            summary.writelines(self.navigation.build_literate_nav())


ReferencePageBuilder().build()
