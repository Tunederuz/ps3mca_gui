from abc import ABC, abstractmethod
import functools
import itertools
import operator
import struct
import pyDes
import usb.core

# Card flag constants - because magic numbers are so 1990s
CF_USE_ECC = 0x01          # Card supports ECC
CF_BAD_BLOCK = 0x08        # Card may have bad blocks  
CF_ERASE_ZEROES = 0x10     # Erased blocks have all bits set to zero

PLACEHOLDER_FOLDER_NAME = '..'
PARENT_POINTER_FOLDER_NAME = '.'

class Ps2MemoryCardReader(ABC):
    """
    Abstract interface for PS2 Memory Card reading operations.
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
    def read_cluster(self, number: int, include_ecc: bool = False) -> bytes:
        """
        Reads a cluster from the memory card.
        
        Args:
            number: The cluster number to read (because we're not psychic)
            include_ecc: Whether to include the ECC data in the returned bytes
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
        return superblock_info['rootdir_cluster']

    def get_directory_clusters(self, start_cluster):
        superblock_info = self.get_superblock_info()
        alloc_offset = superblock_info['alloc_offset']
        directories = []
        cluster = start_cluster
        while True:
            directories.append(alloc_offset + cluster)
            entry = self.get_fat_entry(cluster)
            if entry == 0xFFFFFFFF:
                break
            cluster = entry & 0x7FFFFFFF
        return directories

    def get_directory_content(self, parent_directory_cluster):
        directories = self.get_directory_clusters(parent_directory_cluster)
        entries = []
        for cluster in directories:
            entry_data = self.read_cluster(cluster)
            first_entry = self.parse_directory_entry(entry_data[0:512])
            second_entry = self.parse_directory_entry(entry_data[512:512+512])

            if first_entry is not None and first_entry['name'] != PLACEHOLDER_FOLDER_NAME:
                is_parent_directory = first_entry['name'] == PARENT_POINTER_FOLDER_NAME

                if is_parent_directory:
                    first_entry['name'] = '<Parent Directory>'
                if not is_parent_directory or (is_parent_directory and parent_directory_cluster != self.get_root_directory_cluster()):
                    entries.append(first_entry)
            if second_entry is not None and second_entry['name'] != PLACEHOLDER_FOLDER_NAME:
                is_parent_directory = second_entry['name'] == PARENT_POINTER_FOLDER_NAME

                if is_parent_directory:
                    second_entry['name'] = '<Parent Directory>'
                if not is_parent_directory or (is_parent_directory and parent_directory_cluster != self.get_root_directory_cluster()):
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
    
    def read_cluster(self, number: int, include_ecc: bool = False) -> bytes:
        superblock_info = self.get_superblock_info()
        has_ecc = self.has_ecc_support()

        if include_ecc and not has_ecc:
            raise ValueError("ECC is not supported by the card")

        page_size = superblock_info['page_len']

        if has_ecc:
            page_size += 16

        pages_per_cluster = superblock_info['pages_per_cluster']

        cluster_start = number * pages_per_cluster * page_size
        cluster_size = pages_per_cluster * page_size

        self.memory_card_file.seek(cluster_start)
        data = self.memory_card_file.read(cluster_size)

        # TODO: Handle ECC
        if has_ecc and not include_ecc:
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

class PhysicalPs2MemoryCardReader(Ps2MemoryCardReader):
    """
    A PS2 Memory Card reader that reads from a physical memory card.
    """

    # You must provide the MagicGate keys here
 
    # TODO: Handle that as configuration
    #CE62F68420B65A81E459FA9A2BB3598A
    key_left  = bytes([0xCE, 0x62, 0xF6, 0x84, 0x20, 0xB6, 0x5A, 0x81, 
                    0xE4, 0x59, 0xFA, 0x9A, 0x2B, 0xB3, 0x59, 0x8A])
    #6C26D37F46EE9DA9
    iv_left   = bytes([0x6C, 0x26, 0xD3, 0x7F, 0x46, 0xEE, 0x9D, 0xA9])

    #7014A32FCC5B1237AC1FBF4ED26D1CC1
    key_right = bytes([0x70, 0x14, 0xA3, 0x2F, 0xCC, 0x5B, 0x12, 0x37, 
                    0xAC, 0x1F, 0xBF, 0x4E, 0xD2, 0x6D, 0x1C, 0xC1])
    #2CD160FA8C2ED362
    iv_right  = bytes([0x2C, 0xD1, 0x60, 0xFA, 0x8C, 0x2E, 0xD3, 0x62])

    #2C5BF48D32749127
    challenge_iv = bytes([0x2C, 0x5B, 0xF4, 0x8D, 0x32, 0x74, 0x91, 0x27])

    commands = {
        "CS_AUTHORIZE":[0xF7, 0x01]
        , "CS_AUTH_00":[0xF0, 0x00]
        , "CS_AUTH_GET_VECTOR":[0xF0, 0x01] + [0x00] * 9
        , "CS_AUTH_GET_PLAIN":[0xF0, 0x02] + [0x00] * 9
        , "CS_AUTH_03":[0xF0, 0x03]
        , "CS_AUTH_GET_NONCE":[0xF0, 0x04] + [0x00] * 9
        , "CS_AUTH_05":[0xF0, 0x05]
        , "CS_AUTH_PUT_CHALLENGE1":[0xF0, 0x06] + [0x00] * 9
        , "CS_AUTH_PUT_CHALLENGE2":[0xF0, 0x07] + [0x00] * 9
        , "CS_AUTH_08":[0xF0, 0x08]
        , "CS_AUTH_09":[0xF0, 0x09]
        , "CS_AUTH_0A":[0xF0, 0x0A]
        , "CS_AUTH_PUT_CHALLENGE3":[0xF0, 0x0B] + [0x00] * 9
        , "CS_AUTH_0C":[0xF0, 0x0C]
        , "CS_AUTH_0D":[0xF0, 0x0D]
        , "CS_AUTH_0E":[0xF0, 0x0E]
        , "CS_AUTH_GET_RESPONSE1":[0xF0, 0x0F] + [0x00] * 9
        , "CS_AUTH_10":[0xF0, 0x10]
        , "CS_AUTH_GET_RESPONSE2":[0xF0, 0x11] + [0x00] * 9
        , "CS_AUTH_12":[0xF0, 0x12]
        , "CS_AUTH_GET_RESPONSE3":[0xF0, 0x13] + [0x00] * 9
        , "CS_AUTH_14":[0xF0, 0x14]
        , "CS_PUT_SENTINEL":[0x27, 0x5A]
        , "CS_GET_SPECS":[0x26] + [0x00] * 9
        , "CS_PUT_READ_INDEX":[0x23] + [0x00] * 5
        , "CS_GET_READ_8":[0x43, 0x08] + [0x00] * 9
        , "CS_PUT_WRITE_INDEX":[0x22] + [0x00] * 5
        , "CS_PUT_WRITE_8":[0x42, 0x08] + [0x00] * 9
        , "CS_IO_FIN":[0x81]
        , "CS_PUT_ERASE_INDEX":[0x21] + [0x00] * 5
        , "CS_ERASE_CONFIRM":[0x82]
        , "CS_ERASE_FIN":[0x12]
    }

    dev = None
    cardflags = None

    cardsize = None
    blocksize = None
    pagesize = None
    erased = None
    eccsize = None

    page_cache = {}
    ecc_cache = {}

    def request_response(self,command, data=None, reverse=True):
        wMaxPacketSize = self.dev[0][(0,0)][0].wMaxPacketSize
        payload = self.commands[command]
        size = len(payload) + 3
        packet = [0xAA, 0x42, size, 0x00, 0x81] + payload + [0x00, 0x00]
        if data:
            if len(data) != payload.count(0x00) - 1:
                raise ValueError(command, "Data is not the correct length")

            if reverse:
                data = data[::-1]

            start = packet.index(0,5)
            packet = packet[:start] + data + [functools.reduce(operator.xor, data)] + packet[start+len(data)+1:]

        self.dev.write(0x02, packet)
        response = self.dev.read(0x81, wMaxPacketSize)

        if response[:2] != bytearray([0x55, 0x5A]):
            raise ValueError(command)

        self.cardflags = response[packet.index(0x00,5)];

        if "GET" in command:
            if reverse:
                r = response[-2:-payload.count(0x00)-2:-1]
                return r[1:], r[0]
            else:
                s = packet.index(0x00,5)+1
                r = response[s:s+payload.count(0x00)]
                return r[:-1], r[-1]

    def magic_gate(self):
        self.request_response("CS_AUTHORIZE")
        self.request_response("CS_AUTH_00")
        vector, ecc = self.request_response("CS_AUTH_GET_VECTOR")
        plain, ecc = self.request_response("CS_AUTH_GET_PLAIN")

        block = bytes([v ^ p for v, p in zip(vector, plain)])

        left = pyDes.triple_des(self.key_left, pyDes.CBC, self.iv_left).encrypt(block)
        right = pyDes.triple_des(self.key_right, pyDes.CBC, self.iv_right).encrypt(block)
        auth_key = left + right

        self.request_response("CS_AUTH_03")
        nonce, ecc = self.request_response("CS_AUTH_GET_NONCE")

        test_block = bytes([0xDE, 0xAD, 0xC0, 0xDE, 0xDE, 0xAD, 0xC0, 0xDE])

        challenge3 = pyDes.triple_des(auth_key, pyDes.CBC, self.challenge_iv).encrypt(test_block)
        challenge2 = pyDes.triple_des(auth_key, pyDes.CBC, challenge3).encrypt(bytes(nonce))
        challenge1 = pyDes.triple_des(auth_key, pyDes.CBC, challenge2).encrypt(bytes(vector))

        self.request_response("CS_AUTH_05")
        self.request_response("CS_AUTH_PUT_CHALLENGE1", data=list(challenge1))
        self.request_response("CS_AUTH_PUT_CHALLENGE2", data=list(challenge2))
        self.request_response("CS_AUTH_08")
        self.request_response("CS_AUTH_09")
        self.request_response("CS_AUTH_0A")
        self.request_response("CS_AUTH_PUT_CHALLENGE3", data=list(challenge3))
        self.request_response("CS_AUTH_0C")
        self.request_response("CS_AUTH_0D")
        self.request_response("CS_AUTH_0E")
        response1, ecc = self.request_response("CS_AUTH_GET_RESPONSE1")
        self.request_response("CS_AUTH_10")
        response2, ecc = self.request_response("CS_AUTH_GET_RESPONSE2")
        self.request_response("CS_AUTH_12")
        response3, ecc = self.request_response("CS_AUTH_GET_RESPONSE3")
        self.request_response("CS_AUTH_14")

        verify1 = pyDes.triple_des(auth_key, pyDes.CBC, self.challenge_iv).decrypt(bytes(response1))
        verify2 = pyDes.triple_des(auth_key, pyDes.CBC, response1).decrypt(bytes(response2))
        verify3 = pyDes.triple_des(auth_key, pyDes.CBC, response2).decrypt(bytes(response3))

        if list(nonce) == list(verify1) and list(test_block) == list(verify2):
            session_key = list(verify3)

        # Sometimes reading hangs if the sentinel isn't explicitly set
        self.request_response("CS_PUT_SENTINEL")

    def read_page(self, num):
        if num in self.page_cache:
            return self.page_cache[num], self.ecc_cache[num]

        page = []
        self.request_response("CS_PUT_READ_INDEX", data=list(struct.pack(">I", num)))
        for _ in range(self.pagesize // 8):
            chunk, ecc = self.request_response("CS_GET_READ_8", reverse=False)
            if functools.reduce(operator.xor, chunk) != ecc:
                raise ValueError("Read ECC error")
            page += chunk

        if self.cardflags & CF_USE_ECC:
            old_ecc = []
            for _ in range(((self.pagesize // 128) * 3 + 4) // 8):
                chunk, ecc = self.request_response("CS_GET_READ_8", reverse=False)
                if functools.reduce(operator.xor, chunk) != ecc:
                    raise ValueError("Read ECC error")
                old_ecc+= chunk

        self.request_response("CS_IO_FIN")

        if self.cardflags & CF_USE_ECC and old_ecc[-1] != self.erased:
            def parityOf(int_type):
                parity = 1
                while (int_type):
                    parity = 1 - parity
                    int_type = int_type & (int_type - 1)
                return(str(parity))

            for j in range(self.pagesize // 128):
                line_parity = []
                column_parity = 0xFF
                for i in range(128):
                    line_parity.append(parityOf(page[j*128+i]))
                    column_parity = column_parity ^ page[j*128+i]

                c = ['0','0']
                for i in range(3):
                    c.insert(1  , parityOf(column_parity & int("".join(itertools.islice(itertools.cycle(['1']*2**i + ['0']*2**i), 8)), 2)))
                    c.insert(i+3, parityOf(column_parity & int("".join(itertools.islice(itertools.cycle(['0']*2**i + ['1']*2**i), 8)), 2)))

                lo = []
                le = []
                for i in range(7):
                    lo.append(parityOf(int("".join(itertools.compress(line_parity, itertools.cycle([1]*2**i + [0]*2**i))), 2)))
                    le.append(parityOf(int("".join(itertools.compress(line_parity, itertools.cycle([0]*2**i + [1]*2**i))), 2)))

                new_ecc = [int("".join(c), 2), int("".join(lo[::-1]), 2), int("".join(le[::-1]), 2)]

                def countSetBits(n):
                    if (n == 0):
                        return 0
                    else:
                        return (n & 1) + countSetBits(n >> 1)

                # Detect errors
                test_ecc = [a ^ b for a, b in zip(old_ecc[j*3:j*3+3], new_ecc)]
                bits = sum(countSetBits(n) for n in test_ecc)
                if bits == 10:
                    print("Data Error")
                    page[(j*128)+(127-test_ecc[1])] ^= 1 << (test_ecc[0] >> 4)
                    # TODO commit page
                elif bits == 1:
                    print("ECC Error")
                    old_ecc[j*3:j*3+3] = new_ecc
                    # TODO commit ecc
                elif bits != 0:
                    pass
                    #print("Unrecoverable Error found in page", num, "chunk", j)

            self.page_cache[num] = page
            self.ecc_cache[num] = old_ecc
        return page, old_ecc

    def write_page(self, num, data=None, ecc=None):
        if data is None:
            raise ValueError("write page no data")

        if self.cardflags & CF_USE_ECC and ecc is None:
            raise ValueError("write page no ecc")

        self.request_response("CS_PUT_WRITE_INDEX", data=list(struct.pack(">I", num)))
        for i in range(self.pagesize // 8):
            self.request_response("CS_PUT_WRITE_8", data=data[i*8:i*8+8], reverse=False)

        if self.cardflags & CF_USE_ECC:
            # chunks are 128 bytes, 3 bytes per ecc, 4 byte padding
            for i in range(((self.pagesize // 128) * 3 + 4) // 8):
                self.request_response("CS_PUT_WRITE_8", data=ecc[i*8:i*8+8], reverse=False)

        self.request_response("CS_IO_FIN")

    def open(self) -> None:
        # TODO: Retry 5 times if it fails
        self.dev = usb.core.find(idVendor=0x054c, idProduct=0x02ea)
        if self.dev is None:
            raise ValueError("ps3mca is not connected")
        self.dev.set_configuration()
    
        retries = 0
        while retries < 5:
            try:   
                self.magic_gate()
                break
            except Exception as e:
                print(e)
            retries += 1

        specs, ecc = self.request_response("CS_GET_SPECS")
        self.cardsize, self.blocksize, self.pagesize = struct.unpack(">IHH", specs)
        self.erased = 0x00 if self.cardflags & CF_ERASE_ZEROES else 0xff
        self.eccsize = 16 if self.cardflags & CF_USE_ECC else 0
    
    def read_cluster(self, number: int, include_ecc: bool = False) -> bytes:
        superblock_info = self.get_superblock_info()
        pages_per_cluster = superblock_info['pages_per_cluster']

        page0, ecc0 = self.read_page(number * pages_per_cluster)
        page1, ecc1 = self.read_page(number * pages_per_cluster + 1)

        if include_ecc:
            data = bytes(page0) + bytes(ecc0) + bytes(page1) + bytes(ecc1)
        else:
            data = bytes(page0) + bytes(page1)

        return data
    
    def generate_superblock_info(self) -> dict:
        page0, ecc0 = self.read_page(0)
        page1, ecc1 = self.read_page(1)

        page0 = bytes(page0)
        page1 = bytes(page1)

        superblock_info = page0 + page1
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