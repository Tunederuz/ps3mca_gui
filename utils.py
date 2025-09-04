def print_hex(data):
    # Print data like in hex editors
    for i in range(0, len(data), 16):
        print(f"{i:08X}  ", end="")
        for j in range(i, i+16):
            if j < len(data):
                print(f"{data[j]:02X} ", end="")
            else:
                print("   ", end="")
        print("  |", end="")
        for j in range(i, i+16):
            if j < len(data):
                print(f"{chr(data[j])}", end="")
            else:
                print(" ", end="")
        print()