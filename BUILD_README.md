# Building PS3 Memory Card Manager Executable

This guide will help you create a standalone executable from the Python source code.

## Important Note: Cross-Platform Building

⚠️ **PyInstaller can only create executables for the platform it's running on:**
- **Windows** → Creates `.exe` files
- **Linux** → Creates Linux binaries  
- **macOS** → Creates macOS applications

**To build Windows executables from Linux**, use the GitHub Actions workflow (see below).

## Prerequisites

- Python 3.7 or higher
- PS3 memory card adapter connected (for testing)

## Quick Build (Windows)

1. **Double-click `build.bat`** - This will automatically:
   - Install required dependencies
   - Build the executable
   - Clean up temporary files

2. **Wait for completion** - The build process takes a few minutes

3. **Find your executable** - `PS3MemoryCardManager.exe` will be created in the project folder

## Manual Build Process

If you prefer to do it manually or are on Linux/Mac:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the build script
python build_exe.py
```

## Build Options

The build script uses these PyInstaller options:

- `--onefile`: Creates a single executable file (larger but self-contained)
- `--windowed`: No console window (pure GUI app)
- `--collect-all usb`: Includes all USB backend modules
- `--collect-all pyDes`: Includes encryption modules

## Troubleshooting

### "PyInstaller not found"
```bash
pip install pyinstaller
```

### "Module not found" errors
The build script automatically includes hidden imports for USB backends. If you get import errors, you may need to add more `--hidden-import` flags.

### Large executable size
The .exe file will be 50-100MB because it includes:
- Python interpreter
- All dependencies (tkinter, pyusb, pyDes)
- USB backend libraries

This is normal for PyInstaller executables.

### USB permissions on Windows
The executable may need to run as Administrator to access USB devices, depending on your system configuration.

## Distribution

To share your executable:

1. Copy `PS3MemoryCardManager.exe` to the target computer
2. Ensure PS3 memory card adapter drivers are installed
3. Run the executable (may require Administrator privileges)

No Python installation needed on the target machine! 🎉

## Advanced Options

For smaller file size, you can modify `build_exe.py` to use `--onedir` instead of `--onefile`, which creates a folder with the executable and supporting files instead of a single large file.

For debugging, remove the `--windowed` flag to see console output.

## Cross-Platform Building with GitHub Actions

If you're on Linux/Mac but need Windows executables, use the included GitHub Actions workflow:

1. **Push your code to GitHub**
2. **Go to the "Actions" tab** in your repository
3. **Click "Build Windows Executable"** and run the workflow
4. **Download the built executable** from the artifacts

The workflow automatically builds executables for both Windows and Linux on every push!

### Manual Cross-Platform Options:

1. **Windows VM**: Run Windows in VirtualBox/VMware
2. **Docker with Wine**: Complex but possible for Windows executables
3. **Cloud CI/CD**: Use GitHub Actions, Azure DevOps, or similar
4. **Cross-compilation tools**: Limited support, not recommended for GUI apps
