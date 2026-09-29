"""Builds the API reference pages from the source tree, at documentation build time.

There is one page per module and every page is generated, so a module added anywhere under `src/tradingmachine` appears in the reference without anyone remembering to list it. Each page is laid out as a hierarchy: the module is the page title, each public class is a section in the order the module defines it, and each property and method is a subsection of its class in source order, so the page's table of contents lists every class with its members beneath it. The example programs for a class, kept under `examples/` in a folder that mirrors the module and is named after the class, are shown after the class's members. The landing page of the section is a tree of every class by inheritance.

Nothing produced here is written into the project: `mkdocs_gen_files` holds the pages in memory for the length of the build, and the section's navigation is written to `reference/SUMMARY.md` for the literate-nav plugin to read.

Typical usage example:

  plugins:
    - gen-files:
        scripts:
          - scripts/gen_ref_pages.py
"""

import ast
import pathlib
import re

import mkdocs_gen_files

SOURCE_DIRECTORY = "src"

EXAMPLES_DIRECTORY = "examples"

PACKAGES = ("tradingmachine",)

EXCLUDED_PARTS = ("__pycache__",)

INHERITED_DISCOVERY_MEMBERS = (
    "expiries",
    "contracts",
    "strikes",
    "chain",
)

FAMILY_MODULES = (
    "tradingmachine.assets.equities",
    "tradingmachine.assets.fixed_income",
    "tradingmachine.assets.commodities",
    "tradingmachine.assets.currencies",
)

INDEX_MODULE_NAME = "index"

INDEX_MODULE_PAGE_NAME = "index_module.md"

HIERARCHY_PAGE_NAME = "index.md"


class ModuleSource:
    """What the reference needs to know about one module, read from its source without importing it.

    Attributes:
        path: The pathlib.Path of the module's source file.
        dotted_path: The str dotted import path, such as `tradingmachine.assets.equities`.
        class_names: A list of str, the module's public top-level classes in the order the module defines them.
        attribute_names: A list of str, the module's public top-level constants in the order the module defines them.
        base_expressions: A dict mapping each public class name to a list of str, the source text of each of its bases.
        import_aliases: A dict mapping each name the module binds by importing a module to that module's dotted path.
    """

    def __init__(self, path: pathlib.Path, dotted_path: str):
        """Reads the module's classes, constants, bases and imports.

        Args:
            path: The pathlib.Path of the module's source file.
            dotted_path: The str dotted import path of the module.

        Raises:
            SyntaxError: The module's source cannot be parsed.
        """
        self.path = path
        self.dotted_path = dotted_path
        self.class_names = []
        self.attribute_names = []
        self.base_expressions = {}
        self.import_aliases = {}
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                self._read_class(node)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    self._read_attribute(target)
            elif isinstance(node, ast.AnnAssign):
                self._read_attribute(node.target)
            elif isinstance(node, ast.ImportFrom):
                self._read_import_from(node)
            elif isinstance(node, ast.Import):
                self._read_import(node)

    def _read_class(self, node: ast.ClassDef) -> None:
        """Records one top-level class unless its name marks it internal.

        Args:
            node: The ast.ClassDef of the class.

        Returns:
            None.

        Raises:
            Nothing.
        """
        if node.name.startswith("_"):
            return
        self.class_names.append(node.name)
        bases = []
        for base in node.bases:
            bases.append(ast.unparse(base))
        self.base_expressions[node.name] = bases

    def _read_attribute(self, target: ast.expr) -> None:
        """Records one top-level assignment if it binds a public constant.

        Args:
            target: The ast.expr the value is assigned to.

        Returns:
            None.

        Raises:
            Nothing.
        """
        if not isinstance(target, ast.Name):
            return
        if target.id.startswith("_") or not target.id.isupper():
            return
        self.attribute_names.append(target.id)

    def _read_import_from(self, node: ast.ImportFrom) -> None:
        """Records the names a `from package import module` statement binds.

        Args:
            node: The ast.ImportFrom of the statement.

        Returns:
            None.

        Raises:
            Nothing.
        """
        if node.module is None:
            return
        for alias in node.names:
            bound_name = alias.asname or alias.name
            self.import_aliases[bound_name] = f"{node.module}.{alias.name}"

    def _read_import(self, node: ast.Import) -> None:
        """Records the names an `import module` statement binds.

        Args:
            node: The ast.Import of the statement.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for alias in node.names:
            bound_name = alias.asname or alias.name
            self.import_aliases[bound_name] = alias.name

    def resolve_base(self, expression: str) -> str:
        """Turns the source text of a base class into a full dotted path.

        Args:
            expression: The str source text of the base, such as `instruments.TradeableInstrument` or `Exception`.

        Returns:
            The str dotted path of the base, such as `tradingmachine.assets.instruments.TradeableInstrument`, or the expression unchanged when it names nothing this module defines or imports.

        Raises:
            Nothing.
        """
        if expression in self.class_names:
            return f"{self.dotted_path}.{expression}"
        first_name, separator, rest = expression.partition(".")
        if separator and first_name in self.import_aliases:
            return f"{self.import_aliases[first_name]}.{rest}"
        if expression in self.import_aliases:
            return self.import_aliases[expression]
        return expression


class ClassHierarchyPage:
    """The reference section's landing page, a tree of every public class by inheritance.

    Attributes:
        bases: A dict mapping each class's dotted path to a list of str, the dotted paths of its bases.
        module_of_class: A dict mapping each class's dotted path to the str dotted path of its module.
    """

    def __init__(self):
        """Starts with no classes recorded.

        Raises:
            Nothing.
        """
        self.bases = {}
        self.module_of_class = {}

    def add_module(self, module: ModuleSource) -> None:
        """Records every public class of one module with its resolved bases.

        Args:
            module: The ModuleSource to record.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for class_name in module.class_names:
            class_path = f"{module.dotted_path}.{class_name}"
            resolved_bases = []
            for expression in module.base_expressions[class_name]:
                resolved_bases.append(module.resolve_base(expression))
            self.bases[class_path] = resolved_bases
            self.module_of_class[class_path] = module.dotted_path

    def _project_bases(self, class_path: str) -> list[str]:
        """Lists the bases of a class that are themselves classes in this project.

        Args:
            class_path: The str dotted path of the class.

        Returns:
            A list of str dotted paths, in the order the class names them.

        Raises:
            Nothing.
        """
        project_bases = []
        for base in self.bases[class_path]:
            if base in self.bases:
                project_bases.append(base)
        return project_bases

    def _parent(self, class_path: str) -> str | None:
        """Chooses where a class hangs in the tree.

        A class with exactly one base in this project hangs under it. A class with none, or with several side by side, such as `Instrument` with its fourteen analysis classes, is a root of the tree, and its bases are named beside it instead.

        Args:
            class_path: The str dotted path of the class.

        Returns:
            The str dotted path of the parent class, or None for a root.

        Raises:
            Nothing.
        """
        project_bases = self._project_bases(class_path)
        if len(project_bases) == 1:
            return project_bases[0]
        return None

    def _line_for(self, class_path: str, depth: int) -> str:
        """Writes one class as a line of the nested list.

        Args:
            class_path: The str dotted path of the class.
            depth: The int nesting depth, zero for a root.

        Returns:
            The str Markdown line, ending in a newline.

        Raises:
            Nothing.
        """
        short_name = class_path.rsplit(".", 1)[1]
        module_path = self.module_of_class[class_path]
        indent = "    " * depth
        line = f"{indent}- [`{short_name}`][{class_path}] in `{module_path}`"
        project_bases = self._project_bases(class_path)
        external_bases = []
        for base in self.bases[class_path]:
            if base not in self.bases and base != "object":
                external_bases.append(base)
        if len(project_bases) > 1:
            base_names = []
            for base in project_bases:
                base_names.append(f"`{base.rsplit('.', 1)[1]}`")
            line += f", inheriting {', '.join(base_names)}"
        elif not project_bases and external_bases:
            base_names = []
            for base in external_bases:
                base_names.append(f"`{base}`")
            line += f", from {', '.join(base_names)}"
        return line + "\n"

    def _write_branch(
        self, class_path: str, depth: int, children: dict, lines: list
    ) -> None:
        """Writes a class and, beneath it, every class that hangs under it.

        Args:
            class_path: The str dotted path of the class.
            depth: The int nesting depth of the class.
            children: A dict mapping each class's dotted path to a list of str, the classes that hang under it.
            lines: The list of str Markdown lines the branch is appended to.

        Returns:
            None.

        Raises:
            Nothing.
        """
        lines.append(self._line_for(class_path, depth))
        for child in children.get(class_path, []):
            self._write_branch(child, depth + 1, children, lines)

    def markdown(self) -> str:
        """Writes the whole page.

        Returns:
            The str Markdown of the page.

        Raises:
            Nothing.
        """
        children = {}
        roots = []
        for class_path in self.bases:
            parent = self._parent(class_path)
            if parent is None:
                roots.append(class_path)
            else:
                children.setdefault(parent, []).append(class_path)
        lines = [
            "# Class hierarchy\n",
            "\n",
            "This section documents every public class in the library, one page per module. On each page the module comes first, then each class in the order the module defines it, and under each class every property and method in the order it appears in the code, each with examples. The example programs for a class follow its members. The menu on the right of a module page lists its classes with their members beneath them.\n",
            "\n",
            f"The tree below shows all {len(self.bases)} classes by inheritance. A class hangs under its base when it has exactly one base in this library. A class whose bases all come from outside the library, or that inherits several of the library's classes side by side, starts a new branch, and those bases are named beside it.\n",
            "\n",
        ]
        for root in roots:
            self._write_branch(root, 0, children, lines)
        return "".join(lines)


class ReferencePageBuilder:
    """A builder of one reference page per module in the project's packages.

    Attributes:
        root: The pathlib.Path of the project root, which is the parent of this file's directory.
        source_root: The pathlib.Path of the directory the packages are imported from, which is `src` under the project root.
        examples_root: The pathlib.Path of the directory that holds the example programs.
        navigation: The mkdocs_gen_files.Nav the reference section's navigation is collected into.
        hierarchy: The ClassHierarchyPage every module's classes are recorded in.
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
        self.examples_root = root / EXAMPLES_DIRECTORY
        self.navigation = mkdocs_gen_files.Nav()
        self.hierarchy = ClassHierarchyPage()

    def build(self) -> None:
        """Writes a reference page for every module, then the class hierarchy and the section's navigation file.

        Returns:
            None.

        Raises:
            SyntaxError: A module's source cannot be parsed.
        """
        for package in PACKAGES:
            for path in sorted((self.source_root / package).rglob("*.py")):
                self._build_page_for(path)
        with mkdocs_gen_files.open(
            pathlib.Path("reference") / HIERARCHY_PAGE_NAME, "w"
        ) as page:
            page.write(self.hierarchy.markdown())
        self._write_navigation()

    def _build_page_for(self, path: pathlib.Path) -> None:
        """Writes the reference page for one module, unless the module is excluded.

        A package's `__init__.py` becomes the package's `index.md`, so a module that is itself named `index`, such as `tradingmachine.asset_baskets.index`, is written to `index_module.md` instead, or the two pages would share one path.

        Args:
            path: The pathlib.Path of the module's source file.

        Returns:
            None.

        Raises:
            SyntaxError: The module's source cannot be parsed.
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
        elif parts[-1] == INDEX_MODULE_NAME:
            documentation_path = documentation_path.with_name(INDEX_MODULE_PAGE_NAME)
        elif parts[-1].startswith("__"):
            return
        if not parts:
            return
        dotted_path = ".".join(parts)
        module = ModuleSource(path, dotted_path)
        self.hierarchy.add_module(module)
        self.navigation[parts] = documentation_path.as_posix()
        page_path = pathlib.Path("reference") / documentation_path
        with mkdocs_gen_files.open(page_path, "w") as page:
            page.write(self._page_for(module))
        mkdocs_gen_files.set_edit_path(
            page_path,
            path.relative_to(self.root),
        )

    def _page_for(self, module: ModuleSource) -> str:
        """Builds the Markdown of one module's page.

        Args:
            module: The ModuleSource of the module.

        Returns:
            The str Markdown of the page.

        Raises:
            SyntaxError: An example program's source cannot be parsed.
        """
        lines = [
            f"::: {module.dotted_path}",
            "    options:",
            "      heading_level: 1",
            "      show_root_full_path: true",
        ]
        if module.attribute_names:
            lines.append("      members:")
            for attribute_name in module.attribute_names:
                lines.append(f"        - {attribute_name}")
        else:
            lines.append("      members: false")
        lines.append("")
        for class_name in module.class_names:
            lines.extend(self._class_section(module, class_name))
        return "\n".join(lines) + "\n"

    def _class_section(self, module: ModuleSource, class_name: str) -> list[str]:
        """Builds the lines that render one class, its members and its example programs.

        The classes of the four asset family modules also list the discovery class methods their futures and option classes inherit from `tradingmachine.assets.instruments.Futures` and `tradingmachine.assets.instruments.Option`, so those calls stay on each family class without letting in the inherited analysis methods.

        Args:
            module: The ModuleSource the class belongs to.
            class_name: The str name of the class.

        Returns:
            A list of str Markdown lines.

        Raises:
            SyntaxError: An example program's source cannot be parsed.
        """
        lines = [
            f"::: {module.dotted_path}.{class_name}",
            "    options:",
            "      heading_level: 2",
        ]
        if module.dotted_path in FAMILY_MODULES:
            lines.append("      inherited_members:")
            for member in INHERITED_DISCOVERY_MEMBERS:
                lines.append(f"        - {member}")
        lines.append("")
        programs = self._example_programs(module, class_name)
        if programs:
            lines.append("### Example programs")
            lines.append("")
            for program in programs:
                relative_path = program.relative_to(self.root).as_posix()
                lines.append(f"#### {self._program_title(program)}")
                lines.append("")
                lines.append(f"Run it with `.venv/bin/python {relative_path}`.")
                lines.append("")
                lines.append("```python")
                lines.append(f'--8<-- "{relative_path}"')
                lines.append("```")
                lines.append("")
        return lines

    def _example_programs(
        self, module: ModuleSource, class_name: str
    ) -> list[pathlib.Path]:
        """Finds the example programs written for one class.

        A class's programs live in `examples/`, under the module's path without the top-level package, in a folder named after the class in snake case, such as `examples/assets/equities/equity/`.

        Args:
            module: The ModuleSource the class belongs to.
            class_name: The str name of the class.

        Returns:
            A list of pathlib.Path, sorted by file name, empty when the class has none.

        Raises:
            Nothing.
        """
        module_parts = module.dotted_path.split(".")[1:]
        if module.path.name == "__init__.py":
            module_parts.append("__init__")
        folder = self.examples_root.joinpath(*module_parts, self.snake_case(class_name))
        if not folder.is_dir():
            return []
        return sorted(folder.glob("*.py"))

    @staticmethod
    def snake_case(class_name: str) -> str:
        """Turns a class name into the snake case name of its examples folder.

        Args:
            class_name: The str class name, such as `ExchangeTradedFundConstituents` or `HTTPError`.

        Returns:
            The str snake case name, such as `exchange_traded_fund_constituents` or `http_error`.

        Raises:
            Nothing.
        """
        with_breaks = re.sub(
            r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", class_name
        )
        return with_breaks.lower()

    @staticmethod
    def _program_title(program: pathlib.Path) -> str:
        """Reads the title of an example program from the first line of its module docstring.

        Args:
            program: The pathlib.Path of the program.

        Returns:
            The str title without its closing full stop, or the file name when the program has no docstring.

        Raises:
            SyntaxError: The program's source cannot be parsed.
        """
        docstring = ast.get_docstring(ast.parse(program.read_text()))
        if not docstring:
            return program.stem
        return docstring.splitlines()[0].rstrip(".")

    def _write_navigation(self) -> None:
        """Writes the reference section's navigation to `reference/SUMMARY.md`, with the class hierarchy first.

        Returns:
            None.

        Raises:
            Nothing.
        """
        with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as summary:
            summary.write(f"* [Class hierarchy]({HIERARCHY_PAGE_NAME})\n")
            summary.writelines(self.navigation.build_literate_nav())


ReferencePageBuilder().build()
