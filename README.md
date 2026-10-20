# PS2 Memory Card Manager
One tool for PS2 memory cards, physical (through the PS3 Memory Card Adaptor) or virtual (.ps2 images from PCSX2):
* Browse the content of a card and show its information and free space
* Export a save as .psu (EMS / uLaunchELF format) or extract it to a folder
* Import .psu saves and delete saves, on .ps2 images and physical cards
* Extract individual files from saves
* Dump a physical card to a .ps2 file, load a .ps2 file onto a physical card
* Create new .ps2 files and format cards, physical or virtual
* Erase (unformat) a physical card

# Downloads
Builds are produced by GitHub Actions (can also be run manually from the Actions tab).
Pushing a `v*` tag (e.g. `v1.0.0`) publishes a GitHub release with:
* `ps2-memory-card-manager-<version>-x86_64.AppImage` (Linux)
* `ps2-memory-card-manager-<version>.exe` (Windows)

libusb is bundled in both builds.

## Windows driver
Install the WinUSB driver for the PS3 Memory Card Adaptor (USB ID `054C:02EA`) with [Zadig](https://zadig.akeo.ie/).

## Linux USB permissions
To use the adaptor without root, add a udev rule:
```
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="02ea", MODE="0666"' | sudo tee /etc/udev/rules.d/99-ps3mca.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## Building locally
```
pip install -r requirements.txt pyinstaller
packaging/build_appimage.sh   # Linux AppImage in dist/
```

# Credits
JasonBrownDeveloper - https://github.com/JasonBrownDeveloper/ps3mca - For ps3mca.py base file used for physical memory card operations
# TODO
* Import `.max` saves (Action Replay Max: `Ps2PowerSave` header, LZARI compressed content)
* Import `.cbs` saves (CodeBreaker: zlib compressed, RC4 encrypted content)
* Erase each block once in Erase All and Load instead of once per page (16 times less wear, one erase clears a whole block on the adaptor)
* Read back and verify the card after a Load, so a badly written card is reported instead of silently corrupted
* Before a Load, read the target card's bad block list and warn when it is not empty
* Smart restore: format the target card and import the saves of a dump one by one instead of copying the raw image, so the target's own layout is kept (needs bad block aware formatting, check how the PS2 BIOS / PS2SDK mcman handles bad blocks first)
