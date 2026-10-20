"""
ECC used by PS2 memory cards.

Each 512 byte page carries 16 bytes of ECC: a 3 byte Hamming code for each of
its four 128 byte chunks, followed by 4 zero bytes. A Hamming code holds the
column parity (which bits of the chunk have odd parity) and two line parities
(which byte offsets hold a byte of odd parity, and their complement).
"""

CHUNK_SIZE = 128

_PARITY = [bin(value).count('1') & 1 for value in range(256)]

# Bit i of the column parity covers the bits of the byte selected by mask i,
# bit 3 is always 0
_COLUMN_MASKS = (0x55, 0x33, 0x0F, 0x00, 0xAA, 0xCC, 0xF0)
_COLUMN_BITS = [sum(_PARITY[value & mask] << bit for bit, mask in enumerate(_COLUMN_MASKS))
                for value in range(256)]


def chunk_ecc(chunk: bytes) -> bytes:
    """Hamming code of a 128 byte chunk"""
    column_parity = 0x77
    line_parity = 0x7F
    line_parity_inverted = 0x7F
    for offset, value in enumerate(chunk):
        column_parity ^= _COLUMN_BITS[value]
        if _PARITY[value]:
            line_parity ^= offset
            line_parity_inverted ^= ~offset & 0x7F
    return bytes((column_parity, line_parity_inverted, line_parity))


def page_ecc(page: bytes) -> bytes:
    """16 byte ECC area of a 512 byte page"""
    ecc = b''.join(chunk_ecc(page[i:i + CHUNK_SIZE]) for i in range(0, len(page), CHUNK_SIZE))
    return ecc + bytes(16 - len(ecc))
