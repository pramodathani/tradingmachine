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

## The REST cross-check, and what it found

`--against-rest` picks instruments spanning every exchange Zerodha lists, opens one websocket connection, decodes what arrives, and compares it against Zerodha's own `/quote` endpoint for the same instruments. The broker is the oracle, so this is the check that catches a field the parser and the synthetic checks are wrong about in the same direction.

It can be run outside market hours, which was not obvious in advance. Zerodha sends a snapshot of every subscribed instrument immediately after accepting a subscription, so a connection opened on a Saturday still yields a full set of last-traded prices, day ranges and five level depth carrying Friday's closing state. That makes this a check that can be run at any time rather than only during a session.

It earned itself immediately. On its first run it found that segment 12, NSE Commodity, divides by ten thousand and not by the hundred the parser had assumed, an error of two orders of magnitude affecting roughly a quarter of the instruments Zerodha lists. No synthetic check could have found that, because the synthetic checks assert what this project believes the format to be, and the belief itself was wrong.

After the correction, 837 values across 33 instruments and all nine exchanges agreed exactly, covering segments 1, 2, 3, 4, 5, 7, 9 and 12, which is every segment that appears in the instrument universe.

## What each check can and cannot prove

The synthetic checks prove the parser is self-consistent with the format as this project understands it. They cannot prove that understanding is right, because every byte they read was written by the mirror image of the code they test.

The REST check proves the understanding matches the broker, for the instruments and fields it compares. Its limits are worth naming too: it compares against a snapshot rather than a stream, so it exercises decoding but not the behaviour of a connection under load, and it can only compare fields the quote endpoint also reports, which excludes the two exchange timestamps and the per level order counts.

Between them they leave one gap, which is decoding under a live tick stream at rate. That is what running a shard through a real session covers.
