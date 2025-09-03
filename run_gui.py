#!/usr/bin/env python3
"""
Simple launcher for the PS2 Memory Card Reader GUI
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ps2_gui import main
    print("🎮 Starting PS2 Memory Card Reader GUI...")
    main()
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure all required files are in the same directory")
    print("📋 Required files: ps2_gui.py, memory_card_reader.py")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error starting GUI: {e}")
    sys.exit(1)
