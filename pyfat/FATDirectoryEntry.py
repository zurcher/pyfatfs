#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import struct

from pyfat._exceptions import PyFATException, NotAnLFNEntryException

import errno


class FATDirectoryEntry(object):
    ATTR_READ_ONLY = 0x01
    ATTR_HIDDEN = 0x02
    ATTR_SYSTEM = 0x04
    ATTR_VOLUME_ID = 0x8
    ATTR_DIRECTORY = 0x10
    ATTR_ARCHIVE = 0x20
    ATTR_LONG_NAME = ATTR_READ_ONLY | ATTR_HIDDEN | ATTR_SYSTEM | ATTR_VOLUME_ID
    ATTR_LONG_NAME_MASK = ATTR_READ_ONLY | ATTR_HIDDEN | ATTR_SYSTEM | \
                          ATTR_VOLUME_ID | ATTR_DIRECTORY | ATTR_ARCHIVE

    FAT_DIRECTORY_LAYOUT = "<11sBHHHHHHHHL"
    FAT_DIRECTORY_HEADER_SIZE = struct.calcsize(FAT_DIRECTORY_LAYOUT)
    FAT_DIRECTORY_VARS = ["DIR_Name", "DIR_Attr", "DIR_NTRes",
                          "DIR_CrtTimeTenth", "DIR_CrtDateTenth",
                          "DIR_LstAccessDate", "DIR_FstClusHI",
                          "DIR_WrtTime", "DIR_WrtDate",
                          "DIR_FstClusLO", "DIR_FileSize"]

    def __init__(self, DIR_Name, DIR_Attr, DIR_NTRes, DIR_CrtTimeTenth,
                 DIR_CrtDateTenth, DIR_LstAccessDate, DIR_FstClusHI,
                 DIR_WrtTime, DIR_WrtDate, DIR_FstClusLO, DIR_FileSize,
                 encoding, lfn_entry=None):
        if len(DIR_Name) > 0:
            if DIR_Name[0] == 0x0 or DIR_Name[0] == 0xE5:
                # Empty directory entry
                raise NotADirectoryError("Given dir entry is invalid and has "
                                         "no valid name.")

            if DIR_Name[0] == 0x05:
                # Translate 0x05 to 0xE5
                DIR_Name = DIR_Name.replace(bytes(0x05), bytes(0xE5), 1)

        if isinstance(DIR_Name, str):
            # Encode it to given encoding
            DIR_Name = DIR_Name.encode(encoding)

        self.name = DIR_Name
        self.attr = int(DIR_Attr)
        self.ntres = int(DIR_NTRes)
        self.crttimetenth = int(DIR_CrtTimeTenth)
        self.crtdatetenth = int(DIR_CrtDateTenth)
        self.lstaccessdate = int(DIR_LstAccessDate)
        self.fstclushi = int(DIR_FstClusHI)
        self.wrttime = int(DIR_WrtTime)
        self.wrtdate = int(DIR_WrtDate)
        self.fstcluslo = int(DIR_FstClusLO)
        self.filesize = int(DIR_FileSize)

        self._parent = None

        self.lfn_entry = lfn_entry

        self.__dirs = set()
        self.__encoding = encoding

    def get_entry_size(self):
        """Return size of directory entry."""
        sz = self.FAT_DIRECTORY_HEADER_SIZE
        if isinstance(self.lfn_entry, FATLongDirectoryEntry):
            sz *= len(self.lfn_entry.lfn_entries)
        return sz

    def get_size(self):
        """Return filesize or directory entry size in bytes."""
        if self.is_directory():
            sz = self.FAT_DIRECTORY_HEADER_SIZE
            sz *= len(self.__dirs)+1
            return sz

        return self.filesize

    def get_cluster(self):
        """Return cluster address of directory entry."""
        return self.fstcluslo + (self.fstclushi << 16)

    def set_cluster(self, first_cluster):
        """Convert first_cluster to low and high word and set headers."""
        self.fstcluslo = (first_cluster >> (16 * 0) & 0xFFFF)
        self.fstclushi = (first_cluster >> (16 * 1) & 0xFFFF)

    def byte_repr(self):
        name = self.name
        if name[0] == 0xE5:
            name[0] = 0x05

        entry = struct.pack(self.FAT_DIRECTORY_LAYOUT, name, self.attr, self.ntres,
                            self.crttimetenth, self.crtdatetenth, self.lstaccessdate,
                            self.fstclushi, self.wrttime, self.wrtdate, self.fstcluslo,
                            self.filesize)

        if isinstance(self.lfn_entry, FATLongDirectoryEntry):
            entry += self.lfn_entry.byte_repr()

        return entry

    def add_parent(self, cls):
        if self._parent is not None:
            raise PyFATException("Trying to add multiple parents to current "
                                 "directory!", errno=errno.ETOOMANYREFS)

        if not isinstance(cls, FATDirectoryEntry):
            raise PyFATException("Trying to add a non-FAT directory entry "
                                 "as parent directory!", errno=errno.EBADE)

        self._parent = cls

    def _get_parent_dir(self, sd):
        name = self.__repr__()
        if self.__repr__() == "/":
            name = ""
        sd += [name]

        if self._parent is None:
            return sd

        return self._parent._get_parent_dir(sd)

    def get_parent_dir(self):
        """Iterate all parents up and join them by "/"."""
        parent_dirs = [self.__repr__()]

        if self._parent is None:
            return "/".join(list(reversed(parent_dirs)))

        return "/".join(list(reversed(self._parent._get_parent_dir(parent_dirs))))

    def is_special(self):
        return self.get_short_name() in [".", ".."]

    def is_read_only(self):
        return (self.ATTR_READ_ONLY & self.attr) > 0

    def is_hidden(self):
        return (self.ATTR_HIDDEN & self.attr) > 0

    def is_system(self):
        return (self.ATTR_SYSTEM & self.attr) > 0

    def is_volume_id(self):
        return (self.ATTR_VOLUME_ID & self.attr) > 0

    def is_directory(self):
        return (self.ATTR_DIRECTORY & self.attr) > 0

    def is_archive(self):
        return (self.ATTR_ARCHIVE & self.attr) > 0

    def get_entries(self):
        dirs = []
        files = []
        specials = []

        for d in self.__dirs:
            if d.is_special() or d.is_volume_id():
                # Volume IDs and dot/dotdot entries
                specials += [d]
            elif d.is_directory():
                # Directories
                dirs += [d]
            else:
                # Everything else must be a file
                files += [d]

        return dirs, files, specials

    def _search_entry(self, name):
        # Find given dir entry by walking current dir
        dirs, files, specials = self.get_entries()
        for entry in dirs+files:
            try:
                if entry.get_long_name() == name:
                    return entry
            except NotAnLFNEntryException:
                pass
            if entry.get_short_name() == name:
                return entry
        else:
            raise PyFATException(f'Cannot find entry {name}', errno=errno.ENOENT)

    def get_entry(self, path):
        entry = self
        for segment in filter(None, path.split("/")):
            entry = entry._search_entry(segment)
        return entry

    def walk(self):
        # Walk all directory entries recursively
        # root (current path, full), dirs (all dirs), files (all files)
        root = self.get_parent_dir()
        dirs, files, _ = self.get_entries()

        yield root, dirs, files
        for d in self.__dirs:
            if d.is_special():
                # Ignore dot and dotdot
                continue

            if not d.is_directory():
                continue

            yield from d.walk()

    def add_subdirectory(self, dir_entry=None):
        # Check if current dir entry is even a directory!
        if not self.is_directory():
            raise PyFATException("Cannot add subdirectory to "
                                 "a non-directory entry!",
                                 errno=errno.ENOENT)

        dir_entry.add_parent(self)
        self.__dirs.add(dir_entry)

    def __repr__(self):
        try:
            return self.get_long_name()
        except NotAnLFNEntryException:
            return self.get_short_name()

    def get_short_name(self):
        n = self.name.decode(self.__encoding)

        sep = "."
        if self.attr == self.ATTR_DIRECTORY:
            sep = ""

        name = n[0:8].strip()
        ext = n[8:11].strip()

        if ext == "":
            return name
        else:
            return sep.join([name, ext])

    def _remove_padding(self, entry: bytes):
        while entry.endswith(b'\xFF\xFF'):
            entry = entry[:-2]
        entry = entry.replace(b'\x00', b'')
        return entry

    def get_long_name(self):
        if self.lfn_entry is None:
            raise NotAnLFNEntryException("No LFN entry found for this "
                                         "dir entry.")

        name = ""
        for i in sorted(self.lfn_entry.lfn_entries.keys()):
            # TODO: Verify checksum!
            for h in ["LDIR_Name1", "LDIR_Name2", "LDIR_Name3"]:
                name += self._remove_padding(self.lfn_entry.lfn_entries[i][h]).decode(self.__encoding)

        return name.strip()


class FATLongDirectoryEntry(object):
    FAT_LONG_DIRECTORY_LAYOUT = "<B10sBBB12sH4s"
    FAT_LONG_DIRECTORY_VARS = ["LDIR_Ord", "LDIR_Name1", "LDIR_Attr",
                               "LDIR_Type", "LDIR_Chksum", "LDIR_Name2",
                               "LDIR_FstClusLO", "LDIR_Name3"]
    LAST_LONG_ENTRY = 0x40

    def __init__(self):
        self.lfn_entries = {}

    def byte_repr(self):
        entries_bytes = b""
        for e in self.lfn_entries.keys():
            e = self.lfn_entries[e]
            entries_bytes += struct.pack(self.FAT_LONG_DIRECTORY_LAYOUT,
                                         e["LDIR_Ord"], e["LDIR_Name1"],
                                         e["LDIR_Attr"], e["LDIR_Type"],
                                         e["LDIR_Chksum"], e["LDIR_Name2"],
                                         e["LDIR_FstClusLO"], e["LDIR_Name3"])
        return entries_bytes

    @staticmethod
    def is_lfn_entry(LDIR_Ord, LDIR_Attr):
        lfn_attr = FATDirectoryEntry.ATTR_LONG_NAME
        lfn_attr_mask = FATDirectoryEntry.ATTR_LONG_NAME_MASK
        is_attr_set = (LDIR_Attr & lfn_attr_mask) == lfn_attr

        return is_attr_set and LDIR_Ord != 0xE5

    def add_lfn_entry(self, LDIR_Ord, LDIR_Name1, LDIR_Attr, LDIR_Type,
                      LDIR_Chksum, LDIR_Name2, LDIR_FstClusLO, LDIR_Name3):
        # Check if attribute matches
        if not self.is_lfn_entry(LDIR_Ord, LDIR_Attr):
            raise NotAnLFNEntryException("Given LFN entry is not a long "
                                         "file name entry or attribute "
                                         "not set correctly!")

        # Check if FstClusLO is 0, as required by the spec
        if LDIR_FstClusLO != 0:
            raise PyFATException("Given LFN entry has an invalid first "
                                 "cluster ID, don't know what to do.",
                                 errno=errno.EFAULT)

        # Check if item with same index has already been added
        if LDIR_Ord in self.lfn_entries.keys():
            raise PyFATException("Given LFN entry part with index \'{}\'"
                                 "has already been added to LFN "
                                 "entry list.".format(LDIR_Ord))

        # TODO: Verify checksum

        mapped_entries = dict(zip(self.FAT_LONG_DIRECTORY_VARS,
                                  (LDIR_Ord, LDIR_Name1, LDIR_Attr, LDIR_Type,
                                   LDIR_Chksum, LDIR_Name2, LDIR_FstClusLO,
                                   LDIR_Name3)))
        self.lfn_entries[LDIR_Ord] = mapped_entries

    def is_lfn_entry_complete(self):
        for k in self.lfn_entries.keys():
            if (int(k) & self.LAST_LONG_ENTRY) == self.LAST_LONG_ENTRY:
                return True

        return False


def make_8dot3_name(dir_name: str, dir_entry: FATDirectoryEntry):
    dirs, files, _ = dir_entry.get_entries()
    dir_entries = [e.get_short_name() for e in dirs+files]

    extsep = "."

    try:
        basename = dir_name.upper().rsplit(".", 1)[0][0:8]
    except IndexError:
        basename = ""

    try:
        extname = dir_name.upper().rsplit(".", 1)[1][0:3]
    except IndexError:
        extname = ""

    if len(extname) == 0:
        extsep = ""

    i = 0
    while len(str(i)) + 1 <= 7:
        if i > 0:
            maxlen = 8-(len(str(i))+1)
            basename = f"{basename[0:maxlen]}~{i}"

        short_name = f"{basename}{extsep}{extname}"

        if short_name not in dir_entries:
            return short_name
        i += 1

    raise PyFATException("Cannot generate 8dot3 filename, "
                         "unable to find suiting short file name.",
                         errno=errno.EEXIST)


def make_lfn_entry(dir_name: str, encoding: str = 'ibm437'):
    lfn_entry = FATLongDirectoryEntry()
    lfn_entry_length = 13
    dir_name = bytearray(dir_name.encode(encoding))
    dir_name_modulus = len(dir_name) % lfn_entry_length
    lfn_dir_name = bytearray()

    if len(dir_name) > 255:
        raise PyFATException("Long file name exceeds 255 "
                             "characters, not supported.",
                             errno=errno.ENAMETOOLONG)

    i = 0
    while i < len(dir_name):
        lfn_dir_name.extend([dir_name[i], 0x00])
        i += 1

    if dir_name_modulus == 0:
        # Remove last NULL byte if string evenly fits to LFN entries
        lfn_dir_name = lfn_dir_name[:-1]
    else:
        # Fill the rest with 0xFF if it doesn't fit evenly
        padding = lfn_entry_length - (len(lfn_dir_name) % lfn_entry_length)
        lfn_dir_name.extend([0xFF]*padding)

    # Generate linked LFN entries
    lfn_entries = len(lfn_dir_name) // lfn_entry_length*2
    for i in range(lfn_entries):
        if i == lfn_entries:
            lfn_entry_ord = 0x40
        else:
            lfn_entry_ord = i

        n = i*lfn_entry_length*2
        dirname1 = lfn_dir_name[n:n+10]
        n += 10
        dirname2 = lfn_dir_name[n:n+12]
        n += 12
        dirname3 = lfn_dir_name[n:n+4]
        # TODO: Generate checksum
        lfn_entry.add_lfn_entry(LDIR_Ord=lfn_entry_ord,
                                LDIR_Name1=dirname1,
                                LDIR_Attr=FATDirectoryEntry.ATTR_LONG_NAME,
                                LDIR_Type=0x00,
                                LDIR_Chksum=0x00,
                                LDIR_Name2=dirname2,
                                LDIR_FstClusLO=0,
                                LDIR_Name3=dirname3)
    return lfn_entry
