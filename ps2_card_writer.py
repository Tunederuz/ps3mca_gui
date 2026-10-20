"""
Write access to the PS2 memory card file system.

Changes are staged in memory, then written in an order that keeps the card
consistent if the process stops halfway:
- adding a save writes its data first, then the FAT, then the directory entry,
  so an interruption only leaves unreferenced clusters behind
- deleting a save removes the directory entry first, then frees the FAT
"""

import struct

from ps2_ecc import page_ecc

DF_EXISTS = 0x8000
DF_DIRECTORY = 0x0020
DF_FILE = 0x0010

FAT_ALLOCATED = 0x80000000
FAT_CHAIN_END = 0xFFFFFFFF
FAT_FREE = 0x7FFFFFFF

ENTRY_SIZE = 512
NAME_SIZE = 32


class CardWriteError(Exception):
    pass


class SaveExistsError(CardWriteError):
    pass


class NotEnoughSpaceError(CardWriteError):
    pass


def entry_mode(entry: bytes) -> int:
    return struct.unpack_from('<H', entry, 0)[0]


def entry_length(entry: bytes) -> int:
    return struct.unpack_from('<I', entry, 4)[0]


def entry_cluster(entry: bytes) -> int:
    return struct.unpack_from('<I', entry, 16)[0]


def entry_name(entry: bytes) -> str:
    return entry[64:64 + NAME_SIZE].split(b'\x00', 1)[0].decode('ascii', errors='replace')


def with_fields(entry: bytes, length=None, cluster=None, dir_entry=None, name=None) -> bytes:
    """Copy of a directory entry with some fields replaced"""
    entry = bytearray(entry)
    if length is not None:
        struct.pack_into('<I', entry, 4, length)
    if cluster is not None:
        struct.pack_into('<I', entry, 16, cluster)
    if dir_entry is not None:
        struct.pack_into('<I', entry, 20, dir_entry)
    if name is not None:
        entry[64:64 + NAME_SIZE] = name.encode('ascii').ljust(NAME_SIZE, b'\x00')
    return bytes(entry)


class CardWriter:
    """Stages cluster changes for one operation, then commits them in a safe order"""

    def __init__(self, reader):
        if not reader.supports_writing():
            raise CardWriteError("This memory card cannot be written to")
        self.reader = reader
        superblock = reader.get_superblock_info()
        self.superblock = superblock
        self.alloc_offset = superblock['alloc_offset']
        self.alloc_end = superblock['alloc_end']
        self.pages_per_cluster = superblock['pages_per_cluster']
        self.cluster_size = reader.get_cluster_size()
        self.root_cluster = superblock['rootdir_cluster']
        self._clusters = {}  # absolute cluster -> bytearray
        self._dirty = {}     # absolute cluster -> stage ('data', 'fat' or 'dir')

    # Cluster cache -------------------------------------------------------

    def _cluster(self, absolute):
        if absolute not in self._clusters:
            first_page = absolute * self.pages_per_cluster
            data = b''.join(self.reader.read_page(first_page + i)[0] for i in range(self.pages_per_cluster))
            self._clusters[absolute] = bytearray(data)
        return self._clusters[absolute]

    def _stage(self, absolute, data, stage):
        self._clusters[absolute] = bytearray(data.ljust(self.cluster_size, b'\x00'))
        self._dirty[absolute] = stage

    def commit(self, order):
        """Write every staged cluster, stage by stage"""
        page_size = self.cluster_size // self.pages_per_cluster
        use_ecc = self.reader.has_ecc_support()
        for stage in order:
            for absolute in sorted(c for c, s in self._dirty.items() if s == stage):
                data = bytes(self._clusters[absolute])
                for i in range(self.pages_per_cluster):
                    page = data[i * page_size:(i + 1) * page_size]
                    self.reader.write_page(absolute * self.pages_per_cluster + i, page,
                                           page_ecc(page) if use_ecc else None)
            # Each stage reaches the card before the next one starts
            self.reader.flush()
        self._dirty.clear()
        self.reader.clear_superblock_cache()

    # FAT -----------------------------------------------------------------

    def _fat_location(self, index):
        entries_per_cluster = self.cluster_size // 4
        fat_offset = index % entries_per_cluster
        indirect_index = index // entries_per_cluster
        indirect_cluster = self.superblock['ifc_list'][indirect_index // entries_per_cluster]
        indirect = self._cluster(indirect_cluster)
        fat_cluster = struct.unpack_from('<I', indirect, (indirect_index % entries_per_cluster) * 4)[0]
        return fat_cluster, fat_offset * 4

    def get_fat(self, index):
        fat_cluster, offset = self._fat_location(index)
        return struct.unpack_from('<I', self._cluster(fat_cluster), offset)[0]

    def set_fat(self, index, value):
        fat_cluster, offset = self._fat_location(index)
        struct.pack_into('<I', self._cluster(fat_cluster), offset, value)
        self._dirty[fat_cluster] = 'fat'

    def free_clusters(self):
        return [i for i in range(self.alloc_end) if not self.get_fat(i) & FAT_ALLOCATED]

    def chain(self, start):
        clusters = [start]
        while True:
            entry = self.get_fat(clusters[-1])
            if entry == FAT_CHAIN_END:
                return clusters
            if not entry & FAT_ALLOCATED or len(clusters) > self.alloc_end:
                raise CardWriteError(f"Broken cluster chain starting at {start}")
            clusters.append(entry & ~FAT_ALLOCATED)

    def link(self, clusters):
        """Mark clusters as one allocated chain"""
        for current, following in zip(clusters, clusters[1:]):
            self.set_fat(current, FAT_ALLOCATED | following)
        if clusters:
            self.set_fat(clusters[-1], FAT_CHAIN_END)

    def release(self, start):
        for cluster in self.chain(start):
            self.set_fat(cluster, FAT_FREE)

    # Directories ---------------------------------------------------------

    def directory_slots(self, start):
        """Chain and 512 byte slots of a directory"""
        chain = self.chain(start)
        slots = []
        for cluster in chain:
            data = self._cluster(self.alloc_offset + cluster)
            slots += [data[i:i + ENTRY_SIZE] for i in range(0, len(data), ENTRY_SIZE)]
        return chain, slots

    def _write_slot(self, directory_chain, index, entry, stage):
        slots_per_cluster = self.cluster_size // ENTRY_SIZE
        absolute = self.alloc_offset + directory_chain[index // slots_per_cluster]
        data = self._cluster(absolute)
        offset = (index % slots_per_cluster) * ENTRY_SIZE
        data[offset:offset + ENTRY_SIZE] = entry
        self._dirty[absolute] = stage

    def root_entries(self):
        """(index, entry) of the root slots in use, '.' and '..' excluded"""
        chain, slots = self.directory_slots(self.root_cluster)
        count = entry_length(slots[0])
        return [(i, bytes(slots[i])) for i in range(2, count) if entry_mode(slots[i]) & DF_EXISTS]

    def find_save(self, name):
        for index, entry in self.root_entries():
            if entry_name(entry) == name:
                return index, entry
        return None

    # Saves ---------------------------------------------------------------

    def clusters_needed(self, file_sizes):
        per_cluster = self.cluster_size
        data = sum(-(-size // per_cluster) for size in file_sizes)
        directory = -(-(len(file_sizes) + 2) // (per_cluster // ENTRY_SIZE))
        return data + directory

    def add_save(self, directory_entry, dot_entry, dotdot_entry, files):
        """
        Add a save folder to the root directory.

        directory_entry, dot_entry, dotdot_entry: 512 byte entries of the folder,
        files: list of (512 byte entry, data).
        """
        name = entry_name(directory_entry)
        if not name or len(name.encode('ascii')) >= NAME_SIZE:
            raise CardWriteError(f"Invalid save name {name!r}")
        if not entry_mode(directory_entry) & DF_DIRECTORY:
            raise CardWriteError(f"{name} is not a folder")
        for entry, _ in files:
            if not entry_mode(entry) & DF_FILE:
                raise CardWriteError(f"{name}/{entry_name(entry)} is not a regular file")
        if self.find_save(name):
            raise SaveExistsError(f"A save named {name} already exists on this card")

        # Root slot for the new folder: a deleted one, or a new one at the end
        root_chain, root_slots = self.directory_slots(self.root_cluster)
        root_count = entry_length(root_slots[0])
        free_slot = next((i for i in range(2, root_count) if not entry_mode(root_slots[i]) & DF_EXISTS), None)
        slot_index = free_slot if free_slot is not None else root_count
        extend_root = slot_index >= len(root_slots)

        needed = self.clusters_needed([len(data) for _, data in files]) + (1 if extend_root else 0)
        free = self.free_clusters()
        if needed > len(free):
            raise NotEnoughSpaceError(
                f"{name} needs {needed} KB but only {len(free)} KB are free on this card")
        free.reverse()

        def allocate(count):
            clusters = [free.pop() for _ in range(count)]
            self.link(clusters)
            return clusters

        # File contents
        file_entries = []
        for entry, data in files:
            if data:
                clusters = allocate(-(-len(data) // self.cluster_size))
                for i, cluster in enumerate(clusters):
                    chunk = data[i * self.cluster_size:(i + 1) * self.cluster_size]
                    self._stage(self.alloc_offset + cluster, chunk, 'data')
                first = clusters[0]
            else:
                first = FAT_CHAIN_END
            file_entries.append(with_fields(entry, length=len(data), cluster=first, dir_entry=0))

        # Folder contents: '.' points back to the root slot, then '..' and the files
        entries = [with_fields(dot_entry, length=0, cluster=self.root_cluster, dir_entry=slot_index),
                   with_fields(dotdot_entry, length=0, cluster=0, dir_entry=0)] + file_entries
        slots_per_cluster = self.cluster_size // ENTRY_SIZE
        directory_chain = allocate(-(-len(entries) // slots_per_cluster))
        for i, cluster in enumerate(directory_chain):
            chunk = b''.join(entries[i * slots_per_cluster:(i + 1) * slots_per_cluster])
            self._stage(self.alloc_offset + cluster, chunk, 'data')

        # Root directory: grow its chain if needed, then reference the folder
        if extend_root:
            new_root_cluster = allocate(1)[0]
            self._stage(self.alloc_offset + new_root_cluster, b'', 'data')
            self.set_fat(root_chain[-1], FAT_ALLOCATED | new_root_cluster)
            root_chain.append(new_root_cluster)
        self._write_slot(root_chain, slot_index,
                         with_fields(directory_entry, length=len(entries), cluster=directory_chain[0], dir_entry=0),
                         'dir')
        if slot_index == root_count:
            self._write_slot(root_chain, 0, with_fields(bytes(root_slots[0]), length=root_count + 1), 'dir')

        self.commit(order=('data', 'fat', 'dir'))

    def save_cluster_count(self, name):
        """Clusters a save folder occupies, folder itself included"""
        found = self.find_save(name)
        if not found:
            return 0
        _, entry = found
        directory_chain, directory_slots = self.directory_slots(entry_cluster(entry))
        count = len(directory_chain)
        for slot in directory_slots[2:entry_length(entry)]:
            if entry_mode(slot) & DF_EXISTS and entry_length(slot) and entry_cluster(slot) != FAT_CHAIN_END:
                count += len(self.chain(entry_cluster(slot)))
        return count

    def delete_save(self, name):
        """Remove a save folder from the root directory and free its clusters"""
        found = self.find_save(name)
        if not found:
            raise CardWriteError(f"No save named {name} on this card")
        slot_index, entry = found
        if not entry_mode(entry) & DF_DIRECTORY:
            raise CardWriteError(f"{name} is not a folder")

        directory_start = entry_cluster(entry)
        _, directory_slots = self.directory_slots(directory_start)
        for slot in directory_slots[2:entry_length(entry)]:
            mode = entry_mode(slot)
            if not mode & DF_EXISTS:
                continue
            if mode & DF_DIRECTORY:
                raise CardWriteError(f"{name} contains a subfolder, which is not supported")
            if entry_length(slot) and entry_cluster(slot) != FAT_CHAIN_END:
                self.release(entry_cluster(slot))
        self.release(directory_start)

        root_chain, _ = self.directory_slots(self.root_cluster)
        cleared = bytearray(entry)
        struct.pack_into('<H', cleared, 0, entry_mode(entry) & ~DF_EXISTS)
        self._write_slot(root_chain, slot_index, bytes(cleared), 'dir')

        self.commit(order=('dir', 'fat'))
