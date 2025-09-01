#!/usr/bin/env python3
"""
PS2 Memory Card Reader
Reads and parses PS2 memory card dump files (.ps2)
Based on the PS2 Memory Card File System specification by Ross Ridge

Note: PS2 memory cards use 1056-byte clusters (1024 bytes data + 32 bytes ECC)
"""

import struct
import sys
import os

PHYSICAL_PAGE_SIZE = 512 + 16  # 528 bytes
PAGES_PER_CLUSTER = 2
PHYSICAL_CLUSTER_SIZE = PHYSICAL_PAGE_SIZE * PAGES_PER_CLUSTER  # 1056

def read_cluster(cluster_num):
    with open("test.ps2", "rb") as f:
        f.seek(cluster_num * PHYSICAL_CLUSTER_SIZE)
        data = f.read(PHYSICAL_CLUSTER_SIZE)
        # strip ECC bytes: keep only the first 512 bytes per page
        page1 = data[0:512]
        page2 = data[528:528+512]
        return page1 + page2  # 1024 bytes logical cluster

def get_fat_entry(fat_index, superblock, read_cluster):
    """
    Resolve the FAT entry for a given cluster index on a PS2 memory card.

    :param fat_index: Cluster index (absolute, e.g., cluster_num - alloc_offset)
    :param superblock: Parsed superblock dictionary with:
        - "alloc_offset"
        - "ifc_list" (array of cluster numbers from superblock)
    :param read_cluster: Function(cluster_num) -> bytes (cluster size 1024)
    :return: 32-bit integer FAT entry (next cluster number, or EOC)
    """

    # Step 1: locate the FAT cluster via double indirection
    fat_offset       = fat_index % 256
    indirect_index   = fat_index // 256
    indirect_offset  = indirect_index % 256
    dbl_indirect_idx = indirect_index // 256

    # Step 2: fetch the indirect cluster number from IFC table
    indirect_cluster_num = superblock['ifc_list'][dbl_indirect_idx]
    indirect_data = read_cluster(indirect_cluster_num)

    # indirect cluster contains 256 little-endian cluster numbers
    indirect_cluster = struct.unpack("<256I", indirect_data)
    fat_cluster_num = indirect_cluster[indirect_offset]

    # Step 3: read the FAT cluster itself
    fat_data = read_cluster(fat_cluster_num)
    fat_cluster = struct.unpack("<256I", fat_data)

    # Step 4: extract the entry for our cluster
    entry = fat_cluster[fat_offset]
    return entry

def get_directories_clusters(start_cluster, superblock):
    alloc_offset = superblock['alloc_offset']
    directories = []
    cluster = start_cluster
    while True:
        directories.append(cluster)
        entry = get_fat_entry(cluster - alloc_offset, superblock, read_cluster)
        if entry == 0xFFFFFFFF:
            break
        cluster = alloc_offset + (entry & 0x7FFFFFFF)
    return directories

def read_superblock(bytes_data):
    """
    Read and parse the PS2 memory card superblock (first 340 bytes)
    
    Args:
        bytes_data (bytes): The bytes to read the superblock from
    """
    if len(bytes_data) < 340:
        raise ValueError(f"File too small: expected 340 bytes, got {len(bytes_data)}")
    
    # Parse the superblock according to PS2 memory card format
    data = {}
    
    # 0x00: Magic (28 bytes) - should be "Sony PS2 Memory Card Format "
    data['magic'] = bytes_data[0x00:0x1C].decode('ascii', errors='ignore').rstrip('\x00')
    
    # 0x1C: Version (12 bytes) - format version
    data['version'] = bytes_data[0x1C:0x28].decode('ascii', errors='ignore').rstrip('\x00')
    
    # 0x28: Page length (2 bytes, little-endian) - 512 bytes data + 16 bytes ECC = 528 total
    data['page_len'] = struct.unpack('<H', bytes_data[0x28:0x2A])[0]
    
    # 0x2A: Pages per cluster (2 bytes, little-endian)
    data['pages_per_cluster'] = struct.unpack('<H', bytes_data[0x2A:0x2C])[0]
    
    # 0x2C: Pages per block (2 bytes, little-endian)
    data['pages_per_block'] = struct.unpack('<H', bytes_data[0x2C:0x2E])[0]
    
    # 0x2E: Unused field (2 bytes, should be 0xFF00)
    data['unused_field'] = struct.unpack('<H', bytes_data[0x2E:0x30])[0]
    
    # 0x30: Clusters per card (4 bytes, little-endian)
    data['clusters_per_card'] = struct.unpack('<I', bytes_data[0x30:0x34])[0]
    
    # 0x34: Allocation offset (4 bytes, little-endian) - cluster offset of first allocatable cluster
    data['alloc_offset'] = struct.unpack('<I', bytes_data[0x34:0x38])[0]
    
    # 0x38: Allocation end (4 bytes, little-endian)
    data['alloc_end'] = struct.unpack('<I', bytes_data[0x38:0x3C])[0]
    
    # 0x3C: Root directory cluster (4 bytes, little-endian) - relative to alloc_offset
    data['rootdir_cluster'] = struct.unpack('<I', bytes_data[0x3C:0x40])[0]
    
    # 0x40: Backup block 1 (4 bytes, little-endian)
    data['backup_block1'] = struct.unpack('<I', bytes_data[0x40:0x44])[0]
    
    # 0x44: Backup block 2 (4 bytes, little-endian)
    data['backup_block2'] = struct.unpack('<I', bytes_data[0x44:0x48])[0]
    
    # 0x50: IFC list (32 words = 128 bytes)
    data['ifc_list'] = []
    for i in range(32):
        offset = 0x50 + (i * 4)
        value = struct.unpack('<I', bytes_data[offset:offset+4])[0]
        data['ifc_list'].append(value)
    
    # 0xD0: Bad block list (32 words = 128 bytes)
    data['bad_block_list'] = []
    for i in range(32):
        offset = 0xD0 + (i * 4)
        value = struct.unpack('<I', bytes_data[offset:offset+4])[0]
        data['bad_block_list'].append(value)
    
    # 0x150: Card type (1 byte)
    data['card_type'] = bytes_data[0x150]
    
    # 0x151: Card flags (1 byte)
    data['card_flags'] = bytes_data[0x151]
    
    return data

def read_cluster_from_bytes(bytes_data, cluster_num, superblock):
    """
    Read a cluster from the bytes data
    
    Args:
        bytes_data (bytes): The entire file as bytes
        cluster_num (int): Cluster number to read (absolute)
        superblock (dict): Parsed superblock data
        
    Returns:
        bytes: Cluster data (including ECC)
    """
    # Calculate offset: superblock (340) + cluster * pages_per_cluster * actual_page_size
    # Note: cluster_num is absolute, not relative to alloc_offset
    # PS2 uses 1056-byte clusters (2 pages × 528 bytes = 1056 bytes total)
    # The superblock reports page_len=512, but that's just the data area
    actual_page_size = superblock['page_len'] + 16  # 512 data + 16 ECC
    offset = cluster_num * superblock['pages_per_cluster'] * actual_page_size
    
    # Cluster size including ECC data
    cluster_size = superblock['pages_per_cluster'] * actual_page_size
    
    if offset + cluster_size > len(bytes_data):
        raise ValueError(f"Cluster {cluster_num} would read beyond file end")
    
    return bytes_data[offset:offset + cluster_size]
        
def parse_datetime(dt_bytes):
    """
    Parse PS2 datetime format
    
    Args:
        dt_bytes (bytes): 8 bytes of datetime data
        
    Returns:
        str: Formatted datetime string
    """
    try:
        # PS2 datetime format: [reserved][sec][min][hour][day][month][year_low][year_high]
        sec = dt_bytes[1]
        minute = dt_bytes[2]
        hour = dt_bytes[3]
        day = dt_bytes[4]
        month = dt_bytes[5]
        year = struct.unpack('<H', dt_bytes[6:8])[0]
        
        if year == 0 or month == 0 or day == 0:
            return "Unknown"
            
        return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{sec:02d}"
    except:
        return "Invalid"

def parse_directory_entry(entry_data):
    """
    Parse a directory entry (512 bytes)
    
    Args:
        entry_data (bytes): 512 bytes of directory entry data
        
    Returns:
        dict: Parsed directory entry or None if empty
    """
    if entry_data[0] == 0:  # Empty entry
        return None
    
    entry = {}
    
    # Mode (2 bytes)
    entry['mode'] = struct.unpack('<H', entry_data[0:2])[0]
    
    # Length (4 bytes)
    entry['length'] = struct.unpack('<I', entry_data[4:8])[0]
    
    # Created datetime (8 bytes)
    entry['created'] = parse_datetime(entry_data[8:16])
    
    # Cluster (4 bytes) - relative to alloc_offset
    entry['cluster'] = struct.unpack('<I', entry_data[16:20])[0]
    
    # Modified datetime (8 bytes)
    entry['modified'] = parse_datetime(entry_data[24:32])
    
    # Attributes (4 bytes)
    entry['attr'] = struct.unpack('<I', entry_data[32:36])[0]
    
    # Name (32 bytes, null-terminated)
    entry['name'] = entry_data[64:96].decode('ascii', errors='ignore').rstrip('\x00')
    
    # Determine if it's a file or directory based on mode flags
    entry['is_dir'] = (entry['mode'] & 0x0020) != 0  # DF_DIRECTORY
    entry['is_file'] = (entry['mode'] & 0x0010) != 0  # DF_FILE
    entry['is_hidden'] = (entry['mode'] & 0x2000) != 0  # DF_HIDDEN
    entry['is_ps1'] = (entry['mode'] & 0x1000) != 0  # DF_PSX
    entry['is_pocketstation'] = (entry['mode'] & 0x0800) != 0  # DF_POCKETSTN
    entry['exists'] = (entry['mode'] & 0x8000) != 0  # DF_EXISTS
    
    # Check if this is a valid entry (not just erased flash)
    if entry['mode'] == 0xFFFF or entry['mode'] == 0x7F7F:
        return None
    
    return entry

def print_directory_listing(entries):
    """
    Pretty print directory listing
    
    Args:
        entries (list): List of directory entries
    """
    if not entries:
        print("📁 Directory is empty")
        print("💡 This memory card appears to be empty or unformatted")
        print("   (No save files or directories found)")
        return
    
    print(f"📁 Directory Contents ({len(entries)} entries)")
    print("=" * 80)
    print(f"{'Type':<6} {'Size':<10} {'Modified':<20} {'Name':<32} {'Cluster':<8}")
    print("-" * 80)
    
    for entry in entries:
        # Type indicator
        if entry['is_dir']:
            type_icon = "📁"
        elif entry['is_ps1']:
            type_icon = "🎮"
        elif entry['is_pocketstation']:
            type_icon = "📱"
        else:
            type_icon = "📄"
        
        # Size formatting
        if entry['is_dir']:
            size_str = "<DIR>"
        else:
            size_str = f"{entry['length']:,}"
        
        # Hidden indicator
        name = entry['name']
        if entry['is_hidden']:
            name = f"[HIDDEN] {name}"
        
        print(f"{type_icon:<6} {size_str:<10} {entry['modified']:<20} {name:<32} {entry['cluster']:<8}")

def print_ps2_superblock_info(data):
    """
    Pretty print the PS2 superblock information
    
    Args:
        data (dict): Parsed superblock data from read_ps2_superblock()
    """
    print("🎮 PS2 Memory Card Superblock Analysis")
    print("=" * 50)
    
    print(f"📋 Magic: '{data['magic']}'")
    print(f"🔢 Version: {data['version']}")
    print(f"📄 Page Length: {data['page_len']} bytes (data area only)")
    print(f"📦 Pages per Cluster: {data['pages_per_cluster']}")
    print(f"🧱 Pages per Block: {data['pages_per_block']}")
    print(f"❓ Unused Field: 0x{data['unused_field']:04X}")
    print(f"💾 Clusters per Card: {data['clusters_per_card']:,}")
    print(f"📍 Allocation Offset: {data['alloc_offset']} (first allocatable cluster)")
    print(f"🏁 Allocation End: {data['alloc_end']}")
    print(f"📁 Root Directory Cluster: {data['rootdir_cluster']} (relative to alloc_offset)")
    print(f"💿 Backup Block 1: {data['backup_block1']}")
    print(f"💿 Backup Block 2: {data['backup_block2']}")
    
    print(f"\n🔗 IFC List (Indirect FAT Clusters):")
    for i, value in enumerate(data['ifc_list']):
        if value != 0:  # Only show non-zero values
            print(f"  [{i:2d}]: {value}")
    
    print(f"\n🚫 Bad Block List:")
    bad_blocks = [i for i, value in enumerate(data['bad_block_list']) if value != 0xFFFFFFFF]
    if bad_blocks:
        for i in bad_blocks:
            print(f"  Block {data['bad_block_list'][i]} is marked as bad")
    else:
        print("  No bad blocks found! 🎉")
    
    print(f"\n🎯 Card Type: {data['card_type']} (should be 2 for PS2)")
    print(f"🚩 Card Flags: 0x{data['card_flags']:02X}")
    
    # Calculate card size using actual page size (including ECC)
    actual_page_size = 528  # 512 data + 16 ECC
    total_size = (data['clusters_per_card'] * data['pages_per_cluster'] * actual_page_size) / (1024 * 1024)
    print(f"\n💾 Estimated Card Size: {total_size:.1f} MB")
    
    # Show actual root directory location
    root_absolute = data['rootdir_cluster'] + data['alloc_offset']
    print(f"📁 Root Directory Absolute Cluster: {root_absolute}")
    
    # Show cluster size info
    cluster_size = data['pages_per_cluster'] * actual_page_size
    print(f"🔧 Cluster Size: {cluster_size} bytes ({data['pages_per_cluster']} pages × {actual_page_size} bytes total)")
    print(f"   Note: Each page is {actual_page_size} bytes (512 data + 16 ECC)")

def main():
    """Main function to run the PS2 reader"""
    if len(sys.argv) < 2:
        print("🎮 PS2 Memory Card Reader & File Explorer")
        print("Usage: python ps2_reader.py <filename.ps2> [--list] [--hex] [--fat]")
        print("  --list: List directory contents")
        print("  --hex: Show hex dump of superblock")
        print("  --fat: Show FAT structure analysis")
        return
    
    filename = sys.argv[1]
    show_hex = "--hex" in sys.argv
    show_list = "--list" in sys.argv
    
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return
    
    try:
        print(f"🔍 Reading PS2 memory card: {filename}")
        print("-" * 50)
        
        # Read the entire file into memory
        with open(filename, 'rb') as f:
            bytes_data = f.read()
        
        print(f"📁 File size: {len(bytes_data):,} bytes")
        
        # Read and parse the superblock
        superblock = read_superblock(bytes_data)
        print_ps2_superblock_info(superblock)
        
        # List directory contents if requested
        if show_list:
            directories = get_directories_clusters(superblock['rootdir_cluster'] + superblock['alloc_offset'], superblock)
            directories_entries = []
            for directory in directories:
                directory_data = read_cluster(directory)
                first_entry = parse_directory_entry(directory_data[0:512])
                second_entry = parse_directory_entry(directory_data[512:512+512])

                if first_entry is not None:
                    directories_entries.append(first_entry)
                if second_entry is not None:
                    directories_entries.append(second_entry)
            print_directory_listing(directories_entries)
        # Show hex dump if requested
        if show_hex:
            print("\n" + "=" * 60)
            print("🔍 Hex Dump of superblock (first 340 bytes)")
            print("=" * 60)
            
            for i in range(0, 340, 16):
                # Offset
                print(f"{i:04X}: ", end="")
                
                # Hex values
                hex_part = " ".join(f"{b:02X}" for b in bytes_data[i:i+16])
                print(f"{hex_part:<48}", end="")
                
                # ASCII representation
                ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in bytes_data[i:i+16])
                print(f" |{ascii_part}|")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
