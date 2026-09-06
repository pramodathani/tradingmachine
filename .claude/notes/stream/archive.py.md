# stream/archive.py

Writes every websocket frame to disk exactly as it arrived, compressed with zstd, and reads them back. This is the streaming subsystem's system of record, and it is shared by every broker rather than written once per broker.

## Why the archive is the system of record and the database is not

The obvious design has the database hold the data and the archive, if it exists at all, act as a backup. This is the other way round on purpose.

The database holds an *interpretation* of the bytes. If the parser reads a field at the wrong offset, every row written from it is wrong and no amount of database durability helps. The Redis cache holds a *summary*, coalesced to ten times a second. Only this holds what actually arrived.

Making the archive authoritative is what allows several other decisions to be simple. The database writer can drop rows when its queue fills during an outage, because they can be replayed. The parser can be changed and the affected days re-decoded. A whole day of database trouble costs a backfill rather than a day of data. None of that is available if the database is the only copy.

It is also the cheapest possible write path, which matters because it sits closest to the socket: appending a length-prefixed byte string to a compressor costs almost nothing and, crucially, requires no understanding of the bytes at all.

## Frames are stored verbatim, including the parts we do not use

A record is a timestamp, a length, and the frame. The frame includes its own packet count prefix and includes heartbeats. Nothing is normalised, stripped or reordered.

This is what makes a parser bug recoverable. If the archive stored decoded ticks, a decoding mistake would be baked into it and the original bytes would be gone. Storing the wire means the archive remains true regardless of what this project currently believes about the format.

## The fsync trade-off, and what it actually costs

The compressor is flushed at a block boundary and fsynced every few seconds, and at a frame boundary when a file rotates. It is never fsynced per frame, because that would be tens of thousands of fsync calls a second at the expected rates and no disk sustains it.

The exposure is bounded and was measured rather than assumed. A writer was given seven hundred frames, synced after the first five hundred, and then killed with `os._exit`, which is what `kill -9` looks like from the file's point of view. Reading the resulting unsealed file returned exactly five hundred frames with no exception raised. So a hard power loss or kernel panic costs at most one sync interval per shard, and an ordinary process crash costs nothing at all, since the page cache survives it.

That the reader tolerates an unsealed file is the point of using an explicit `ZstdCompressor` rather than `ZstdFile`. `FLUSH_BLOCK` closes a block so everything before it is independently decodable, and the reader uses a streaming `ZstdDecompressor`, which stops cleanly at the end of the readable data instead of demanding a terminated frame.

## Rotation, and why the manifest exists

Files are sealed after fifteen minutes or five hundred and twelve compressed megabytes. Sealing appends a line to `manifest.jsonl` recording the file's frame count, packet count, byte counts, and the first and last arrival timestamps it contains.

The manifest is what makes a backfill cheap. Replaying a half hour window reads the manifest, selects the two or three files whose arrival range overlaps the window, and never opens the other ninety files of the day. Without it, any replay would be a full day scan.

The frame and packet counts also serve as a reconciliation check: they can be compared against what the shard logged and against what reached the database, and a mismatch is a real signal rather than a guess.

## Restarting a shard does not overwrite its earlier files

A shard that is restarted part way through a trading day opens a new file whose sequence number continues from the highest already on disk, rather than starting again at one. Since a shard restarting mid-session is expected rather than exceptional, starting the sequence over would quietly destroy the morning's data.

## The broker code in the header

The file header carries a numeric broker code as well as the shard number. A replay tool reading a file has to know which broker's decoder to apply to the frames inside it, and while the directory path also says so, the path can be renamed or the file moved. Putting it in the bytes makes the file self-describing.

Adding a broker means adding an entry to `BROKER_CODES`. Codes are never reused or renumbered, because old archive files keep the code they were written with. The codes are handed out in the order the streaming subsystem learned to carry each broker: Zerodha is 1, Dhan is 2, Flattrade is 3 and Shoonya is 4.

## Packet counting is the broker parser's job

The manifest records how many packets the sealed frames claimed to carry, which serves as a reconciliation check against what the shard logged and what reached the database. The writer itself has no idea how to count packets, though: Zerodha frames begin with a two byte big endian count, while Dhan frames begin with an eight byte little endian header whose second field is a message length that means something different. Reading a Dhan frame with Zerodha's unpack produces garbage counts, and garbage in a reconciliation check is worse than no check, because it looks like a real signal.

So the writer takes a `frame_packet_counter` callable from its constructor, supplied by the broker's own parser, and calls it on every frame. Each broker's `packets` module owns the counting decision, exactly as it owns the decoding decision, and the archive stays ignorant of every wire format. A writer constructed without a counter records zero packets, which no shard should do in production; the parameter is not optional in spirit, only in signature, because nothing constructs an `ArchiveWriter` yet and the first shard will pass its broker's counter.

## Threading

An `ArchiveWriter` belongs to one shard and is written by one thread. It is not thread safe and is not meant to be: the shard hands frames to a dedicated archive thread through a queue precisely so that compression and disk writes never happen on the socket read path. Compression releases the interpreter lock, so that thread genuinely runs alongside decoding rather than competing with it.
