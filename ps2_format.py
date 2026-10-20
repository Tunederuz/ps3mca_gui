"""
Formatting standard 8 MB PS2 memory cards.

The layout is the one PCSX2 gives new cards, which the PS2 BIOS uses too:
- cluster 0: superblock, the rest of block 0 filled with 0xFF
- cluster 8: indirect FAT cluster, listing the FAT clusters 9 to 40
- clusters 9-40: FAT, every allocatable cluster free except the root directory
- cluster 41: first allocatable cluster, holding the root directory '.' and '..'
- blocks 1022 and 1023: backup blocks, block 1023 starting with a copy of the superblock
Every other page is left erased.
"""

import struct
import time

from ps2_ecc import page_ecc

PAGE_SIZE = 512
ECC_SIZE = 16
PAGES_PER_CLUSTER = 2
PAGES_PER_BLOCK = 16
CLUSTERS_PER_CARD = 8192
PAGES_PER_CARD = CLUSTERS_PER_CARD * PAGES_PER_CLUSTER
CLUSTER_SIZE = PAGE_SIZE * PAGES_PER_CLUSTER
ENTRIES_PER_CLUSTER = CLUSTER_SIZE // 4
CLUSTERS_PER_BLOCK = PAGES_PER_BLOCK // PAGES_PER_CLUSTER

INDIRECT_FAT_CLUSTER = 8
FIRST_FAT_CLUSTER = 9
FAT_CLUSTERS = CLUSTERS_PER_CARD // ENTRIES_PER_CLUSTER
ALLOC_OFFSET = FIRST_FAT_CLUSTER + FAT_CLUSTERS
BACKUP_BLOCK1 = PAGES_PER_CARD // PAGES_PER_BLOCK - 1
BACKUP_BLOCK2 = BACKUP_BLOCK1 - 1
ALLOC_END = CLUSTERS_PER_CARD - ALLOC_OFFSET - 2 * CLUSTERS_PER_BLOCK

CARD_TYPE = 2
CARD_FLAGS = 0x2B
# Written by the PS2 BIOS and PCSX2 after the documented superblock fields
MAX_ALLOCATABLE_CLUSTERS = 0x1F41

FAT_FREE = 0x7FFFFFFF
FAT_CHAIN_END = 0xFFFFFFFF

ERASED_PAGE = b'\xff' * (PAGE_SIZE + ECC_SIZE)
IMAGE_SIZE = PAGES_PER_CARD * (PAGE_SIZE + ECC_SIZE)


def ps2_time(when=None):
    """8 byte PS2 timestamp. The PS2 keeps its clock in Japan time (UTC+9)"""
    t = time.gmtime((time.time() if when is None else when) + 9 * 3600)
    return struct.pack('<BBBBBBH', 0, t.tm_sec, t.tm_min, t.tm_hour, t.tm_mday, t.tm_mon, t.tm_year)


def superblock():
    data = bytearray(b'\xff' * PAGE_SIZE)
    data[:0x17C] = bytes(0x17C)
    data[0x00:0x1C] = b'Sony PS2 Memory Card Format '
    data[0x1C:0x28] = b'1.2.0.0'.ljust(12, b'\x00')
    struct.pack_into('<HHHHIIIIII', data, 0x28, PAGE_SIZE, PAGES_PER_CLUSTER, PAGES_PER_BLOCK, 0xFF00,
                     CLUSTERS_PER_CARD, ALLOC_OFFSET, ALLOC_END, 0, BACKUP_BLOCK1, BACKUP_BLOCK2)
    struct.pack_into('<I', data, 0x50, INDIRECT_FAT_CLUSTER)
    struct.pack_into('<32I', data, 0xD0, *([0xFFFFFFFF] * 32))
    struct.pack_into('<BBHIIII', data, 0x150, CARD_TYPE, CARD_FLAGS, 0, CLUSTER_SIZE, ENTRIES_PER_CLUSTER,
                     CLUSTERS_PER_BLOCK, 0xFFFFFFFF)
    struct.pack_into('<I', data, 0x170, MAX_ALLOCATABLE_CLUSTERS)
    return bytes(data)


def _directory_entry(mode, length, timestamp, name):
    entry = bytearray(PAGE_SIZE)
    struct.pack_into('<HHI8sII8s', entry, 0, mode, 0, length, timestamp, 0, 0, timestamp)
    entry[64:64 + len(name)] = name
    return bytes(entry)


def formatted_pages(timestamp=None):
    """Data of every page that is not left erased, by page number"""
    timestamp = timestamp or ps2_time()
    filler = b'\xff' * PAGE_SIZE
    pages = {}

    def put_cluster(cluster, data):
        for i in range(PAGES_PER_CLUSTER):
            pages[cluster * PAGES_PER_CLUSTER + i] = data[i * PAGE_SIZE:(i + 1) * PAGE_SIZE].ljust(PAGE_SIZE, b'\xff')

    # Block 0: superblock, then filler
    for page in range(PAGES_PER_BLOCK):
        pages[page] = filler
    pages[0] = superblock()

    indirect = [FIRST_FAT_CLUSTER + i for i in range(FAT_CLUSTERS)]
    put_cluster(INDIRECT_FAT_CLUSTER, struct.pack(f'<{len(indirect)}I', *indirect))

    fat = [FAT_FREE] * CLUSTERS_PER_CARD
    fat[0] = FAT_CHAIN_END                       # the root directory, one cluster
    fat[ALLOC_END:] = [FAT_CHAIN_END] * (CLUSTERS_PER_CARD - ALLOC_END)
    for i in range(FAT_CLUSTERS):
        entries = fat[i * ENTRIES_PER_CLUSTER:(i + 1) * ENTRIES_PER_CLUSTER]
        put_cluster(FIRST_FAT_CLUSTER + i, struct.pack(f'<{ENTRIES_PER_CLUSTER}I', *entries))

    # Root directory, then filler up to the end of its block
    pages[ALLOC_OFFSET * PAGES_PER_CLUSTER] = _directory_entry(0x8427, 2, timestamp, b'.')
    pages[ALLOC_OFFSET * PAGES_PER_CLUSTER + 1] = _directory_entry(0xA426, 0, timestamp, b'..')
    root_block_end = (ALLOC_OFFSET * PAGES_PER_CLUSTER // PAGES_PER_BLOCK + 1) * PAGES_PER_BLOCK
    for page in range(ALLOC_OFFSET * PAGES_PER_CLUSTER + 2, root_block_end):
        pages[page] = filler

    # Backup block 1: superblock copy, then filler
    first = BACKUP_BLOCK1 * PAGES_PER_BLOCK
    for page in range(first, first + PAGES_PER_BLOCK):
        pages[page] = filler
    pages[first] = superblock()
    return pages


def format_image(timestamp=None):
    """A complete .ps2 image of a freshly formatted card"""
    image = bytearray(ERASED_PAGE * PAGES_PER_CARD)
    stride = PAGE_SIZE + ECC_SIZE
    for page, data in formatted_pages(timestamp).items():
        image[page * stride:(page + 1) * stride] = data + page_ecc(data)
    return bytes(image)


def format_file(path, timestamp=None):
    """Create or overwrite a .ps2 file with an empty formatted card"""
    with open(path, 'wb') as f:
        f.write(format_image(timestamp))
