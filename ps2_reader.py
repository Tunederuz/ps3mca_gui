#!/usr/bin/env python3
"""
PS2 Memory Card Reader
Reads and parses PS2 memory card dump files (.ps2)
Based on the PS2 Memory Card File System specification by Ross Ridge

Note: PS2 memory cards use 1056-byte clusters (1024 bytes data + 32 bytes ECC)
"""

import sys
import os
from memory_card_reader import VirtualPs2MemoryCardReader

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
    show_list = "--list" in sys.argv
    
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return
    
    try:
        print(f"🔍 Reading PS2 memory card: {filename}")
        print("-" * 50)
        
        reader = VirtualPs2MemoryCardReader(filename)
        reader.open()        
        
        # Read and parse the superblock
        superblock = reader.get_superblock_info()
        print_ps2_superblock_info(superblock)
        
        # List directory contents if requested
        if show_list:
            directories_entries = reader.get_directories_entries(reader.get_root_directory_cluster())
            print_directory_listing(directories_entries)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
