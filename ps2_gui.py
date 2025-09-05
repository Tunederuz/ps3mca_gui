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
        # PS2-inspired dark mode theme
        self.colors = {
            'bg_primary': '#0a0a0a',           # Deep black (PS2 console color)
            'bg_secondary': '#1a1a1a',         # Dark charcoal (PS2 surface)
            'bg_tertiary': '#2a2a2a',          # Medium dark (PS2 accent areas)
            'bg_elevated': '#333333',          # Elevated surfaces
            'border': '#404040',               # Subtle borders
            'border_accent': '#0066cc',        # PS2 signature blue borders
            'accent_blue': '#0066cc',          # PS2 signature blue
            'accent_blue_bright': '#0088ff',   # Bright PS2 blue
            'accent_green': '#00cc44',         # PS2 success green
            'accent_orange': '#ff6600',        # PS2 warning orange
            'accent_red': '#cc0000',           # PS2 error red
            'text_primary': '#ffffff',         # Pure white text
            'text_secondary': '#cccccc',       # Light grey text
            'text_muted': '#999999',           # Muted grey text
            'text_disabled': '#666666',        # Disabled text
            'text_accent': '#0088ff',          # PS2 blue text
            'hover': '#333333',                # Hover states
            'selected': '#0066cc',             # PS2 blue selection
            'ps2_gradient_start': '#001122',   # PS2 gradient start
            'ps2_gradient_end': '#003366'      # PS2 gradient end
        }
        
        self.root.title("🎮 PS2 Memory Card Manager")
        self.root.geometry("1200x800")
        self.root.configure(bg=self.colors['bg_primary'])
        self.root.minsize(1000, 700)
        
        # Enhanced style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure sleek dark theme styles
        self.style.configure('Title.TLabel', 
                           font=('Segoe UI', 22, 'bold'), 
                           foreground=self.colors['text_primary'],
                           background=self.colors['bg_primary'])
        self.style.configure('Header.TLabel', 
                           font=('Segoe UI', 12, 'bold'), 
                           foreground=self.colors['text_primary'],
                           background=self.colors['bg_secondary'])
        self.style.configure('Info.TLabel', 
                           font=('Segoe UI', 10), 
                           foreground=self.colors['text_secondary'],
                           background=self.colors['bg_secondary'])
        
        # Configure PS2 progress bar style
        self.style.configure('PS2.Horizontal.TProgressbar',
                           background=self.colors['accent_blue'],
                           troughcolor=self.colors['bg_tertiary'],
                           borderwidth=0,
                           lightcolor=self.colors['accent_blue_bright'],
                           darkcolor=self.colors['accent_blue'])
        
        # Variables
        self.current_reader = None
        self.current_file_path = None
        self.is_physical = False
        self.conn_var = tk.StringVar(value="virtual")
        self.file_path_var = tk.StringVar()
        
        self.setup_menu_bar()
        self.setup_ui()
        
    def setup_menu_bar(self):
        """Setup the application menu bar"""
        menubar = tk.Menu(self.root, bg=self.colors['bg_secondary'], 
                         fg=self.colors['text_primary'],
                         activebackground=self.colors['accent_blue'],
                         activeforeground=self.colors['text_primary'])
        self.root.config(menu=menubar)
        
        # File menu
        self.file_menu = tk.Menu(menubar, tearoff=0, 
                           bg=self.colors['bg_secondary'], 
                           fg=self.colors['text_primary'],
                           activebackground=self.colors['accent_blue'],
                           activeforeground=self.colors['text_primary'])
        menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Initialize menu state (will add connection options)
        self.update_menu_state()
        
        # Tools menu
        self.tools_menu = tk.Menu(menubar, tearoff=0,
                            bg=self.colors['bg_secondary'], 
                            fg=self.colors['text_primary'],
                            activebackground=self.colors['accent_blue'],
                            activeforeground=self.colors['text_primary'])
        menubar.add_cascade(label="Tools", menu=self.tools_menu)
        self.tools_menu.add_command(label="📊 Card Information", command=self.show_card_info_popup)
        
        # Initialize tools menu state
        self.update_tools_menu_state()
        
    def setup_ui(self):
        """Setup the main UI components"""
        # Main frame with sleek styling
        main_frame = tk.Frame(self.root, bg=self.colors['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title with sleek styling
        title_frame = tk.Frame(main_frame, bg=self.colors['bg_primary'])
        title_frame.pack(fill=tk.X, pady=(0, 25))
        
        title_label = tk.Label(title_frame, text="🎮 PS2 Memory Card Manager", 
                              font=('Segoe UI', 28, 'bold'), 
                              bg=self.colors['bg_primary'], 
                              fg=self.colors['text_primary'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="PlayStation 2 Memory Card Management Tool", 
                                 font=('Segoe UI', 12), 
                                 bg=self.colors['bg_primary'], 
                                 fg=self.colors['text_accent'])
        subtitle_label.pack(pady=(8, 0))
        
        # Directory listing frame (with integrated navigation)
        self.setup_directory_frame(main_frame)
        
        # Progress bar frame
        self.setup_progress_frame(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
        
    def setup_progress_frame(self, parent):
        """Setup the progress bar frame"""
        # Progress bar (initially hidden)
        self.progress_frame = tk.Frame(parent, bg=self.colors['bg_primary'])
        self.progress_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        self.progress_frame.pack_forget()  # Initially hidden
        
        self.progress_label = tk.Label(self.progress_frame, text="Dumping memory card...", 
                                      bg=self.colors['bg_primary'], 
                                      fg=self.colors['text_primary'], 
                                      font=('Segoe UI', 10))
        self.progress_label.pack(anchor=tk.W)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, 
                                          mode='determinate', 
                                          length=400,
                                          style='PS2.Horizontal.TProgressbar')
        self.progress_bar.pack(fill=tk.X, pady=(8, 0))
        
    def setup_directory_frame(self, parent):
        """Setup the directory listing frame with integrated navigation"""
        dir_frame = tk.LabelFrame(parent, text="📁 Directory Contents", 
                                 bg=self.colors['bg_secondary'], 
                                 fg=self.colors['text_primary'],
                                 font=('Segoe UI', 13, 'bold'),
                                 relief=tk.FLAT,
                                 bd=2,
                                 highlightbackground=self.colors['border_accent'],
                                 highlightthickness=2)
        dir_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Navigation controls frame
        nav_controls = tk.Frame(dir_frame, bg=self.colors['bg_secondary'])
        nav_controls.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        # Back button
        self.back_btn = tk.Button(nav_controls, text="⬅️ Back", command=self.navigate_back,
                                 bg=self.colors['accent_blue'], 
                                 fg=self.colors['text_primary'], 
                                 font=('Segoe UI', 11, 'bold'),
                                 relief=tk.FLAT, 
                                 padx=20, 
                                 pady=6,
                                 activebackground=self.colors['accent_blue_bright'],
                                 activeforeground=self.colors['text_primary'])
        self.back_btn.pack(side=tk.LEFT, padx=(0, 18))
        
        # Current directory label
        self.current_dir_label = tk.Label(nav_controls, text="📁 Current Directory: /", 
                                         bg=self.colors['bg_secondary'], 
                                         fg=self.colors['text_accent'], 
                                         font=('Segoe UI', 11, 'bold'))
        self.current_dir_label.pack(side=tk.LEFT)
        
        # Directory tree with custom styling (reduced height)
        self.dir_tree = ttk.Treeview(dir_frame, columns=('Type', 'Size', 'Modified', 'Cluster'), 
                                    show='tree headings', height=10)
        
        # Configure PS2 treeview styling
        self.style.configure('Treeview', 
                           background=self.colors['bg_tertiary'],
                           foreground=self.colors['text_primary'],
                           fieldbackground=self.colors['bg_tertiary'],
                           font=('Segoe UI', 10))
        self.style.configure('Treeview.Heading',
                           background=self.colors['bg_secondary'],
                           foreground=self.colors['text_accent'],
                           font=('Segoe UI', 11, 'bold'))
        self.style.map('Treeview',
                      background=[('selected', self.colors['accent_blue'])],
                      foreground=[('selected', self.colors['text_primary'])])
        
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
        
        self.dir_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 0), pady=12)
        dir_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=12)
        
        # Initially empty (no items to show)
        
        # Bind double-click event for folder navigation
        self.dir_tree.bind('<Double-1>', self.on_tree_double_click)
        
        # Navigation state variables
        self.navigation_stack = []
        self.current_directory = None
        
    def setup_status_bar(self, parent):
        """Setup the status bar"""
        self.status_var = tk.StringVar(value="Ready to connect")
        status_bar = tk.Label(parent, textvariable=self.status_var, 
                             relief=tk.FLAT, 
                             anchor=tk.W, 
                             bg=self.colors['bg_secondary'], 
                             fg=self.colors['text_secondary'],
                             font=('Segoe UI', 11),
                             padx=20,
                             pady=10)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(15, 0))
        
    def show_card_info_popup(self):
        """Show card information in a popup window"""
        if not self.current_reader:
            messagebox.showwarning("No Connection", "Please connect to a memory card first.")
            return
            
        # Create popup window
        popup = tk.Toplevel(self.root)
        popup.title("📊 Memory Card Information")
        popup.geometry("600x500")
        popup.configure(bg=self.colors['bg_primary'])
        popup.resizable(True, True)
        
        # Center the popup
        popup.transient(self.root)
        popup.grab_set()
        
        # Main frame
        main_frame = tk.Frame(popup, bg=self.colors['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="📊 PlayStation 2 Memory Card Information", 
                              font=('Segoe UI', 20, 'bold'), 
                              bg=self.colors['bg_primary'], 
                              fg=self.colors['text_primary'])
        title_label.pack(pady=(0, 20))
        
        # Card info text widget
        card_info_text = scrolledtext.ScrolledText(main_frame, 
                                                  bg=self.colors['bg_tertiary'], 
                                                  fg=self.colors['text_primary'],
                                                  font=('Consolas', 10),
                                                  relief=tk.FLAT,
                                                  bd=1,
                                                  insertbackground=self.colors['text_primary'],
                                                  selectbackground=self.colors['accent_blue'],
                                                  selectforeground=self.colors['text_primary'])
        card_info_text.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Load card information
        try:
            superblock = self.current_reader.get_superblock_info()
            
            # Calculate total size
            total_size_mb = (superblock['clusters_per_card'] * superblock['pages_per_cluster'] * 528) / (1024*1024)
            
            info_text = f"""🎮 PS2 Memory Card - {total_size_mb:.1f} MB
{'─' * 60}

📊 SPECIFICATIONS
  Size: {total_size_mb:.1f} MB ({superblock['clusters_per_card']:,} clusters)
  Format: {superblock['magic']} v{superblock['version']}
  Page Size: {superblock['page_len']} bytes
  Block Size: {superblock['pages_per_block']} pages

🔧 FEATURES
  ECC Support: {'✓' if self.current_reader.has_ecc_support() else '✗'}
  Bad Block Management: {'✓' if self.current_reader.has_bad_blocks() else '✗'}
  Erase Mode: {'Zero' if self.current_reader.erased_blocks_are_zeroes() else 'One'}

📁 STRUCTURE
  Root Directory: Cluster {superblock['rootdir_cluster']}
  Allocation Range: {superblock['alloc_offset']} - {superblock['alloc_end']}
  Backup Blocks: {superblock['backup_block1']}, {superblock['backup_block2']}
"""
            
            card_info_text.insert(1.0, info_text)
            card_info_text.config(state=tk.DISABLED)
            
        except Exception as e:
            card_info_text.insert(1.0, f"Error loading card info: {str(e)}")
            card_info_text.config(state=tk.DISABLED)
        
        # Close button
        close_btn = tk.Button(main_frame, text="Close", command=popup.destroy,
                             bg=self.colors['accent_blue'], 
                             fg=self.colors['text_primary'], 
                             font=('Segoe UI', 12, 'bold'),
                             relief=tk.FLAT, 
                             padx=35, 
                             pady=10,
                             activebackground=self.colors['accent_blue_bright'],
                             activeforeground=self.colors['text_primary'])
        close_btn.pack()
        
    def update_menu_state(self):
        """Update menu items based on connection state"""
        # Clear existing disconnect/close commands if they exist
        try:
            self.file_menu.delete("🔌 Disconnect")
        except:
            pass
        try:
            self.file_menu.delete("📁 Close Memory Card File")
        except:
            pass
            
        # Clear existing connection commands if they exist
        try:
            self.file_menu.delete("📁 Load Memory Card File")
            self.file_menu.delete("🔌 Connect to Physical Memory Card")
        except:
            pass
            
        if self.current_reader:
            # Connected state - show disconnect option
            if self.is_physical:
                # Physical card connected - show disconnect
                self.file_menu.insert_command(0, label="🔌 Disconnect", command=self.disconnect)
            else:
                # Virtual card loaded - show close option
                self.file_menu.insert_command(0, label="📁 Close Memory Card File", command=self.disconnect)
            # Hide connection options when connected
        else:
            # Not connected - show connection options
            self.file_menu.insert_command(0, label="📁 Load Memory Card File", command=self.load_memory_card_file)
            self.file_menu.insert_command(1, label="🔌 Connect to Physical Memory Card", command=self.connect_to_physical_card)
        
    def update_tools_menu_state(self):
        """Update tools menu items based on connection state"""
        # Clear existing physical card tools if they exist
        try:
            self.tools_menu.delete("💾 Dump to .ps2 File")
        except:
            pass
        try:
            self.tools_menu.delete("📥 Load from .ps2 File")
        except:
            pass
        try:
            self.tools_menu.delete("🧹 Erase All")
        except:
            pass
        try:
            self.tools_menu.delete("separator")
        except:
            pass
            
        # Add physical card tools only if physical card is connected
        if self.current_reader and self.is_physical:
            self.tools_menu.add_separator()
            self.tools_menu.add_command(label="💾 Dump to .ps2 File", command=self.dump_physical_card)
            self.tools_menu.add_command(label="📥 Load from .ps2 File", command=self.load_to_physical_card)
            self.tools_menu.add_command(label="🧹 Erase All", command=self.erase_physical_card)
        
    def load_memory_card_file(self):
        """Load a memory card file from File menu"""
        self.conn_var.set("virtual")
        self.on_connection_change()
        
        # Browse for file and connect if selected
        file_path = filedialog.askopenfilename(
            title="Select PS2 Memory Card File",
            filetypes=[("PS2 Memory Card", "*.ps2"), ("All Files", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.current_file_path = file_path
            # Automatically connect to the selected file
            self.connect()
        
    def connect_to_physical_card(self):
        """Connect to physical memory card from File menu"""
        self.conn_var.set("physical")
        self.on_connection_change()
        self.connect()
        
    def on_connection_change(self):
        """Handle connection type change"""
        if self.conn_var.get() == "physical":
            self.current_file_path = None
            
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
        self.status_var.set("Connected successfully! Loading directory...")
        
        # Load directory listing
        self.load_directory_listing()
        
        # Update menu state
        self.update_menu_state()
        self.update_tools_menu_state()
        
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
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        # Clear all items from the tree
        for item in self.dir_tree.get_children():
            self.dir_tree.delete(item)
            
        # Update menu state
        self.update_menu_state()
        self.update_tools_menu_state()
            
        self.status_var.set("Disconnected")
        
            
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
            
            # Show progress bar
            self.progress_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
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
                                self.root.after(0, lambda p=progress: self.update_progress("Dumping memory card", p, page_num + 1, total_pages))
                                    
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
            
            # Show progress bar
            self.progress_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
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

    def update_progress(self, text, percentage, current, total):
        """Update the progress bar and label"""
        self.progress_bar['value'] = percentage
        self.progress_label.config(text=f"{text}... {current}/{total} pages ({percentage:.1f}%)")
        self.status_var.set(f"{text}... {percentage:.1f}%")

    def on_dump_success(self, file_path):
        """Handle successful dump completion"""
        self.status_var.set(f"✅ Dump completed: {os.path.basename(file_path)}")
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        # Show success message
        messagebox.showinfo("Dump Complete", 
                          f"Memory card successfully dumped to:\n{file_path}\n\n"
                          f"File size: {os.path.getsize(file_path) / (1024*1024):.1f} MB")

    def on_dump_error(self, error_msg):
        """Handle dump error"""
        self.status_var.set(f"❌ Dump failed: {error_msg}")
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        messagebox.showerror("Dump Error", f"Failed to dump memory card:\n{error_msg}")

    def on_load_success(self, file_path):
        """Handle successful load completion"""
        self.status_var.set(f"✅ Load completed: {os.path.basename(file_path)}")
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        # Show success message
        messagebox.showinfo("Load Complete", 
                          f"Memory card successfully loaded from:\n{file_path}\n\n"
                          f"File size: {os.path.getsize(file_path) / (1024*1024):.1f} MB")

    def on_load_error(self, error_msg):
        """Handle load error"""
        self.status_var.set(f"❌ Load failed: {error_msg}")
        
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
            
        # Show progress
        self.status_var.set("🧹 Erasing memory card...")
        
        # Show progress bar
        self.progress_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
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
                    self.update_erase_progress(p, c, t))
                
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
        self.status_var.set(f"🧹 Erasing... {percentage:.1f}%")

    def on_erase_success(self):
        """Handle successful erase completion"""
        self.status_var.set("✅ Erase completed")
        
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
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        messagebox.showerror("Erase Error", f"Failed to erase memory card:\n{error_msg}")

def main():
    root = tk.Tk()
    app = Ps2MemoryCardGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
