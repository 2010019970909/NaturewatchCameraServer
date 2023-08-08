# -*- coding: utf-8 -*-
"""A Zipfile generator to write zip files in a stream."""
import logging
from io import RawIOBase
from zipfile import ZipFile, ZipInfo


class ZipfileGenerator:  # pylint: disable=locally-disabled, too-few-public-methods, line-too-long # noqa: E501
    """A Zipfile generator to write zip files in a stream."""

    class UnseekableStream(RawIOBase):
        """A stream that can't be seeked."""

        def __init__(self):
            """Constructor."""
            super().__init__()
            self._buffer = b""

        def writable(self):
            """Return True if the stream supports writing.
            :return: True"""
            return True

        def write(self, b):
            """Write the given bytes to the stream.
            :param b: bytes to write
            :return: number of bytes written
            """
            if (
                self.closed
            ):  # pylint: disable=locally-disabled, using-constant-test, line-too-long # noqa: E501
                raise ValueError("Stream was closed!")
            self._buffer += b
            return len(b)

        def get(self):
            """Get the current buffer and reset it.
            :return: the current buffer
            """
            chunk = self._buffer
            self._buffer = b""
            return chunk

    # Constructor
    def __init__(
        self,
        paths: list,  # { 'filename':'', 'arcname':'' }
        chunk_size=0x8000,
        logger=logging.getLogger(__name__),
    ):
        """Constructor.
        :param paths: The list of paths to zip.
        :param chunk_size: The size of the chunks to yield.
        :param logger: The logger to use.
        """
        if paths is None:
            paths = []
        self.paths = paths
        self.chunk_size = chunk_size
        self.logger = logger

    # Generator
    def get(self):
        """Generate the zip file.
        :return: The zip file in a stream.
        """
        output = ZipfileGenerator.UnseekableStream()

        with ZipFile(output, mode="w") as zipfile:
            for path in self.paths:
                try:
                    if len(path["arcname"]) == 0:
                        path["arcname"] = path["filename"]

                    z_info = ZipInfo.from_file(
                        path["filename"], path["arcname"]
                    )

                    # it's not worth the resources,
                    # achieves max 0.1% on JPEGs...
                    # z_info.compress_type = ZIP_DEFLATED

                    # should we try to fix the disk timestamps?
                    # or should it be solved by setting the
                    # system time with the browser time?
                    # VS: Seems to be solved using the former technique.

                    with (
                        open(path["filename"], "rb") as entry,
                        zipfile.open(z_info, mode="w") as dest,
                    ):
                        chunk = entry.read(self.chunk_size)
                        while chunk:
                            dest.write(chunk)
                            # yield chunk of the zip file stream in bytes.
                            yield output.get()
                            chunk = entry.read(self.chunk_size)

                except FileNotFoundError:
                    self.logger.error("File not found: %s", path["filename"])

        # ZipFile was closed: get the final bytes
        yield output.get()
