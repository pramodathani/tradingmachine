"""
Applies the instrument schema and table definitions to TimescaleDB.

Every file under data/sql/ddl is executed in filename order, so the schema is created before the tables that live in it. Each statement is written to be safe to run again, which makes this script the way to both create the tables and pick up a later change to them.
"""

from pathlib import Path

from sqlalchemy import create_engine, text

from utilities.configuration import postgres_configuration

DDL_DIRECTORY = Path(__file__).parent / "sql" / "ddl"


def run():
    """
    Execute every DDL file in filename order.

    Returns:
        int: The number of DDL files applied.

    Raises:
        FileNotFoundError: If the DDL directory does not exist.
    """
    if not DDL_DIRECTORY.is_dir():
        raise FileNotFoundError(f"No DDL directory at {DDL_DIRECTORY}")

    engine = create_engine(postgres_configuration["connection_string"])
    paths = sorted(DDL_DIRECTORY.glob("*.sql"))
    with engine.begin() as connection:
        for path in paths:
            connection.execute(text(path.read_text()))
            print(f"applied {path.name}")
    print(f"Applied {len(paths)} DDL file(s).")
    return len(paths)


if __name__ == "__main__":
    run()
