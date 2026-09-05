"""
The raw frame archive, which is the streaming subsystem's system of record.

Every websocket frame is appended here exactly as it arrived, before it is decoded and before anything else sees it. That ordering is the point. The database holds an interpretation of the bytes and the Redis cache holds a summary of them, but this holds the bytes, so a parser that turns out to be wrong, a batch the database refused, or a day the database was down are all recoverable by reading these files again.

Files are compressed with zstd from the standard library. A file is flushed at a block boundary every few seconds and sealed at a frame boundary when it rotates, which means a file whose process was killed is still readable up to its last flush rather than being lost entirely.

The format carries a broker code, so a reader knows which broker's decoder to apply, and the directory layout puts the broker first, so a second broker's archive sits beside the first with nothing else changing.
"""

import json
import os
import struct
import time
from compression import zstd
from pathlib import Path

ARCHIVE_MAGIC = b"BBSF"
ARCHIVE_FORMAT_VERSION = 1

FILE_HEADER_STRUCT = struct.Struct(">4sHHHHQ")
RECORD_HEADER_STRUCT = struct.Struct(">QI")

MANIFEST_FILE_NAME = "manifest.jsonl"

BROKER_CODES = {
    "zerodha": 1,
    "dhan": 2,
}


class ArchiveFormatError(Exception):
    """
    Raised when an archive file is not in the format this module writes.
    """


def broker_code(broker_name):
    """
    Give the numeric code stored in an archive file header for a broker.

    Args:
        broker_name (str): The broker name, for example "zerodha".

    Returns:
        int: The broker's code.

    Raises:
        KeyError: If the broker has no code, which means a new broker was added without registering one here.
    """
    return BROKER_CODES[broker_name]


def broker_name_for_code(code):
    """
    Give the broker name for a code read out of an archive file header.

    Args:
        code (int): The broker code from the file header.

    Returns:
        str: The broker name.

    Raises:
        ArchiveFormatError: If the code is not one this module knows about.
    """
    for name in BROKER_CODES:
        if BROKER_CODES[name] == code:
            return name
    raise ArchiveFormatError(f"Archive file carries unknown broker code {code}.")


def shard_directory(archive_directory, broker_name, trading_date, shard_number):
    """
    Give the directory one shard's archive files for one trading day live in.

    Args:
        archive_directory (str): The root of the archive, from stream_configuration.
        broker_name (str): The broker name, for example "zerodha".
        trading_date (datetime.date): The trading day the files belong to.
        shard_number (int): The shard that wrote them.

    Returns:
        pathlib.Path: The directory, which may not exist yet.
    """
    return Path(archive_directory) / broker_name / trading_date.strftime("%Y-%m-%d") / f"shard_{shard_number:02d}"


class ArchiveWriter:
    """
    Appends raw websocket frames to compressed files, rotating and sealing them as it goes.

    One instance belongs to one shard and is written by one thread. It is not safe to share between threads, which is deliberate: the shard hands frames to a single archive thread precisely so that compression never happens on the socket read path.

    Attributes:
        broker_name (str): The broker whose frames are being written.
        shard_number (int): The shard that owns this writer.
        directory (pathlib.Path): Where this shard's files for the day are written.
        frame_count (int): Frames written to the current file.
        packet_count (int): Packets those frames claimed to carry.
        uncompressed_bytes (int): Bytes of frame payload written to the current file, excluding record headers.
        compressed_bytes (int): Bytes actually written to the current file.
    """

    def __init__(self, archive_directory, broker_name, trading_date, shard_number, compression_level, rotation_seconds, rotation_bytes, sync_seconds, frame_packet_counter=None):
        """
        Prepare a writer and open its first file.

        Args:
            archive_directory (str): The root of the archive, from stream_configuration.
            broker_name (str): The broker whose frames will be written, for example "zerodha".
            trading_date (datetime.date): The trading day these files belong to.
            shard_number (int): The shard that owns this writer.
            compression_level (int): The zstd level to compress with.
            rotation_seconds (int): Seal the current file once it is this old.
            rotation_bytes (int): Seal the current file once it has this many compressed bytes.
            sync_seconds (float): Flush and fsync at least this often.
            frame_packet_counter (callable | None): A function from frame bytes to the number of packets the frame carries, supplied by the broker's own parser, or None to count no packets at all.

        Returns:
            None.

        Raises:
            OSError: If the directory cannot be created or the first file cannot be opened.
            KeyError: If the broker has no registered archive code.
        """
        self.broker_name = broker_name
        self.shard_number = shard_number
        self.trading_date = trading_date
        self.compression_level = compression_level
        self.rotation_seconds = rotation_seconds
        self.rotation_bytes = rotation_bytes
        self.sync_seconds = sync_seconds
        self.frame_packet_counter = frame_packet_counter

        self.directory = shard_directory(archive_directory, broker_name, trading_date, shard_number)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.directory / MANIFEST_FILE_NAME

        self.broker_code = broker_code(broker_name)
        self.file_sequence = self._next_file_sequence()

        self.output_file = None
        self.compressor = None
        self.path = None
        self.frame_count = 0
        self.packet_count = 0
        self.uncompressed_bytes = 0
        self.compressed_bytes = 0
        self.first_arrival_nanoseconds = None
        self.last_arrival_nanoseconds = None
        self.opened_at = 0.0
        self.last_sync_at = 0.0

        self._open_file()

    def _next_file_sequence(self):
        """
        Work out the sequence number the next file should take.

        A shard that is restarted part way through a day must not overwrite the files it wrote before, so the sequence continues from whatever is already on disk rather than starting again at one.

        Returns:
            int: The sequence number to give the next file.
        """
        highest = 0
        for path in self.directory.glob("*.frames.zst"):
            parts = path.name.split(".")[0].split("_")
            if len(parts) == 2 and parts[1].isdigit():
                highest = max(highest, int(parts[1]))
        return highest + 1

    def _open_file(self):
        """
        Open a new archive file and write its header.

        Returns:
            None.

        Raises:
            OSError: If the file cannot be created.
        """
        name = f"{time.strftime('%H%M%S')}_{self.file_sequence:06d}.frames.zst"
        self.path = self.directory / name
        self.output_file = open(self.path, "wb")
        self.compressor = zstd.ZstdCompressor(level=self.compression_level)

        header = FILE_HEADER_STRUCT.pack(
            ARCHIVE_MAGIC,
            ARCHIVE_FORMAT_VERSION,
            self.broker_code,
            self.shard_number,
            0,
            time.time_ns(),
        )
        self._write(header)

        self.frame_count = 0
        self.packet_count = 0
        self.uncompressed_bytes = 0
        self.first_arrival_nanoseconds = None
        self.last_arrival_nanoseconds = None
        self.opened_at = time.monotonic()
        self.last_sync_at = self.opened_at

    def _write(self, data):
        """
        Compress and write one piece of data, counting the compressed bytes it produced.

        Args:
            data (bytes): The bytes to compress and write.

        Returns:
            None.

        Raises:
            OSError: If the write fails.
        """
        chunk = self.compressor.compress(data)
        if chunk:
            self.output_file.write(chunk)
            self.compressed_bytes = self.compressed_bytes + len(chunk)

    def append(self, arrival_time_nanoseconds, frame):
        """
        Append one websocket frame to the archive.

        The frame is stored exactly as it arrived, so what comes back out of the archive is what came off the socket rather than anything this project decided about it. Counting the packets inside the frame is the broker parser's job, supplied as frame_packet_counter, because the archive does not know any broker's wire format.

        Args:
            arrival_time_nanoseconds (int): The value of time.time_ns() when the frame was read off the socket.
            frame (bytes): The frame as received.

        Returns:
            None.

        Raises:
            OSError: If the write, flush or rotation fails.
        """
        self._write(RECORD_HEADER_STRUCT.pack(arrival_time_nanoseconds, len(frame)))
        self._write(frame)

        self.frame_count = self.frame_count + 1
        self.uncompressed_bytes = self.uncompressed_bytes + len(frame)
        if self.frame_packet_counter is not None:
            self.packet_count = self.packet_count + self.frame_packet_counter(frame)
        if self.first_arrival_nanoseconds is None:
            self.first_arrival_nanoseconds = arrival_time_nanoseconds
        self.last_arrival_nanoseconds = arrival_time_nanoseconds

        now = time.monotonic()
        if now - self.last_sync_at >= self.sync_seconds:
            self.sync()
            self.last_sync_at = now
        if now - self.opened_at >= self.rotation_seconds or self.compressed_bytes >= self.rotation_bytes:
            self.rotate()

    def sync(self):
        """
        Close the current zstd block and push everything written so far to disk.

        This is what bounds how much a power loss can cost. Syncing on every frame would mean tens of thousands of fsync calls a second, which no disk sustains, so the archive accepts losing at most one sync interval and relies on the database holding the same ticks.

        Returns:
            None.

        Raises:
            OSError: If the flush or fsync fails.
        """
        chunk = self.compressor.flush(zstd.ZstdCompressor.FLUSH_BLOCK)
        if chunk:
            self.output_file.write(chunk)
            self.compressed_bytes = self.compressed_bytes + len(chunk)
        self.output_file.flush()
        os.fsync(self.output_file.fileno())

    def rotate(self):
        """
        Seal the current file and open the next one.

        Returns:
            None.

        Raises:
            OSError: If sealing or opening fails.
        """
        self._seal()
        self.file_sequence = self.file_sequence + 1
        self._open_file()

    def _seal(self):
        """
        Finish the current file at a zstd frame boundary and record it in the manifest.

        Returns:
            None.

        Raises:
            OSError: If the flush, fsync, close or manifest write fails.
        """
        chunk = self.compressor.flush(zstd.ZstdCompressor.FLUSH_FRAME)
        if chunk:
            self.output_file.write(chunk)
            self.compressed_bytes = self.compressed_bytes + len(chunk)
        self.output_file.flush()
        os.fsync(self.output_file.fileno())
        self.output_file.close()

        entry = {
            "file_name": self.path.name,
            "broker": self.broker_name,
            "shard_number": self.shard_number,
            "frame_count": self.frame_count,
            "packet_count": self.packet_count,
            "uncompressed_bytes": self.uncompressed_bytes,
            "compressed_bytes": self.compressed_bytes,
            "first_arrival_nanoseconds": self.first_arrival_nanoseconds,
            "last_arrival_nanoseconds": self.last_arrival_nanoseconds,
            "sealed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(self.manifest_path, "a") as manifest:
            manifest.write(json.dumps(entry) + "\n")
        self.compressed_bytes = 0

    def close(self):
        """
        Seal the current file and stop writing.

        Returns:
            None.

        Raises:
            OSError: If sealing fails.
        """
        if self.output_file is None:
            return
        self._seal()
        self.output_file = None
        self.compressor = None


def read_archive_file(path):
    """
    Yield every frame in one archive file, in the order it arrived.

    A file whose writer was killed before it could be sealed is read up to its last completed flush and then stops, rather than raising, because that is exactly the case this function exists to rescue.

    Args:
        path (pathlib.Path | str): Path to a .frames.zst file written by ArchiveWriter.

    Yields:
        tuple: An (arrival_time_nanoseconds, frame_bytes) pair, where the frame is exactly the bytes that came off the socket.

    Raises:
        ArchiveFormatError: If the file does not begin with a recognisable header.
        OSError: If the file cannot be read.
    """
    with open(path, "rb") as compressed_file:
        decompressor = zstd.ZstdDecompressor()
        buffer = b""
        header_read = False
        offset = 0

        while True:
            chunk = compressed_file.read(1024 * 1024)
            if chunk:
                buffer = buffer + decompressor.decompress(chunk)
            elif not chunk:
                pass

            if not header_read and len(buffer) >= FILE_HEADER_STRUCT.size:
                magic, version, code, shard, reserved, started = FILE_HEADER_STRUCT.unpack_from(buffer, 0)
                if magic != ARCHIVE_MAGIC:
                    raise ArchiveFormatError(f"{path} does not start with {ARCHIVE_MAGIC!r}.")
                if version != ARCHIVE_FORMAT_VERSION:
                    raise ArchiveFormatError(f"{path} is format version {version}, this reader understands {ARCHIVE_FORMAT_VERSION}.")
                offset = FILE_HEADER_STRUCT.size
                header_read = True

            if header_read:
                while True:
                    if offset + RECORD_HEADER_STRUCT.size > len(buffer):
                        break
                    arrival, frame_length = RECORD_HEADER_STRUCT.unpack_from(buffer, offset)
                    if offset + RECORD_HEADER_STRUCT.size + frame_length > len(buffer):
                        break
                    frame_start = offset + RECORD_HEADER_STRUCT.size
                    yield (arrival, buffer[frame_start:frame_start + frame_length])
                    offset = frame_start + frame_length
                buffer = buffer[offset:]
                offset = 0

            if not chunk:
                break


def read_manifest(directory):
    """
    Read the manifest describing every sealed file in one shard's directory.

    The manifest is what makes a backfill cheap: it carries the first and last arrival time of every file, so replaying a half hour window reads only the files whose range overlaps it rather than every file of the day.

    Args:
        directory (pathlib.Path | str): A shard directory containing a manifest.

    Returns:
        list[dict]: One entry per sealed file, in the order they were sealed. An empty list when no manifest exists yet.

    Raises:
        OSError: If the manifest exists but cannot be read.
    """
    path = Path(directory) / MANIFEST_FILE_NAME
    if not path.exists():
        return []
    entries = []
    with open(path) as manifest:
        for line in manifest:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries
