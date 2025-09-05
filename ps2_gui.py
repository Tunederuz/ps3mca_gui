#!/usr/bin/env python3
"""
PS2 Memory Card Reader GUI
A modern interface for reading both physical and virtual PS2 memory cards
"""

from time import sleep
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
        
        # Navigation frame
        self.setup_navigation_frame(main_frame)
        
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
        
        # Dump button (initially hidden)
        self.dump_btn = tk.Button(self.card_frame, text="💾 Dump to .ps2 File", 
                                 command=self.dump_physical_card,
                                 bg='#2196F3', fg='#ffffff', font=('Arial', 12, 'bold'),
                                 relief=tk.FLAT, padx=20, pady=5)
        self.dump_btn.pack(pady=(0, 10))
        self.dump_btn.pack_forget()  # Initially hidden
        
        # Load button (initially hidden)
        self.load_btn = tk.Button(self.card_frame, text="📥 Load from .ps2 File", 
                                 command=self.load_to_physical_card,
                                 bg='#FF9800', fg='#ffffff', font=('Arial', 12, 'bold'),
                                 relief=tk.FLAT, padx=20, pady=5)
        self.load_btn.pack(pady=(0, 10))
        self.load_btn.pack_forget()  # Initially hidden
        
        # Erase All button (initially hidden)
        self.erase_btn = tk.Button(self.card_frame, text="🗑️ Erase All", 
                                  command=self.erase_physical_card,
                                  bg='#F44336', fg='#ffffff', font=('Arial', 12, 'bold'),
                                  relief=tk.FLAT, padx=20, pady=5)
        self.erase_btn.pack(pady=(0, 10))
        self.erase_btn.pack_forget()  # Initially hidden
        
        # Progress bar (initially hidden)
        self.progress_frame = tk.Frame(self.card_frame, bg='#2b2b2b')
        self.progress_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.progress_frame.pack_forget()  # Initially hidden
        
        self.progress_label = tk.Label(self.progress_frame, text="Dumping memory card...", 
                                      bg='#2b2b2b', fg='#ffffff', font=('Arial', 10))
        self.progress_label.pack(anchor=tk.W)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate', length=300)
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
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
        
        # Bind double-click event for folder navigation
        self.dir_tree.bind('<Double-1>', self.on_tree_double_click)
        
        # Navigation state variables
        self.navigation_stack = []
        self.current_directory = None
        
    def setup_navigation_frame(self, parent):
        """Setup the navigation frame"""
        nav_frame = tk.LabelFrame(parent, text="🗺️ Navigation", bg='#2b2b2b', fg='#ffffff',
                                  font=('Arial', 12, 'bold'))
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Back button
        self.back_btn = tk.Button(nav_frame, text="⬅️ Back", command=self.navigate_back,
                                   bg='#4a4a4a', fg='#ffffff', font=('Arial', 10, 'bold'),
                                   relief=tk.FLAT, padx=10, pady=5)
        self.back_btn.pack(side=tk.LEFT, padx=5)
        
        # Current directory label
        self.current_dir_label = tk.Label(nav_frame, text="📁 Current Directory: /", 
                                         bg='#2b2b2b', fg='#ffffff', font=('Arial', 10))
        self.current_dir_label.pack(side=tk.LEFT, padx=5)
        
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
                error_msg = str(e)  # Capture the error message
                self.root.after(0, lambda: self.on_connection_error(error_msg))
                
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
        
        # Show dump and load buttons for physical cards
        if self.is_physical:
            self.dump_btn.pack(pady=(0, 10))
            self.load_btn.pack(pady=(0, 10))
            self.erase_btn.pack(pady=(0, 10))
        
        self.status_var.set("Ready")
        
    def on_connection_error(self, error_msg):
        """Handle connection error"""
        self.status_var.set(f"Connection failed: {error_msg}")
        messagebox.showerror("Connection Error", f"Failed to connect: {error_msg}")
        
    def disconnect(self):
        """Disconnect from memory card"""
        if self.current_reader:
            self.current_reader.close()
            self.current_reader = None
            
        self.current_file_path = None
        self.is_physical = False
        
        # Reset UI
        self.connect_btn.config(text="🔌 Connect", bg='#4CAF50', command=self.connect)
        self.card_info_text.config(state=tk.NORMAL)
        self.card_info_text.delete(1.0, tk.END)
        self.card_info_text.config(state=tk.DISABLED)
        
        # Hide dump button, load button, erase button, and progress bar
        self.dump_btn.pack_forget()
        self.load_btn.pack_forget()
        self.erase_btn.pack_forget()
        self.progress_frame.pack_forget()
        
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
            entries = self.current_reader.get_directory_content(root_cluster)
            
            # Sort entries by name in ascending order
            entries = sorted(entries, key=lambda x: x['name'].lower() if x and x['name'] else '')
            
            # Populate tree
            for entry in entries:
                if entry:  # Skip None entries
                    # Type icon
                    if entry['is_dir']:
                        type_icon = "📁"
                        type_text = "DIR"
                        #if entry['is_hidden']:
                        #    type_text = f"{type_text} [HIDDEN]"
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
                    
                    # Insert into tree
                    item = self.dir_tree.insert('', 'end', text=f"{type_icon} {name}", 
                                              values=(type_text, size_str, entry['modified'], entry['cluster']))
                    
            # Update current directory label
            self.current_directory = root_cluster
            self.current_dir_label.config(text=f"📁 Current Directory: Cluster {root_cluster}")
            
        except Exception as e:
            messagebox.showerror("Directory Error", f"Failed to load directory: {str(e)}")

    def on_tree_double_click(self, event):
        """Handle double-click on the directory tree to navigate into folders"""
        selected_item = self.dir_tree.selection()
        if not selected_item:
            return
            
        item_id = selected_item[0]
        item_values = self.dir_tree.item(item_id)['values']
        
        if not item_values:
            return
            
        # Check if it's a directory
        if item_values[0] == "DIR":
            # Get the cluster number from the values
            cluster_num = item_values[3]  # Cluster column
            
            if cluster_num is not None:
                self.navigate_to_directory(cluster_num)
    
    def navigate_to_directory(self, cluster_num):
        """Navigate to a specific directory cluster"""
        if not self.current_reader:
            messagebox.showwarning("Not Connected", "Please connect to a memory card first.")
            return
            
        try:
            # Store current directory in navigation stack
            if self.current_directory is not None:
                self.navigation_stack.append(self.current_directory)
            
            # Navigate to the new directory using existing method
            entries = self.current_reader.get_directory_content(cluster_num)
            
            if entries:
                # Update current directory
                self.current_directory = cluster_num
                
                # Clear and repopulate the tree
                self.populate_directory_tree(entries)
                
                # Update status and current directory label
                self.status_var.set(f"📁 Navigated to directory cluster {cluster_num}")
                self.current_dir_label.config(text=f"📁 Current Directory: Cluster {cluster_num}")
            else:
                messagebox.showinfo("Empty Directory", f"Directory cluster {cluster_num} is empty or could not be read.")
                
        except Exception as e:
            messagebox.showerror("Navigation Error", f"Failed to navigate to cluster {cluster_num}: {str(e)}")
            self.status_var.set(f"Navigation failed: {str(e)}")
    
    def navigate_back(self):
        """Navigate back to the previous directory"""
        if not self.navigation_stack:
            return
            
        try:
            # Get previous directory from stack
            previous_cluster = self.navigation_stack.pop()
            
            # Navigate back using existing method
            entries = self.current_reader.get_directory_content(previous_cluster)
            
            if entries:
                # Update current directory
                self.current_directory = previous_cluster
                
                # Clear and repopulate the tree
                self.populate_directory_tree(entries)
                
                # Update status and current directory label
                self.status_var.set(f"⬅️ Navigated back to cluster {previous_cluster}")
                self.current_dir_label.config(text=f"📁 Current Directory: Cluster {previous_cluster}")
            else:
                messagebox.showinfo("Navigation Error", f"Could not navigate back to cluster {previous_cluster}")
                
        except Exception as e:
            messagebox.showerror("Navigation Error", f"Failed to navigate back: {str(e)}")
            self.status_var.set(f"Navigation failed: {str(e)}")
    
    def populate_directory_tree(self, entries):
        """Populate the directory tree with entries"""
        # Clear existing items
        for item in self.dir_tree.get_children():
            self.dir_tree.delete(item)
        
        # Sort entries by name in ascending order
        entries = sorted(entries, key=lambda x: x['name'].lower() if x and x['name'] else '')
        
        # Populate tree with new entries
        for entry in entries:
            if entry:
                # Type icon and text
                if entry['is_dir']:
                    type_icon = "📁"
                    type_text = "DIR"
                    #if entry['is_hidden']:
                    #    type_text = f"{type_text} [HIDDEN]"
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
                
                # Name
                name = entry['name']
                
                # Insert into tree
                self.dir_tree.insert('', 'end', text=f"{type_icon} {name}", 
                                   values=(type_text, size_str, entry['modified'], entry['cluster']))

    def dump_physical_card(self):
        """Dump the physical memory card to a .ps2 file"""
        if not self.current_reader or not self.is_physical:
            messagebox.showwarning("Not Connected", "Please connect to a physical memory card first.")
            return
            
        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            title="Save Memory Card Dump",
            defaultextension=".ps2",
            filetypes=[("PS2 Memory Card", "*.ps2"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            self.status_var.set("💾 Starting memory card dump...")
            self.dump_btn.config(state=tk.DISABLED, text="⏳ Dumping...")
            
            # Show progress bar
            self.progress_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            self.progress_bar['value'] = 0
            
            # Run dump in background thread
            def dump_thread():
                try:
                    # Get card specifications
                    specs = self.current_reader.get_card_specs()
                    total_pages = specs['cardsize']
                    
                    with open(file_path, 'wb') as f:
                        # Dump all pages
                        for page_num in range(total_pages):
                            try:
                                cluster_data, ecc = self.current_reader.read_page(page_num)
                                
                                # Write page data
                                f.write(bytes(cluster_data) + bytes(ecc))
                                
                                # Update progress bar
                                progress = ((page_num + 1) / total_pages) * 100
                                self.root.after(0, lambda p=progress: self.update_progress(p, page_num + 1, total_pages))
                                    
                            except Exception as e:
                                print(f"Error reading page {page_num}: {e}")
                                # Continue with next page
                                continue
                    
                    # Success message
                    self.root.after(0, lambda: self.on_dump_success(file_path))
                    
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda: self.on_dump_error(error_msg))
                    
            threading.Thread(target=dump_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Dump Error", f"Failed to start dump: {str(e)}")
            self.status_var.set("Dump failed")
            self.dump_btn.config(state=tk.NORMAL, text="💾 Dump to .ps2 File")

    def load_to_physical_card(self):
        """Load a .ps2 file to the physical memory card"""
        if not self.current_reader or not self.is_physical:
            messagebox.showwarning("Not Connected", "Please connect to a physical memory card first.")
            return
            
        # Ask user for source .ps2 file
        file_path = filedialog.askopenfilename(
            title="Select PS2 Memory Card File to Load",
            filetypes=[("PS2 Memory Card", "*.ps2"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
            
        if not os.path.exists(file_path):
            messagebox.showerror("File Not Found", "The selected file does not exist")
            return
            
        try:
            self.status_var.set("📥 Starting memory card load...")
            self.load_btn.config(state=tk.DISABLED, text="⏳ Loading...")
            self.dump_btn.config(state=tk.DISABLED)  # Disable dump button during load
            
            # Show progress bar
            self.progress_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            self.progress_bar['value'] = 0
            self.progress_label.config(text="Loading memory card from file...")
            
            # Run load in background thread
            def load_thread():
                try:
                    # Create virtual reader for source file
                    virtual_reader = VirtualPs2MemoryCardReader(file_path)
                    virtual_reader.open()
                    
                    # Get card specifications from both readers
                    physical_specs = self.current_reader.get_card_specs()

                    virtual_specs = virtual_reader.get_card_specs()
                    
                    # Check compatibility
                    if (self.current_reader.is_formatted() and (physical_specs['cardsize'] != virtual_specs['cardsize'] or
                        physical_specs['blocksize'] != virtual_specs['blocksize'] or
                        physical_specs['pagesize'] != virtual_specs['pagesize'] or
                        physical_specs['eccsize'] != virtual_specs['eccsize'])):
                        raise ValueError("Memory card sizes don't match! Cannot load file.")
                    
                    total_pages = virtual_specs['cardsize']

                    print("Erasing physical card")
                    self.current_reader.erase_all()

                    sleep(5)

                    print("Loading physical card")
                    # Load all pages
                    for page_num in range(total_pages):
                        try:
                            # Read page from virtual file
                            cluster_data, ecc = virtual_reader.read_page(page_num)
                            
                            # Write page to physical card
                            self.current_reader.write_page(page_num, cluster_data, ecc)
                            
                            # Update progress bar
                            progress = ((page_num + 1) / total_pages) * 100
                            self.root.after(0, lambda p=progress, c=page_num+1, t=total_pages: 
                                          self.update_progress("Importing file to physical card", p, c, t))
                                
                        except Exception as e:
                            print(f"Error processing page {page_num}: {e}")
                            # Continue with next page
                            continue
                    
                    # Close virtual reader
                    virtual_reader.close()
                    
                    # Success message
                    self.root.after(0, lambda: self.on_load_success(file_path))
                    
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda: self.on_load_error(error_msg))
                    
            threading.Thread(target=load_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to start load: {str(e)}")
            self.status_var.set("Load failed")
            self.load_btn.config(state=tk.NORMAL, text="📥 Load from .ps2 File")
            self.dump_btn.config(state=tk.NORMAL)

    def update_progress(self, text, percentage, current, total):
        """Update the progress bar and label"""
        self.progress_bar['value'] = percentage
        self.progress_label.config(text=f"{text}... {current}/{total} pages ({percentage:.1f}%)")
        self.status_var.set(f"💾 Dumping... {percentage:.1f}%")

    def on_dump_success(self, file_path):
        """Handle successful dump completion"""
        self.status_var.set(f"✅ Dump completed: {os.path.basename(file_path)}")
        self.dump_btn.config(state=tk.NORMAL, text="💾 Dump to .ps2 File")
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        # Show success message
        messagebox.showinfo("Dump Complete", 
                          f"Memory card successfully dumped to:\n{file_path}\n\n"
                          f"File size: {os.path.getsize(file_path) / (1024*1024):.1f} MB")

    def on_dump_error(self, error_msg):
        """Handle dump error"""
        self.status_var.set(f"❌ Dump failed: {error_msg}")
        self.dump_btn.config(state=tk.NORMAL, text="💾 Dump to .ps2 File")
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        messagebox.showerror("Dump Error", f"Failed to dump memory card:\n{error_msg}")

    def on_load_success(self, file_path):
        """Handle successful load completion"""
        self.status_var.set(f"✅ Load completed: {os.path.basename(file_path)}")
        self.load_btn.config(state=tk.NORMAL, text="📥 Load from .ps2 File")
        self.dump_btn.config(state=tk.NORMAL)
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        # Show success message
        messagebox.showinfo("Load Complete", 
                          f"Memory card successfully loaded from:\n{file_path}\n\n"
                          f"File size: {os.path.getsize(file_path) / (1024*1024):.1f} MB")

    def on_load_error(self, error_msg):
        """Handle load error"""
        self.status_var.set(f"❌ Load failed: {error_msg}")
        self.load_btn.config(state=tk.NORMAL, text="📥 Load from .ps2 File")
        self.dump_btn.config(state=tk.NORMAL)
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        messagebox.showerror("Load Error", f"Failed to load memory card:\n{error_msg}")

    def erase_physical_card(self):
        """Erase all content from the physical memory card"""
        if not self.current_reader or not self.is_physical:
            messagebox.showerror("Error", "No physical memory card connected")
            return
            
        # Confirmation dialog
        result = messagebox.askyesno("Confirm Erase", 
                                   "⚠️ WARNING: This will permanently erase ALL data on the memory card!\n\n"
                                   "This action cannot be undone. Are you sure you want to continue?")
        if not result:
            return
            
        # Disable buttons and show progress
        self.erase_btn.config(state=tk.DISABLED, text="🗑️ Erasing...")
        self.dump_btn.config(state=tk.DISABLED)
        self.load_btn.config(state=tk.DISABLED)
        self.status_var.set("🗑️ Erasing memory card...")
        
        # Show progress bar
        self.progress_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Erasing memory card... 0%")
        
        def erase_thread():
            try:
                # Get card specs
                specs = self.current_reader.get_card_specs()
                total_pages = specs['cardsize']
                
                # Erase all pages
                for page_num in range(total_pages):
                    self.current_reader.erase_page(page_num)
                    
                    # Update progress
                    progress = ((page_num + 1) / total_pages) * 100
                    self.root.after(0, lambda p=progress, c=page_num+1, t=total_pages: 
                                  self.update_erase_progress("Erasing memory card", p, c, t))
                
                # Success
                self.root.after(0, self.on_erase_success)
                
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self.on_erase_error(error_msg))
                
        threading.Thread(target=erase_thread, daemon=True).start()

    def update_erase_progress(self, percentage, current, total):
        """Update the erase progress bar and label"""
        self.progress_bar['value'] = percentage
        self.progress_label.config(text=f"Erasing memory card... {current}/{total} pages ({percentage:.1f}%)")
        self.status_var.set(f"🗑️ Erasing... {percentage:.1f}%")

    def on_erase_success(self):
        """Handle successful erase completion"""
        self.status_var.set("✅ Erase completed")
        self.erase_btn.config(state=tk.NORMAL, text="🗑️ Erase All")
        self.dump_btn.config(state=tk.NORMAL)
        self.load_btn.config(state=tk.NORMAL)
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        # Reload card info and directory
        self.load_card_info()
        self.load_directory_listing()
        
        # Show success message
        messagebox.showinfo("Erase Complete", "Memory card has been completely erased!")

    def on_erase_error(self, error_msg):
        """Handle erase error"""
        self.status_var.set(f"❌ Erase failed: {error_msg}")
        self.erase_btn.config(state=tk.NORMAL, text="🗑️ Erase All")
        self.dump_btn.config(state=tk.NORMAL)
        self.load_btn.config(state=tk.NORMAL)
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        messagebox.showerror("Erase Error", f"Failed to erase memory card:\n{error_msg}")

def main():
    root = tk.Tk()
    app = Ps2MemoryCardGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
