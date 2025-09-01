#!/usr/bin/env python3
"""
Test script for PS3 Memory Card Directory Navigation Features

This script demonstrates the new directory navigation capabilities
added to ps3mca_extended.py
"""

import sys
import os

def test_directory_listing():
    """Test directory listing functionality"""
    print("=== Testing Directory Listing ===")
    print("Command: python ps3mca_extended.py --list /")
    print("This will list the root directory of the memory card")
    print()

def test_file_extraction():
    """Test file extraction functionality"""
    print("=== Testing File Extraction ===")
    print("Command: python ps3mca_extended.py --extract /FILENAME.EXT output_file.ext")
    print("This will extract a file from the memory card")
    print()

def test_file_injection():
    """Test file injection functionality"""
    print("=== Testing File Injection ===")
    print("Command: python ps3mca_extended.py --inject input_file.ext /FILENAME.EXT")
    print("This will inject a file into the memory card")
    print()

def test_directory_creation():
    """Test directory creation functionality"""
    print("=== Testing Directory Creation ===")
    print("Command: python ps3mca_extended.py --mkdir /NEWDIR")
    print("This will create a new directory on the memory card")
    print()

def test_file_removal():
    """Test file removal functionality"""
    print("=== Testing File Removal ===")
    print("Command: python ps3mca_extended.py --remove /FILENAME.EXT")
    print("This will remove a file from the memory card")
    print()

def test_directory_removal():
    """Test directory removal functionality"""
    print("=== Testing Directory Removal ===")
    print("Command: python ps3mca_extended.py --rmdir /DIRNAME")
    print("This will remove a directory from the memory card")
    print()

def show_help():
    """Show help information"""
    print("PS3 Memory Card Directory Navigation Test Script")
    print("=" * 50)
    print()
    print("This script demonstrates the new features added to ps3mca_extended.py:")
    print()
    print("1. Directory listing (--list)")
    print("2. File extraction (--extract)")
    print("3. File injection (--inject)")
    print("4. Directory creation (--mkdir)")
    print("5. File removal (--remove)")
    print("6. Directory removal (--rmdir)")
    print()
    print("Prerequisites:")
    print("- PS3 Memory Card Adapter connected")
    print("- PS2 Memory Card inserted")
    print("- ps3mca_extended.py in the same directory")
    print()
    print("Usage: python test_directory_nav.py [test_name]")
    print("Available tests: listing, extraction, injection, mkdir, remove, rmdir, all")
    print()

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    test_name = sys.argv[1].lower()
    
    if test_name == "all":
        test_directory_listing()
        test_file_extraction()
        test_file_injection()
        test_directory_creation()
        test_file_removal()
        test_directory_removal()
    elif test_name == "listing":
        test_directory_listing()
    elif test_name == "extraction":
        test_file_extraction()
    elif test_name == "injection":
        test_file_injection()
    elif test_name == "mkdir":
        test_directory_creation()
    elif test_name == "remove":
        test_file_removal()
    elif test_name == "rmdir":
        test_directory_removal()
    else:
        print(f"Unknown test: {test_name}")
        show_help()

if __name__ == "__main__":
    main()
