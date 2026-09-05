# stream/zerodha/verify_stream.py

Checks that `stream/zerodha/packets.py` decodes correctly. Run with `python3 -m stream.zerodha.verify_stream --synthetic`, which needs no network and no market hours, and exits non-zero if any check fails.

It follows the precedent set by `data/mapping/verify_mapping.py`: a standalone command that prints a readable report, rather than a test framework, which the project does not otherwise use.

## Why a binary parser needs this more than most code

A parser that reads a field at the wrong offset or the wrong width does not crash. It produces numbers that are still integers in a plausible range, which flow into the database and onto the bus and look exactly like prices and quantities. Every model downstream would then trade on them with no indication that anything was wrong. The failure is silent, and silence is what these checks exist to break.

Each check therefore targets a specific way the parser could be wrong, rather than exercising a happy path:

- The index ordering check uses five deliberately different prices, so decoding an index with the tradeable reader swaps open with high and low with close and the check fails.
- The depth check gives every level a different order count, including 65535 at the last ask, so reading the two byte order count as four bytes shifts the later entries and shows up as wrong prices rather than only wrong order counts.
- The divisor check covers NSE currency, BSE currency, NSE Commodity, an index and a segment number that does not exist, so both the special cases and the fall-through are pinned down.
- The truncation check cuts a frame at every single byte position and also builds a frame whose header overstates the packet count, since a corrupted count is the other way the loop could be driven past the end of the buffer.

## These checks were themselves tested

Passing checks prove nothing on their own, so each of the five dangerous mistakes above was deliberately introduced into the parser and the checks re-run, confirming that the intended check failed each time. All five were caught.

That exercise is worth repeating whenever a check is added or changed, because it is the only thing that distinguishes a check that would catch a regression from one that merely runs.

It also produced a trap worth recording. When mutations are applied by rewriting the source file in place and the checks are run in a subprocess, Python's bytecode cache can serve a stale `.pyc`: its cache key is the source file's size together with its modification time in whole seconds, so two different mutations that happen to produce files of identical size within the same second will run the earlier one's compiled code. Two of the five mutations here produced files of exactly 15793 bytes and did precisely that, which made a working check appear broken. Set `PYTHONDONTWRITEBYTECODE=1` when running this kind of experiment.

## What is not covered here

These checks prove the parser is self-consistent with the format as understood. They cannot prove that understanding is right, because every byte they read was written by the same module's mirror image in this file.

The check that closes that gap needs the live market: fetching Zerodha's own REST quote for a set of instruments and comparing it against the decoded ticks for the same instruments, with the broker as the oracle. That is added when the connection exists, and it is the check that would catch a field this file and the parser are wrong about in the same direction.
