"""
Changing saves on a physical memory card.

Flash memory is rewritten by blocks of 16 pages: one erase command clears the
whole block, which is then written again. A PhysicalCardSession reads the
blocks a change needs as CardWriter asks for them, keeps the changes in memory,
and on each flush rewrites only the blocks that differ, so CardWriter's
crash-safe stage order is kept on the card. Every rewritten block is read back
and compared.
"""

import time

from memory_card_reader import Ps2MemoryCardReader

WRITE_ATTEMPTS = 2

# How long to wait for an erased block to read back as erased
ERASE_TIMEOUT = 2.0


class PhysicalWriteError(Exception):
    pass


def erase_block(device, first_page):
    """
    Erase a block and wait until it reads back as erased.

    Measured on the PS3 adaptor: one erase command clears the whole block, but
    the first page access that follows it is unreliable, a write is dropped and
    a read may return the old content. A throwaway read absorbs it, then the
    first and last pages are polled until both read as erased.
    """
    specs = device.get_card_specs()
    erased = bytes([specs['erased_byte']]) * (specs['pagesize'] + specs['eccsize'])
    last_page = first_page + specs['blocksize'] - 1

    def is_erased(page):
        data, ecc = device.read_page(page)
        return bytes(data) + bytes(ecc)[:specs['eccsize']] == erased

    def wait_until_erased(pages):
        try:
            device.read_page(first_page)
        except ValueError:
            # The throwaway read may come back garbled, it only has to happen
            pass
        deadline = time.monotonic() + ERASE_TIMEOUT
        while not all(is_erased(page) for page in pages):
            if time.monotonic() > deadline:
                return False
            time.sleep(0.01)
        return True

    device.erase_page(first_page)
    if wait_until_erased((first_page, last_page)):
        return

    # Fall back to one erase per page for cards that erase less than a block
    for page in range(first_page, last_page + 1):
        device.erase_page(page)
    if not wait_until_erased(range(first_page, last_page + 1)):
        raise PhysicalWriteError(f"The block starting at page {first_page} could not be erased")


def rewrite_block(device, block, new):
    """Erase one block and write it again with new, the block's bytes in .ps2 image layout"""
    specs = device.get_card_specs()
    page_size, ecc_size = specs['pagesize'], specs['eccsize']
    stride = page_size + ecc_size
    first_page = block * specs['blocksize']
    erased = bytes([specs['erased_byte']]) * stride
    pages = [new[i * stride:(i + 1) * stride] for i in range(specs['blocksize'])]

    for attempt in range(WRITE_ATTEMPTS):
        erase_block(device, first_page)
        for i, page in enumerate(pages):
            # An erased page reads back as erased bytes, nothing to write
            if page != erased:
                device.write_page(first_page + i, page[:page_size], page[page_size:] if ecc_size else None)

        mismatch = None
        for i, page in enumerate(pages):
            data, ecc = device.read_page(first_page + i)
            if bytes(data) != page[:page_size] or (ecc_size and bytes(ecc) != page[page_size:]):
                mismatch = first_page + i
                break
        if mismatch is None:
            return
    raise PhysicalWriteError(f"Page {mismatch} did not read back as written")


class PhysicalCardSession(Ps2MemoryCardReader):
    """
    Block cache over a physical card for one change. CardWriter reads and writes
    pages through it, and each flush pushes the blocks that changed to the card.
    """

    def __init__(self, device):
        self.device = device
        self.specs = device.get_card_specs()
        self.stride = self.specs['pagesize'] + self.specs['eccsize']
        self.original = {}  # block -> bytes as on the card
        self.blocks = {}    # block -> bytearray with the changes
        self.progress = None
        self.superblock_cache = None
        device.clear_superblock_cache()

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def supports_writing(self) -> bool:
        return True

    def get_card_specs(self, refresh: bool = False) -> dict:
        return self.specs

    def generate_superblock_info(self) -> dict:
        return self.device.get_superblock_info()

    def erase_page(self, number: int):
        raise NotImplementedError("Pages are erased by flush")

    def _block(self, block):
        if block not in self.blocks:
            first_page = block * self.specs['blocksize']
            data = b''.join(bytes(page) + bytes(ecc) for page, ecc in
                            (self.device.read_page(first_page + i) for i in range(self.specs['blocksize'])))
            self.original[block] = data
            self.blocks[block] = bytearray(data)
        return self.blocks[block]

    def read_page(self, number: int) -> tuple[bytes, bytes]:
        block = self._block(number // self.specs['blocksize'])
        offset = (number % self.specs['blocksize']) * self.stride
        return (bytes(block[offset:offset + self.specs['pagesize']]),
                bytes(block[offset + self.specs['pagesize']:offset + self.stride]))

    def write_page(self, number: int, data: bytes, ecc: bytes):
        block = self._block(number // self.specs['blocksize'])
        offset = (number % self.specs['blocksize']) * self.stride
        block[offset:offset + self.specs['pagesize']] = data
        if self.specs['eccsize']:
            block[offset + self.specs['pagesize']:offset + self.stride] = ecc

    def flush(self) -> None:
        changed = [block for block in sorted(self.blocks) if self.blocks[block] != self.original[block]]
        for done, block in enumerate(changed):
            new = bytes(self.blocks[block])
            rewrite_block(self.device, block, new)
            self.original[block] = new
            if self.progress:
                self.progress(done + 1, len(changed))
