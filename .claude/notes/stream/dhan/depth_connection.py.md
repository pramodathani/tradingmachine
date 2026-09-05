# stream/dhan/depth_connection.py

Drives one Dhan full market depth websocket connection, for either the twenty level or the two hundred level book. It mirrors `stream/dhan/connection.py` in shape, including the identical health counter names, and imports every shared constant from that module, so the two sockets' keep-alive timings, backoff curve and refusal close codes cannot drift apart.

## One class for two levels, and where the line of that decision sits

The twenty level and two hundred level sockets differ in only three things: the host URL, the shape of the subscription message, and how many instruments a connection may carry. Everything else on the wire, from the twelve byte header to the disconnect reasons to the keep-alive cadence, is the same, so one class parameterised on `depth_level` carries both. The differences live in small explicit branches, `websocket_url` and `subscribe_message`, which is the honest form of the variation. A shared abstraction that hid them would hide the fact that the two hundred level subscription is flat, with the instrument named at the top of the message rather than in a list, and that flatness is the reason a two hundred level connection can never carry more than one instrument.

The validation is enforced in three places on purpose: `websocket_url` and `subscribe_message` reject an unknown depth level on their own, so the module's functions are safe to call directly, and the constructor rejects both an unknown level and a two hundred level subscription with the wrong instrument count, so a caller cannot build an object that would fail later. `subscribe_message` keeps its own copy of the exactly-one-instrument check so the message builder cannot be misused without the class.

## The shared five connection budget

Dhan's real connection limit is measured, not documented, and the depth sockets draw on the same pool the live feed does. A twenty level socket carrying fifty instruments is cheap in connections but the two hundred level socket spends one whole connection on one instrument, so it is built and verified here but is not expected to carry anything beyond a handful of watched symbols. The connection supervisor, when it exists, must count depth sockets and live feed sockets together against the measured limit, and the eviction warning from the live feed connection applies unchanged: reason 805 closes the oldest healthy socket rather than refusing the new one, so a tight retry loop on a depth socket churns its siblings.

## The disconnect test reads the segment byte, not the code byte

The depth header is length-first, `<hBBiI`, so the section's code sits at byte 2 rather than byte 0, and the disconnect test is `message[2] == 50`. This is the single easiest place to confuse the two Dhan feeds, since the live feed puts its code at byte 0, and it is why this module owns its own frame handler rather than sharing one with the live connection. A disconnect packet is counted and handed to the callback before the exception is raised, so the archive holds the reason the connection ended, exactly as the live feed connection does.

## verify_stream --depth is a live probe, not a proof

The `--depth` mode opens a real socket, holds it for the requested seconds, and reports frames, heartbeats, distinct security identifiers, bid and ask section counts, and reconnects. Its pass criteria are deliberately narrow: data frames seen, bid and ask sections arriving in roughly equal numbers, every subscribed instrument represented, and no reconnection during a short hold. Seeing nothing outside market hours is a note, not a failure, because silence is the expected answer when the exchange is closed. The row layout itself is pinned by the synthetic checks; this mode confirms the live wire matches them.