import struct

# PS2 memory card physical layout
PAGE_SIZE = 512
ECC_SIZE = 16
PAGES_PER_CLUSTER = 2
PHYSICAL_PAGE_SIZE = PAGE_SIZE + ECC_SIZE
PHYSICAL_CLUSTER_SIZE = PHYSICAL_PAGE_SIZE * PAGES_PER_CLUSTER  # 1056 bytes
LOGICAL_CLUSTER_SIZE = PAGE_SIZE * PAGES_PER_CLUSTER           # 1024 bytes

def print_hex_dump(data, bytes_per_line=16):
    """Print data as a proper hex dump with offsets and ASCII"""
    for i in range(0, len(data), bytes_per_line):
        # Offset
        print(f"{i:04X}: ", end="")
        
        # Hex values
        hex_part = " ".join(f"{b:02X}" for b in data[i:i+bytes_per_line])
        print(f"{hex_part:<48}", end="")
        
        # ASCII representation
        ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in data[i:i+bytes_per_line])
        print(f" |{ascii_part}|")

def read_cluster(cluster_num, fp):
    """
    Read a logical cluster from the PS2 memory card image,
    stripping ECC bytes.
    """
    fp.seek(cluster_num * PHYSICAL_CLUSTER_SIZE)
    data = fp.read(PHYSICAL_CLUSTER_SIZE)
    if len(data) != PHYSICAL_CLUSTER_SIZE:
        raise ValueError(f"Failed to read cluster {cluster_num}")

    # Strip ECC: take first 512 bytes of each page
    page1 = data[0:PAGE_SIZE]
    page2 = data[PHYSICAL_PAGE_SIZE:PHYSICAL_PAGE_SIZE + PAGE_SIZE]
    return page1 + page2  # 1024 bytes logical cluster

def get_fat_entry(fat_index, superblock, fp):
    """
    Get the FAT entry (next cluster in chain) for a given fat_index.
    
    :param fat_index: cluster number relative to alloc_offset
    :param superblock: dict containing:
        - 'alloc_offset': integer
        - 'ifc_table': list of cluster numbers from superblock
    :param fp: open file object of PS2 memory card image
    :return: FAT entry as 32-bit int (next cluster or 0xFFFFFFFF for EOC)
    """
    fat_offset       = fat_index % 256
    indirect_index   = fat_index // 256
    indirect_offset  = indirect_index % 256
    dbl_indirect_idx = indirect_index // 256

    print("fat_offset: " + str(fat_offset))
    print("indirect_index: " + str(indirect_index))
    print("indirect_offset: " + str(indirect_offset))
    print("dbl_indirect_idx: " + str(dbl_indirect_idx))

    # Step 2: fetch the indirect cluster number from IFC table
    indirect_cluster_num = superblock['ifc_table'][dbl_indirect_idx]
    print("indirect_cluster_num: " + str(indirect_cluster_num))
    indirect_data = read_cluster(indirect_cluster_num, fp)
    indirect_cluster = struct.unpack("<256I", indirect_data)
    fat_cluster_num = indirect_cluster[indirect_offset]

    # Step 3: read the FAT cluster itself
    fat_data = read_cluster(fat_cluster_num, fp)
    print("fat_cluster_num: " + str(fat_cluster_num))
    fat_cluster = struct.unpack("<256I", fat_data)
    # Step 4: extract the entry for our cluster
    entry = fat_cluster[fat_offset]

    print_hex_dump(fat_cluster[fat_offset-10:fat_offset+10])

    return entry

def follow_chain(start_cluster, superblock, fp):
    """
    Follow the FAT chain starting from start_cluster until end-of-chain.
    Returns a list of cluster numbers (absolute clusters).
    """
    alloc_offset = superblock['alloc_offset']
    chain = []
    cluster = start_cluster

    while True:
        chain.append(cluster)
        fat_index = cluster - alloc_offset
        print("fat_index: " + str(fat_index))
        entry = get_fat_entry(fat_index, superblock, fp)
        print("0x%08X" % entry)

        # End-of-chain marker
        if entry == 0xFFFFFFFF:
            break

        # MSB = 1, lower 31 bits = next cluster relative to alloc_offset
        next_cluster = alloc_offset + (entry & 0x7FFFFFFF)
        cluster = next_cluster

    return chain

superblock = {
    "alloc_offset": 49,
    "rootdir_cluster": 0,
    "ifc_table": [16]  # replace with actual values
}

start_cluster = superblock['rootdir_cluster'] + superblock['alloc_offset'] # root directory
with open("test.ps2", "rb") as fp:
    chain = follow_chain(start_cluster, superblock, fp)
    print(f"Cluster chain for root directory: {chain}")
