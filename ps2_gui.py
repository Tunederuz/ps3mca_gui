#!/usr/bin/env python3
"""
PS2 Memory Card Reader GUI
A modern interface for reading both physical and virtual PS2 memory cards
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
from memory_card_reader import PhysicalPs2MemoryCardReader, VirtualPs2MemoryCardReader

class Ps2MemoryCardGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PS2 Memory Card Reader 🎮")
        self.root.geometry("1000x700")
        self.root.configure(bg='#2b2b2b')
        
        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#ffffff')
        self.style.configure('Header.TLabel', font=('Arial', 12, 'bold'), foreground='#ffffff')
        self.style.configure('Info.TLabel', font=('Arial', 10), foreground='#cccccc')
        
        # Variables
        self.current_reader = None
        self.current_file_path = None
        self.is_physical = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the main UI components"""
        # Main frame
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(main_frame, text="🎮 PS2 Memory Card Reader", 
                              font=('Arial', 20, 'bold'), bg='#2b2b2b', fg='#ffffff')
        title_label.pack(pady=(0, 20))
        
        # Connection frame
        self.setup_connection_frame(main_frame)
        
        # Card info frame
        self.setup_card_info_frame(main_frame)
        
        # Directory listing frame
        self.setup_directory_frame(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
        
    def setup_connection_frame(self, parent):
        """Setup the connection/selection frame"""
        conn_frame = tk.LabelFrame(parent, text="🔌 Connection", bg='#2b2b2b', fg='#ffffff',
                                  font=('Arial', 12, 'bold'))
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Radio buttons for connection type
        self.conn_var = tk.StringVar(value="virtual")
        
        virtual_radio = tk.Radiobutton(conn_frame, text="📁 Virtual Memory Card (.ps2 file)", 
                                      variable=self.conn_var, value="virtual", 
                                      bg='#2b2b2b', fg='#ffffff', selectcolor='#2b2b2b',
                                      command=self.on_connection_change)
        virtual_radio.pack(anchor=tk.W, padx=10, pady=5)
        
        physical_radio = tk.Radiobutton(conn_frame, text="🔌 Physical Memory Card (USB)", 
                                       variable=self.conn_var, value="physical", 
                                       bg='#2b2b2b', fg='#ffffff', selectcolor='#2b2b2b',
                                       command=self.on_connection_change)
        physical_radio.pack(anchor=tk.W, padx=10, pady=5)
        
        # File selection frame
        self.file_frame = tk.Frame(conn_frame, bg='#2b2b2b')
        self.file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(self.file_frame, text="📁 Memory Card File:", bg='#2b2b2b', fg='#ffffff').pack(side=tk.LEFT)
        
        self.file_path_var = tk.StringVar()
        self.file_entry = tk.Entry(self.file_frame, textvariable=self.file_path_var, 
                                  width=50, bg='#3c3c3c', fg='#ffffff', insertbackground='#ffffff')
        self.file_entry.pack(side=tk.LEFT, padx=(10, 5))
        
        self.browse_btn = tk.Button(self.file_frame, text="Browse", command=self.browse_file,
                                   bg='#4a4a4a', fg='#ffffff', relief=tk.FLAT)
        self.browse_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Connect button
        self.connect_btn = tk.Button(conn_frame, text="🔌 Connect", command=self.connect,
                                    bg='#4CAF50', fg='#ffffff', font=('Arial', 12, 'bold'),
                                    relief=tk.FLAT, padx=20, pady=5)
        self.connect_btn.pack(pady=10)
        
        # Initially hide file selection for physical
        self.on_connection_change()
        
    def setup_card_info_frame(self, parent):
        """Setup the card information display frame"""
        self.card_frame = tk.LabelFrame(parent, text="💾 Card Information", bg='#2b2b2b', fg='#ffffff',
                                       font=('Arial', 12, 'bold'))
        self.card_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Card info text widget
        self.card_info_text = scrolledtext.ScrolledText(self.card_frame, height=8, 
                                                       bg='#3c3c3c', fg='#ffffff',
                                                       font=('Consolas', 9))
        self.card_info_text.pack(fill=tk.X, padx=10, pady=10)
        
        # Initially disabled
        self.card_info_text.config(state=tk.DISABLED)
        
    def setup_directory_frame(self, parent):
        """Setup the directory listing frame"""
        dir_frame = tk.LabelFrame(parent, text="📁 Directory Contents", bg='#2b2b2b', fg='#ffffff',
                                 font=('Arial', 12, 'bold'))
        dir_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Directory tree
        self.dir_tree = ttk.Treeview(dir_frame, columns=('Type', 'Size', 'Modified', 'Cluster'), 
                                    show='tree headings', height=15)
        
        # Configure columns
        self.dir_tree.heading('#0', text='Name')
        self.dir_tree.heading('Type', text='Type')
        self.dir_tree.heading('Size', text='Size')
        self.dir_tree.heading('Modified', text='Modified')
        self.dir_tree.heading('Cluster', text='Cluster')
        
        self.dir_tree.column('#0', width=200)
        self.dir_tree.column('Type', width=80)
        self.dir_tree.column('Size', width=100)
        self.dir_tree.column('Modified', width=150)
        self.dir_tree.column('Cluster', width=80)
        
        # Scrollbar
        dir_scrollbar = ttk.Scrollbar(dir_frame, orient=tk.VERTICAL, command=self.dir_tree.yview)
        self.dir_tree.configure(yscrollcommand=dir_scrollbar.set)
        
        self.dir_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dir_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Initially empty (no items to show)
        
    def setup_status_bar(self, parent):
        """Setup the status bar"""
        self.status_var = tk.StringVar(value="Ready to connect")
        status_bar = tk.Label(parent, textvariable=self.status_var, relief=tk.SUNKEN, 
                             anchor=tk.W, bg='#1e1e1e', fg='#ffffff')
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def on_connection_change(self):
        """Handle connection type change"""
        if self.conn_var.get() == "physical":
            self.file_frame.pack_forget()
            self.current_file_path = None
        else:
            self.file_frame.pack(fill=tk.X, padx=10, pady=10)
            
    def browse_file(self):
        """Browse for a .ps2 file"""
        file_path = filedialog.askopenfilename(
            title="Select PS2 Memory Card File",
            filetypes=[("PS2 Memory Card", "*.ps2"), ("All Files", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.current_file_path = file_path
            
    def connect(self):
        """Connect to the memory card (physical or virtual)"""
        try:
            if self.conn_var.get() == "physical":
                self.connect_physical()
            else:
                self.connect_virtual()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.status_var.set(f"Connection failed: {str(e)}")
            
    def connect_physical(self):
        """Connect to physical memory card"""
        self.status_var.set("Connecting to physical memory card...")
        
        def connect_thread():
            try:
                self.current_reader = PhysicalPs2MemoryCardReader()
                self.current_reader.open()
                self.is_physical = True
                
                # Update UI in main thread
                self.root.after(0, self.on_connection_success)
                
            except Exception as e:
                self.root.after(0, lambda: self.on_connection_error(str(e)))
                
        threading.Thread(target=connect_thread, daemon=True).start()
        
    def connect_virtual(self):
        """Connect to virtual memory card file"""
        if not self.current_file_path:
            messagebox.showwarning("No File Selected", "Please select a .ps2 file first")
            return
            
        if not os.path.exists(self.current_file_path):
            messagebox.showerror("File Not Found", "The selected file does not exist")
            return
            
        self.status_var.set("Loading virtual memory card...")
        
        try:
            self.current_reader = VirtualPs2MemoryCardReader(self.current_file_path)
            self.current_reader.open()
            self.is_physical = False
            
            self.on_connection_success()
            
        except Exception as e:
            self.on_connection_error(str(e))
            
    def on_connection_success(self):
        """Handle successful connection"""
        self.status_var.set("Connected successfully! Loading card information...")
        self.connect_btn.config(text="🔌 Disconnect", bg='#f44336', command=self.disconnect)
        
        # Load card information
        self.load_card_info()
        self.load_directory_listing()
        
        self.status_var.set("Ready")
        
    def on_connection_error(self, error_msg):
        """Handle connection error"""
        self.status_var.set(f"Connection failed: {error_msg}")
        messagebox.showerror("Connection Error", f"Failed to connect: {error_msg}")
        
    def disconnect(self):
        """Disconnect from memory card"""
        if self.current_reader:
            if hasattr(self.current_reader, 'memory_card_file') and self.current_reader.memory_card_file:
                self.current_reader.memory_card_file.close()
            self.current_reader = None
            
        self.current_file_path = None
        self.is_physical = False
        
        # Reset UI
        self.connect_btn.config(text="🔌 Connect", bg='#4CAF50', command=self.connect)
        self.card_info_text.config(state=tk.NORMAL)
        self.card_info_text.delete(1.0, tk.END)
        self.card_info_text.config(state=tk.DISABLED)
        
        # Clear all items from the tree
        for item in self.dir_tree.get_children():
            self.dir_tree.delete(item)
            
        self.status_var.set("Disconnected")
        
    def load_card_info(self):
        """Load and display card information"""
        try:
            superblock = self.current_reader.get_superblock_info()
            
            info_text = f"""🎮 PS2 Memory Card Information
{'='*50}
📋 Magic: {superblock['magic']}
🔢 Version: {superblock['version']}
📄 Page Length: {superblock['page_len']} bytes
📦 Pages per Cluster: {superblock['pages_per_cluster']}
🧱 Pages per Block: {superblock['pages_per_block']}
💾 Clusters per Card: {superblock['clusters_per_card']:,}
📍 Allocation Offset: {superblock['alloc_offset']}
🏁 Allocation End: {superblock['alloc_end']}
📁 Root Directory Cluster: {superblock['rootdir_cluster']}
💿 Backup Block 1: {superblock['backup_block1']}
💿 Backup Block 2: {superblock['backup_block2']}
🎯 Card Type: {superblock['card_type']}
🚩 Card Flags: 0x{superblock['card_flags']:02X}

🔧 Card Features:
  • ECC Support: {'Yes' if self.current_reader.has_ecc_support() else 'No'}
  • Bad Blocks: {'Yes' if self.current_reader.has_bad_blocks() else 'No'}
  • Erased Blocks Zeroed: {'Yes' if self.current_reader.erased_blocks_are_zeroes() else 'No'}

💾 Estimated Size: {(superblock['clusters_per_card'] * superblock['pages_per_cluster'] * 528) / (1024*1024):.1f} MB
"""
            
            self.card_info_text.config(state=tk.NORMAL)
            self.card_info_text.delete(1.0, tk.END)
            self.card_info_text.insert(1.0, info_text)
            self.card_info_text.config(state=tk.DISABLED)
            
        except Exception as e:
            self.card_info_text.config(state=tk.NORMAL)
            self.card_info_text.delete(1.0, tk.END)
            self.card_info_text.insert(1.0, f"Error loading card info: {str(e)}")
            self.card_info_text.config(state=tk.DISABLED)
            
    def load_directory_listing(self):
        """Load and display directory listing"""
        try:
            # Clear existing items
            for item in self.dir_tree.get_children():
                self.dir_tree.delete(item)
                
            # Get root directory cluster
            root_cluster = self.current_reader.get_root_directory_cluster()
            
            # Get directory entries
            entries = self.current_reader.get_directories_entries(root_cluster)
            
            # Populate tree
            for entry in entries:
                if entry:  # Skip None entries
                    # Type icon
                    if entry['is_dir']:
                        type_icon = "📁"
                        type_text = "DIR"
                    elif entry['is_ps1']:
                        type_icon = "🎮"
                        type_text = "PS1"
                    elif entry['is_pocketstation']:
                        type_icon = "📱"
                        type_text = "PS"
                    else:
                        type_icon = "📄"
                        type_text = "FILE"
                    
                    # Size formatting
                    if entry['is_dir']:
                        size_str = "<DIR>"
                    else:
                        size_str = f"{entry['length']:,}"
                    
                    # Name with hidden indicator
                    name = entry['name']
                    if entry['is_hidden']:
                        name = f"[HIDDEN] {name}"
                    
                    # Insert into tree
                    item = self.dir_tree.insert('', 'end', text=f"{type_icon} {name}", 
                                              values=(type_text, size_str, entry['modified'], entry['cluster']))
                    
            # Tree is always enabled, just populated with items
            
        except Exception as e:
            messagebox.showerror("Directory Error", f"Failed to load directory: {str(e)}")

def main():
    root = tk.Tk()
    app = Ps2MemoryCardGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
