from abc import ABC, abstractmethod
import struct

# Card flag constants - because magic numbers are so 1990s
CF_USE_ECC = 0x01          # Card supports ECC
CF_BAD_BLOCK = 0x08        # Card may have bad blocks  
CF_ERASE_ZEROES = 0x10     # Erased blocks have all bits set to zero

class Ps2MemoryCardReader(ABC):
    """
    Abstract interface for PS2 Memory Card reading operations.
    Because apparently we need to make everything object-oriented these days. 🙄
    """

    superblock_cache = None
    
    @abstractmethod
    def open(self) -> None:
        """
        Opens the memory card connection.
        Returns nothing because void methods are so much fun!
        """
        pass
    
    @abstractmethod
    def read_cluster(self, number: int) -> bytes:
        """
        Reads a cluster from the memory card.
        
        Args:
            number: The cluster number to read (because we're not psychic)
            
        Returns:
            The cluster data as bytes, or empty bytes if something goes wrong
            (which it probably will, because memory cards are finicky little beasts)
        """
        pass

    @abstractmethod
    def generate_superblock_info(self) -> dict:
        """
        Extracts the superblock from the memory card.
        """
        pass

    def get_superblock_info(self) -> dict:
        """
        Gets the superblock from the memory card.
        """
        if self.superblock_cache is None:
            self.superblock_cache = self.generate_superblock_info()
        return self.superblock_cache

    def has_ecc_support(self) -> bool:
        """
        Checks if the card supports ECC (Error Correction Code).
        Returns True if CF_USE_ECC flag is set.
        """
        return bool(self.get_superblock_info()['card_flags'] & CF_USE_ECC)
    
    def has_bad_blocks(self) -> bool:
        """
        Checks if the card may have bad blocks.
        Returns True if CF_BAD_BLOCK flag is set.
        """
        return bool(self.get_superblock_info()['card_flags'] & CF_BAD_BLOCK)
    
    def erased_blocks_are_zeroes(self) -> bool:
        """
        Checks if erased blocks have all bits set to zero.
        Returns True if CF_ERASE_ZEROES flag is set.
        """
        return bool(self.get_superblock_info()['card_flags'] & CF_ERASE_ZEROES)

    def get_fat_entry(self, fat_index):
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

        print(f"fat_offset: {fat_offset}")
        print(f"indirect_index: {indirect_index}")
        print(f"indirect_offset: {indirect_offset}")
        print(f"dbl_indirect_idx: {dbl_indirect_idx}")

        superblock = self.get_superblock_info()

        # Step 2: fetch the indirect cluster number from IFC table
        indirect_cluster_num = superblock['ifc_list'][dbl_indirect_idx]
        indirect_data = self.read_cluster(indirect_cluster_num)

        # indirect cluster contains 256 little-endian cluster numbers
        indirect_cluster = struct.unpack("<256I", indirect_data)
        fat_cluster_num = indirect_cluster[indirect_offset]

        # Step 3: read the FAT cluster itself
        fat_data = self.read_cluster(fat_cluster_num)
        fat_cluster = struct.unpack("<256I", fat_data)

        # Step 4: extract the entry for our cluster
        entry = fat_cluster[fat_offset]
        return entry

    def parse_datetime(self, dt_bytes):
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

    def parse_directory_entry(self, entry_data):
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
        entry['created'] = self.parse_datetime(entry_data[8:16])
        
        # Cluster (4 bytes) - relative to alloc_offset
        entry['cluster'] = struct.unpack('<I', entry_data[16:20])[0]
        
        # Modified datetime (8 bytes)
        entry['modified'] = self.parse_datetime(entry_data[24:32])
        
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

    def get_root_directory_cluster(self):
        superblock_info = self.get_superblock_info()
        return superblock_info['rootdir_cluster'] + superblock_info['alloc_offset']

    def get_directories_clusters(self, start_cluster):
        superblock_info = self.get_superblock_info()
        alloc_offset = superblock_info['alloc_offset']
        directories = []
        cluster = start_cluster
        while True:
            directories.append(cluster)
            entry = self.get_fat_entry(cluster - alloc_offset)
            print(f"Entry for cluster {cluster}: 0x{entry:08X}")
            if entry == 0xFFFFFFFF:
                break
            cluster = alloc_offset + (entry & 0x7FFFFFFF)
        return directories

    def get_directories_entries(self, start_cluster):
        directories = self.get_directories_clusters(start_cluster)
        entries = []
        for cluster in directories:
            print(f"Reading cluster {cluster}")
            entry_data = self.read_cluster(cluster)
            first_entry = self.parse_directory_entry(entry_data[0:512])
            second_entry = self.parse_directory_entry(entry_data[512:512+512])

            if first_entry is not None:
                entries.append(first_entry)
            if second_entry is not None:
                entries.append(second_entry)
        return entries

class VirtualPs2MemoryCardReader(Ps2MemoryCardReader):
    """
    A virtual PS2 Memory Card reader that reads from a file.
    """
    memory_card_file = None

    def __init__(self, file_path: str):
        self.file_path = file_path

    def open(self) -> None:
        self.memory_card_file = open(self.file_path, "rb")
    
    def read_cluster(self, number: int) -> bytes:
        superblock_info = self.get_superblock_info()
        has_ecc = self.has_ecc_support()

        page_size = superblock_info['page_len']

        if has_ecc:
            page_size += 16

        pages_per_cluster = superblock_info['pages_per_cluster']

        cluster_start = number * pages_per_cluster * page_size
        cluster_size = pages_per_cluster * page_size

        self.memory_card_file.seek(cluster_start)
        data = self.memory_card_file.read(cluster_size)

        # TODO: Handle ECC
        if has_ecc:
            data1 = data[0:page_size - 16]
            data2 = data[page_size:page_size + page_size - 16]
            data = data1 + data2

        return data
    
    def generate_superblock_info(self) -> dict:
        self.memory_card_file.seek(0)
        superblock_info = self.memory_card_file.read(340)
        # Parse the superblock according to PS2 memory card format
        data = {}
        # 0x00: Magic (28 bytes) - should be "Sony PS2 Memory Card Format "
        data['magic'] = superblock_info[0x00:0x1C].decode('ascii', errors='ignore').rstrip('\x00')
        # 0x1C: Version (12 bytes) - format version
        data['version'] = superblock_info[0x1C:0x28].decode('ascii', errors='ignore').rstrip('\x00')
        # 0x28: Page length (2 bytes, little-endian) - 512 bytes data + 16 bytes ECC = 528 total
        data['page_len'] = struct.unpack('<H', superblock_info[0x28:0x2A])[0]
        # 0x2A: Pages per cluster (2 bytes, little-endian)
        data['pages_per_cluster'] = struct.unpack('<H', superblock_info[0x2A:0x2C])[0]
        # 0x2C: Pages per block (2 bytes, little-endian)
        data['pages_per_block'] = struct.unpack('<H', superblock_info[0x2C:0x2E])[0]
        # 0x2E: Unused field (2 bytes, should be 0xFF00)
        data['unused_field'] = struct.unpack('<H', superblock_info[0x2E:0x30])[0]
        # 0x30: Clusters per card (4 bytes, little-endian)
        data['clusters_per_card'] = struct.unpack('<I', superblock_info[0x30:0x34])[0]
        # 0x34: Allocation offset (4 bytes, little-endian) - cluster offset of first allocatable cluster
        data['alloc_offset'] = struct.unpack('<I', superblock_info[0x34:0x38])[0]
        # 0x38: Allocation end (4 bytes, little-endian)
        data['alloc_end'] = struct.unpack('<I', superblock_info[0x38:0x3C])[0]

        # 0x3C: Root directory cluster (4 bytes, little-endian) - relative to alloc_offset
        data['rootdir_cluster'] = struct.unpack('<I', superblock_info[0x3C:0x40])[0]

        # 0x40: Backup block 1 (4 bytes, little-endian)
        data['backup_block1'] = struct.unpack('<I', superblock_info[0x40:0x44])[0]

        # 0x44: Backup block 2 (4 bytes, little-endian)
        data['backup_block2'] = struct.unpack('<I', superblock_info[0x44:0x48])[0]
        # 0x50: IFC list (32 words = 128 bytes)
        data['ifc_list'] = []
        for i in range(32):
            offset = 0x50 + (i * 4)
            value = struct.unpack('<I', superblock_info[offset:offset+4])[0]
            data['ifc_list'].append(value)
        
        # 0xD0: Bad block list (32 words = 128 bytes)
        data['bad_block_list'] = []
        for i in range(32):
            offset = 0xD0 + (i * 4)
            value = struct.unpack('<I', superblock_info[offset:offset+4])[0]
            data['bad_block_list'].append(value)
        
        # 0x150: Card type (1 byte)
        data['card_type'] = superblock_info[0x150]
        
        # 0x151: Card flags (1 byte)
        data['card_flags'] = superblock_info[0x151]

        return data