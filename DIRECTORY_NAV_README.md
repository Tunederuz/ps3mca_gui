# PS3 Memory Card Adapter - Directory Navigation Features

## Overview

This document describes the new directory navigation and file system operations that have been added to `ps3mca_extended.py`. These features were implemented based on the C code from `ps3mca_tool-main` and provide comprehensive memory card file system access.

## New Features

### 1. Directory Listing (`--list`, `-ls`)

Lists the contents of a directory on the memory card.

```bash
python ps3mca_extended.py --list /
python ps3mca_extended.py -ls /
```

**Output Format:**
```
Listing directory: /
------------------------------------------------------------
Name                     Type     Size       Modified
------------------------------------------------------------
BIEXEC-SYSTEM           <dir>    0          2000-01-01 00:00:00
SYSTEM.CNF              <file>   1,024      2000-01-01 00:00:00
------------------------------------------------------------
Total entries: 2
```

### 2. File Extraction (`--extract`, `-x`)

Extracts a file from the memory card to the local filesystem.

```bash
python ps3mca_extended.py --extract /FILENAME.EXT output_file.ext
python ps3mca_extended.py -x /FILENAME.EXT output_file.ext
```

### 3. File Injection (`--inject`, `-in`)

Injects a local file into the memory card.

```bash
python ps3mca_extended.py --inject input_file.ext /FILENAME.EXT
python ps3mca_extended.py -in input_file.ext /FILENAME.EXT
```

### 4. Directory Creation (`--mkdir`)

Creates a new directory on the memory card.

```bash
python ps3mca_extended.py --mkdir /NEWDIR
```

### 5. File Removal (`--remove`, `-rm`)

Removes a file from the memory card.

```bash
python ps3mca_extended.py --remove /FILENAME.EXT
python ps3mca_extended.py -rm /FILENAME.EXT
```

### 6. Directory Removal (`--rmdir`)

Removes a directory from the memory card.

```bash
python ps3mca_extended.py --rmdir /DIRNAME
```

## Implementation Details

### Memory Card Structures

The implementation includes several key data structures:

- **MCDevInfo**: Contains memory card metadata (magic, version, sizes, offsets)
- **MCFsEntry**: Represents a file system entry (file or directory)
- **MCFHandle**: Manages file/directory handles for operations

### File System Operations

#### Directory Reading
- `mcio_mcDopen()`: Opens a directory for reading
- `mcio_mcDread()`: Reads directory entries one by one
- `mcio_mcDclose()`: Closes a directory

#### File System Navigation
- `read_cluster()`: Reads a cluster from the memory card
- `read_dir_entry()`: Parses directory entries from cluster data
- `parse_datetime()`: Converts PS2 datetime format to readable format

### Error Handling

The implementation includes proper error codes matching the C version:

- `sceMcResSucceed` (0): Operation successful
- `sceMcResNoFormat` (-2): Memory card not formatted
- `sceMcResNoEntry` (-4): Entry not found
- `sceMcResNotDir` (-100): Path is not a directory
- `sceMcResNotFile` (-101): Path is not a file

## Usage Examples

### Basic Directory Navigation

```bash
# List root directory
python ps3mca_extended.py --list /

# List specific directory
python ps3mca_extended.py --list /BIEXEC-SYSTEM
```

### File Operations

```bash
# Extract a save file
python ps3mca_extended.py --extract /SAVE001.00 save_backup.00

# Inject a save file
python ps3mca_extended.py --inject save_backup.00 /SAVE001.00
```

### Directory Management

```bash
# Create a new directory
python ps3mca_extended.py --mkdir /CUSTOM_SAVES

# Remove a directory
python ps3mca_extended.py --rmdir /CUSTOM_SAVES
```

## Testing

A test script `test_directory_nav.py` is provided to demonstrate all the new features:

```bash
# Test all features
python test_directory_nav.py all

# Test specific feature
python test_directory_nav.py listing
python test_directory_nav.py extraction
python test_directory_nav.py injection
python test_directory_nav.py mkdir
python test_directory_nav.py remove
python test_directory_nav.py rmdir
```

## Technical Notes

### Current Limitations

1. **Subdirectory Support**: Currently only root directory listing is fully implemented
2. **File I/O**: File reading/writing operations are stubbed out and need full implementation
3. **FAT Management**: FAT table reading is simplified and needs enhancement
4. **Error Recovery**: ECC error correction is basic and could be improved

### Future Enhancements

1. **Full Subdirectory Support**: Implement path parsing and navigation
2. **Complete File I/O**: Implement file reading, writing, and management
3. **FAT Table Management**: Full FAT reading and writing capabilities
4. **Advanced Error Handling**: Better error recovery and validation
5. **File Attributes**: Support for file permissions and timestamps

### Architecture

The implementation follows the same structure as the C version:

```
Memory Card → Page Cache → Cluster Reading → Directory Parsing → File Operations
```

## Dependencies

- `pyDes`: For MagicGate authentication
- `usb.core`: For USB device communication
- Standard Python libraries: `struct`, `functools`, `itertools`, `operator`

## Compatibility

- **Hardware**: PS3 Memory Card Adapter (USB ID: 0x054c:0x02ea)
- **Cards**: Sony PS2 Memory Cards (8MB, 16MB, 32MB, 64MB)
- **Python**: Python 3.6+
- **OS**: Windows, Linux, macOS (with appropriate USB drivers)

## Troubleshooting

### Common Issues

1. **"ps3mca is not connected"**: Check USB connection and drivers
2. **"Memory card is not formatted"**: Ensure PS2 memory card is properly formatted
3. **"Cannot open directory"**: Verify path exists and is accessible
4. **"File extraction not yet implemented"**: Some features are still in development

### Debug Mode

Enable trace output for debugging:

```bash
python ps3mca_extended.py --list / --trace
```

## Contributing

To contribute to the development of these features:

1. Study the C implementation in `ps3mca_tool-main/src/`
2. Implement missing functionality in Python
3. Test with real hardware
4. Submit improvements and bug fixes

## License

This implementation follows the same license as the original C code (GPL v3).

## Acknowledgments

- Original C implementation authors
- PlayStation 2 memory card format documentation
- MagicGate authentication research
