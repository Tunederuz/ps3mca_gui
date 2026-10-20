# PS2 Memory Card manager
Fully supports:
* Display superblock information
* List content of Physical Memory Card (requires drivers)
* List content of Virtual Memory Card (.ps2 format from PCSX2)
* Erase (unformat) physical Memory Card content
* Load .ps2 files into a physical memory card
* Extract individual files from saves

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