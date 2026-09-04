# data/create_tables.py

Applies every `.sql` file under `data/sql/ddl` in filename order, inside one transaction.

The numeric filename prefixes exist purely to order the run: `000` creates the schema, and the rest create the tables that live in it. Every statement is written to be safe to run again, so this script is both the way to create the tables initially and the way to pick up a later change to one of them.

## Why the SQL is not in the Python

Keeping the DDL in `.sql` files means the table definitions can be read, diffed and applied without going through Python at all, and a change to a broker's columns shows up in review as a change to that broker's own file. The Python here is only the runner, which is the one place mixing the two is unavoidable.

## Adding a column when a broker changes its file

`BrokerInstruments.ingest` refuses to write a frame carrying a column the table does not have, rather than dropping it. When that happens, add the column to that broker's DDL file with an `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statement and re-run this script.
