#!/usr/bin/python
# coding: utf-8

"""
File parser for Chemstation files (*.ch)
Basically a port of the matlab script at:
https://github.com/chemplexity/chromatography/blob/master/Development/File%20Conversion/ImportAgilentFID.m

This file is a standalone file to parse the binary files created by Chemstation

I use it for file with version 130, genereted by an Agilent LC.
"""

import struct
from struct import unpack
import numpy as np

# Constants used for binary file parsing
ENDIAN = ">"
STRING = ENDIAN + "{}s"
UINT8 = ENDIAN + "B"
UINT16 = ENDIAN + "H"
INT16 = ENDIAN + "h"
INT32 = ENDIAN + "i"
UINT32 = ENDIAN + "I"


def fread(fid, nelements, dtype):

    """Equivalent to Matlab fread function"""

    if dtype is np.str:
        dt = np.uint8  # WARNING: assuming 8-bit ASCII for np.str!
    else:
        dt = dtype

    data_array = np.fromfile(fid, dt, nelements)
    data_array.shape = (nelements, 1)

    return data_array


def parse_utf16_string(file_, encoding="UTF16"):

    """Parse a pascal type UTF16 encoded string from a binary file object"""

    # First read the expected number of CHARACTERS
    string_length = unpack(UINT8, file_.read(1))[0]
    # Then read and decode
    parsed = unpack(STRING.format(2 * string_length), file_.read(2 * string_length))
    return parsed[0].decode(encoding)


class cached_property(object):

    """A property that is only computed once per instance and then replaces
    itself with an ordinary attribute. Deleting the attribute resets the
    property.

    https://github.com/bottlepy/bottle/commit/fa7733e075da0d790d809aa3d2f53071897e6f76
    """

    def __init__(self, func):
        self.__doc__ = getattr(func, "__doc__")
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class CHFile(object):

    """Class that implementats the Agilent .ch file format version
    130. Warning: Not all aspects of the file header is understood,
    so there may and probably is information that is not parsed. See
    _parse_header_status for an overview of which parts of the header
    is understood.

    Attributes:
        values (numpy.array): The intensity values (y-value) or the
        spectrum. The unit for the values is given in `metadata['units']`

        metadata (dict): The extracted metadata

        filepath (str): The filepath this object was loaded from
    """

    # Fields is a table of name, offset and type. Types 'x-time' and 'utf16'
    # are specially handled, the rest are format arguments for struct unpack
    fields = (
        ("sequence_line_or_injection", 252, UINT16),
        ("injection_or_sequence_line", 256, UINT16),
        ("data_offset", 264, UINT32),
        ("start_time", 282, "x-time"),
        ("end_time", 286, "x-time"),
        ("version_string", 326, "utf16"),
        ("description", 347, "utf16"),
        ("sample", 858, "utf16"),
        ("operator", 1880, "utf16"),
        ("date", 2391, "utf16"),
        ("inlet", 2492, "utf16"),
        ("instrument", 2533, "utf16"),
        ("method", 2574, "utf16"),
        ("software version", 3601, "utf16"),
        ("software name", 3089, "utf16"),
        ("software revision", 3802, "utf16"),
        ("zero", 4110, INT32),
        ("units", 4172, "utf16"),
        ("detector", 4213, "utf16"),
        ("yscaling", 4732, ENDIAN + "d"),
    )

    # The start position of the data
    # Get it from metadata['data_offset'] * 512
    data_start = 6144

    # The versions of the file format supported by this implementation
    supported_versions = {130}

    def __init__(self, filepath):

        self.filepath = filepath
        self.metadata = {}
        with open(self.filepath, "rb") as file_:
            self._parse_header(file_)
            self.values = self._parse_data(file_)

    def _parse_header(self, file_):

        """Parse the header"""

        # Parse and check version
        length = unpack(UINT8, file_.read(1))[0]
        parsed = unpack(STRING.format(length), file_.read(length))
        version = int(parsed[0])
        if version not in self.supported_versions:
            raise ValueError("Unsupported file version {}".format(version))
        self.metadata["magic_number_version"] = version

        # Parse all metadata fields
        for name, offset, type_ in self.fields:
            file_.seek(offset)
            if type_ == "utf16":
                self.metadata[name] = parse_utf16_string(file_)
            elif type_ == "x-time":
                self.metadata[name] = unpack(UINT32, file_.read(4))[0] / 60000
            else:
                self.metadata[name] = unpack(type_, file_.read(struct.calcsize(type_)))[
                    0
                ]

    def _parse_header_status(self):

        """Print known and unknown parts of the header"""

        file_ = open(self.filepath, "rb")

        print("Header parsing status")
        # Map positions to fields for all the known fields
        knowns = {item[1]: item for item in self.fields}
        # A couple of places has a \x01 byte before a string, these we simply
        # skip
        skips = {325, 3600}
        # Jump to after the magic number version
        file_.seek(4)

        # Initialize variables for unknown bytes
        unknown_start = None
        unknown_bytes = b""
        # While we have not yet reached the data
        while file_.tell() < self.data_start:
            current_position = file_.tell()
            # Just continue on skip bytes
            if current_position in skips:
                file_.read(1)
                continue

            # If we know about a data field that starts at this point
            if current_position in knowns:
                # If we have collected unknown bytes, print them out and reset
                if unknown_bytes != b"":
                    print(
                        "Unknown at", unknown_start, repr(unknown_bytes.rstrip(b"\x00"))
                    )
                    unknown_bytes = b""
                    unknown_start = None

                # Print out the position, type, name and value of the known
                # value
                print("Known field at {: >4},".format(current_position), end=" ")
                name, _, type_ = knowns[current_position]
                if type_ == "x-time":
                    print(
                        'x-time, "{: <19}'.format(name + '"'),
                        unpack(ENDIAN + "f", file_.read(4))[0] / 60000,
                    )
                elif type_ == "utf16":
                    print(
                        ' utf16, "{: <19}'.format(name + '"'), parse_utf16_string(file_)
                    )
                else:
                    size = struct.calcsize(type_)
                    print(
                        '{: >6}, "{: <19}'.format(type_, name + '"'),
                        unpack(type_, file_.read(size))[0],
                    )

            # We do not know about a data field at this position If we have
            # already collected 4 zero bytes, assume that we are done with
            # this unknown field, print and reset
            else:
                if unknown_bytes[-4:] == b"\x00\x00\x00\x00":
                    print(
                        "Unknown at", unknown_start, repr(unknown_bytes.rstrip(b"\x00"))
                    )
                    unknown_bytes = b""
                    unknown_start = None

                # Read one byte and save it
                one_byte = file_.read(1)
                if unknown_bytes == b"":
                    # Only start a new collection of unknown bytes, if this
                    # byte is not a zero byte
                    if one_byte != b"\x00":
                        unknown_bytes = one_byte
                        unknown_start = file_.tell() - 1
                else:
                    unknown_bytes += one_byte

        file_.close()

    def _parse_data(self, file_):

        """Parse the data. Decompress the delta-encoded data, and scale them
        with y-scaling"""

        scaling = self.metadata["yscaling"]

        # Go to the end of the file
        file_.seek(0, 2)
        stop = file_.tell()

        # Go to the start point of the data
        file_.seek(self.data_start)

        signal = []

        buff = [0, 0, 0, 0]

        while file_.tell() < stop:

            buff[0] = fread(file_, 1, INT16)[0][0]
            buff[1] = buff[3]

            if buff[0] << 12 == 0:
                break

            for i in range(buff[0] & 4095):

                buff[2] = fread(file_, 1, INT16)[0][0]

                if buff[2] != -32768:
                    buff[1] = buff[1] + buff[2]
                else:
                    buff[1] = fread(file_, 1, INT32)[0][0]

                signal.append(buff[1])

            buff[3] = buff[1]

        signal = np.array(signal)
        signal = signal * scaling

        return signal

    @cached_property
    def times(self):

        """The time values (x-value) for the data set in minutes"""

        return np.linspace(
            self.metadata["start_time"], self.metadata["end_time"], len(self.values)
        )


if __name__ == "__main__":
    CHFile("lcdiag.reg")
