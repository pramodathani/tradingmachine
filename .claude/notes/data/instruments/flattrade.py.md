# data/instruments/flattrade.py

Flattrade publishes eight public CSV files on S3, one per exchange and segment, all sharing the same nine-column header. They are fetched and stacked into one frame.

The BSE equity file ends with a footer of blank rows, whose key columns parse as null. Those are filled with empty strings before the base class de-duplicates, so the footer rows collapse into one instead of causing a null key.

Flattrade and Shoonya both sit on the Noren platform and their files look similar. They are deliberately kept as two separate modules rather than sharing one implementation, so each is readable on its own.

Verified on 2026-09-04: 148,982 rows after dropping 3,797 duplicates, by far the largest duplicate count of the ten, which is expected given the same instrument appears in several of the eight files.
