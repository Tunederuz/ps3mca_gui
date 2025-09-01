#!/usr/bin/env python3
"""
Build script for creating PS3 Memory Card Manager executable
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def clean_build_dirs():
    """Clean up previous build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_name)
    
    # Also clean .spec files
    for spec_file in Path('.').glob('*.spec'):
        print(f"Removing {spec_file}...")
        spec_file.unlink()

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building PS3 Memory Card Manager executable...")
    
    # Determine the correct path separator for --add-data
    # Windows uses semicolon, Unix-like systems use colon
    path_sep = ';' if os.name == 'nt' else ':'
    
    # PyInstaller command with optimized settings
    cmd = [
        'pyinstaller',
        '--onefile',                    # Create a single executable file
        '--windowed',                   # No console window (GUI app)
        '--name=PS3MemoryCardManager',  # Executable name
        '--icon=icon.ico',              # Icon (if available)
        f'--add-data=ps3mca.py{path_sep}.',       # Include the original module
        '--hidden-import=usb.backend.libusb1',    # USB backend
        '--hidden-import=usb.backend.libusb0',    # Alternative USB backend
        '--hidden-import=usb.backend.openusb',    # Another USB backend
        '--collect-all=usb',            # Collect all USB-related modules
        '--collect-all=pyDes',          # Collect pyDes modules
        'ps3mca_gui.py'                 # Main script
    ]
    
    # Remove icon parameter if icon file doesn't exist
    if not os.path.exists('icon.ico'):
        cmd = [arg for arg in cmd if not arg.startswith('--icon')]
        print("Note: No icon.ico found, building without custom icon")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print("PyInstaller not found! Please install it with: pip install pyinstaller")
        return False

def create_simple_icon():
    """Create a simple icon file if none exists"""
    if not os.path.exists('icon.ico'):
        print("Creating a simple icon...")
        try:
            # Try to create a simple icon using PIL if available
            from PIL import Image, ImageDraw
            
            # Create a simple 32x32 icon
            img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw a simple memory card representation
            draw.rectangle([4, 8, 28, 24], fill=(50, 50, 50, 255), outline=(100, 100, 100, 255))
            draw.rectangle([6, 10, 26, 22], fill=(0, 100, 200, 255))
            draw.rectangle([8, 12, 24, 20], fill=(200, 200, 200, 255))
            
            img.save('icon.ico', format='ICO')
            print("Simple icon created!")
            return True
        except ImportError:
            print("PIL not available, skipping icon creation")
            return False
    return True

def post_build_cleanup():
    """Clean up after build"""
    print("Cleaning up build artifacts...")
    
    # Keep only the executable and remove build directories
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    # Move the executable to a more convenient location
    # Different naming for different platforms
    if os.name == 'nt':
        exe_name = 'PS3MemoryCardManager.exe'
    else:
        exe_name = 'PS3MemoryCardManager'
    
    if os.path.exists(f'dist/{exe_name}'):
        if os.path.exists(exe_name):
            os.remove(exe_name)
        shutil.move(f'dist/{exe_name}', exe_name)
        print(f"Executable created: {exe_name}")
        
        # Make executable on Unix-like systems
        if os.name != 'nt':
            os.chmod(exe_name, 0o755)
            print(f"Made {exe_name} executable")
        
        # Remove empty dist directory
        if os.path.exists('dist'):
            shutil.rmtree('dist')
    
    # Clean up spec file
    spec_files = list(Path('.').glob('*.spec'))
    for spec_file in spec_files:
        spec_file.unlink()

def main():
    """Main build process"""
    print("=" * 50)
    print("PS3 Memory Card Manager - Executable Builder")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('ps3mca_gui.py'):
        print("Error: ps3mca_gui.py not found in current directory!")
        print("Please run this script from the project root directory.")
        sys.exit(1)
    
    # Step 1: Clean previous builds
    clean_build_dirs()
    
    # Step 2: Create icon if needed
    create_simple_icon()
    
    # Step 3: Build executable
    if build_executable():
        # Step 4: Post-build cleanup
        post_build_cleanup()
        
        print("\n" + "=" * 50)
        print("BUILD SUCCESSFUL! 🎉")
        print("=" * 50)
        print("Your executable is ready: PS3MemoryCardManager.exe")
        print("\nTo distribute your app:")
        print("1. Copy PS3MemoryCardManager.exe to the target machine")
        print("2. Make sure the PS3 memory card adapter drivers are installed")
        print("3. Run as administrator if USB access requires it")
        print("\nNote: The executable is quite large because it includes")
        print("the entire Python runtime and all dependencies.")
        
    else:
        print("\n" + "=" * 50)
        print("BUILD FAILED! ❌")
        print("=" * 50)
        print("Please check the error messages above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
