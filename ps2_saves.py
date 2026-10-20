"""
Game saves: read them from a card, and convert them to and from .psu files.

A save is a folder at the root of the card. The .psu format (EMS adapter,
uLaunchELF) stores it as the card does: the folder's 512 byte directory entry,
its '.' and '..' entries, then each file's entry followed by its data padded
to 1 KB.
"""

import os
from dataclasses import dataclass, field

from ps2_card_writer import (CardWriter, NotEnoughSpaceError, SaveExistsError, DF_DIRECTORY, DF_EXISTS, DF_FILE, ENTRY_SIZE,
                             entry_cluster, entry_length, entry_mode, entry_name, with_fields)

PSU_CLUSTER_SIZE = 1024


class SaveFormatError(Exception):
    pass


@dataclass
class SaveFile:
    entry: bytes
    data: bytes

    @property
    def name(self):
        return entry_name(self.entry)


@dataclass
class Save:
    directory_entry: bytes
    dot_entry: bytes
    dotdot_entry: bytes
    files: list = field(default_factory=list)

    @property
    def name(self):
        return entry_name(self.directory_entry)

    @property
    def size(self):
        return sum(len(f.data) for f in self.files)


def read_save(reader, name):
    """Read a save folder from the root of a card"""
    root = reader.get_root_directory_cluster()
    root_slots = reader.read_directory_slots(root)
    for slot in root_slots[2:entry_length(root_slots[0])]:
        if entry_mode(slot) & DF_EXISTS and entry_name(slot) == name:
            directory_entry = slot
            break
    else:
        raise SaveFormatError(f"No save named {name} on this card")
    if not entry_mode(directory_entry) & DF_DIRECTORY:
        raise SaveFormatError(f"{name} is not a folder")

    slots = reader.read_directory_slots(entry_cluster(directory_entry))
    files = []
    for slot in slots[2:entry_length(directory_entry)]:
        mode = entry_mode(slot)
        if not mode & DF_EXISTS:
            continue
        if not mode & DF_FILE:
            raise SaveFormatError(f"{name}/{entry_name(slot)} is a subfolder, which is not supported")
        length = entry_length(slot)
        data = reader.read_file(entry_cluster(slot), length) if length else b''
        files.append(SaveFile(slot, data))

    directory_entry = with_fields(directory_entry, length=len(files) + 2)
    return Save(directory_entry, slots[0], slots[1], files)


def _padding(length):
    return -length % PSU_CLUSTER_SIZE


def save_to_psu(save, path):
    with open(path, 'wb') as f:
        f.write(with_fields(save.directory_entry, length=len(save.files) + 2, cluster=0, dir_entry=0))
        f.write(with_fields(save.dot_entry, length=0, cluster=0, dir_entry=0))
        f.write(with_fields(save.dotdot_entry, length=0, cluster=0, dir_entry=0))
        for save_file in save.files:
            f.write(with_fields(save_file.entry, length=len(save_file.data), cluster=0, dir_entry=0))
            f.write(save_file.data)
            f.write(bytes(_padding(len(save_file.data))))


def load_psu(path):
    with open(path, 'rb') as f:
        content = f.read()

    def entry_at(offset):
        if offset + ENTRY_SIZE > len(content):
            raise SaveFormatError("The .psu file is truncated")
        return content[offset:offset + ENTRY_SIZE]

    directory_entry = entry_at(0)
    count = entry_length(directory_entry)
    if not entry_mode(directory_entry) & DF_DIRECTORY or count < 2:
        raise SaveFormatError("This is not a .psu save file")

    dot_entry, dotdot_entry = entry_at(ENTRY_SIZE), entry_at(2 * ENTRY_SIZE)
    if entry_name(dot_entry) != '.' or entry_name(dotdot_entry) != '..':
        raise SaveFormatError("This is not a .psu save file")

    offset = 3 * ENTRY_SIZE
    files = []
    for _ in range(count - 2):
        entry = entry_at(offset)
        offset += ENTRY_SIZE
        if entry_mode(entry) & DF_DIRECTORY:
            raise SaveFormatError(f"{entry_name(entry)} is a subfolder, which is not supported")
        length = entry_length(entry)
        if offset + length > len(content):
            raise SaveFormatError(f"{entry_name(entry)} is truncated")
        data = content[offset:offset + length]
        offset += length + _padding(length)
        if entry_mode(entry) & DF_EXISTS:
            files.append(SaveFile(entry, data))

    if not entry_name(directory_entry):
        raise SaveFormatError("The save has no name")
    return Save(directory_entry, dot_entry, dotdot_entry, files)


def extract_to_folder(save, parent_folder):
    """Write the save's files into parent_folder/<save name>, return that path"""
    folder = os.path.join(parent_folder, save.name)
    os.makedirs(folder, exist_ok=True)
    for save_file in save.files:
        name = save_file.name
        if not name or name in ('.', '..') or '/' in name or '\\' in name:
            raise SaveFormatError(f"Unsafe file name {name!r} in the save")
        with open(os.path.join(folder, name), 'wb') as f:
            f.write(save_file.data)
    return folder


def write_save(writer, save):
    """Add a save to a card through a CardWriter"""
    files = [(save_file.entry, save_file.data) for save_file in save.files]
    writer.add_save(save.directory_entry, save.dot_entry, save.dotdot_entry, files)


def import_save(reader, save, replace=False):
    """
    Add a save to a card. With replace, an existing save of the same name is
    deleted first, but only once the new one is known to fit in its place.
    """
    writer = CardWriter(reader)
    if writer.find_save(save.name):
        if not replace:
            raise SaveExistsError(f"A save named {save.name} already exists on this card")
        needed = writer.clusters_needed([len(f.data) for f in save.files])
        available = len(writer.free_clusters()) + writer.save_cluster_count(save.name)
        if needed > available:
            raise NotEnoughSpaceError(
                f"{save.name} needs {needed} KB but only {available} KB would be free on this card")
        writer.delete_save(save.name)
        writer = CardWriter(reader)
    write_save(writer, save)


def delete_save(reader, name):
    CardWriter(reader).delete_save(name)
