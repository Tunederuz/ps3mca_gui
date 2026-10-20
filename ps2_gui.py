#!/usr/bin/env python3
"""
PS2 Memory Card Reader GUI
A modern interface for reading both physical and virtual PS2 memory cards
"""

from time import sleep
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
import threading
import os
import native_dialogs
import ps2_format
import ps2_saves
from ps2_card_writer import NotEnoughSpaceError, SaveExistsError
from ps2_physical_writer import PhysicalCardSession, PhysicalWriteError
from memory_card_reader import PhysicalPs2MemoryCardReader, VirtualPs2MemoryCardReader, PARENT_DIRECTORY_LABEL

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
            'ps2_gradient_end': '#003366',     # PS2 gradient end
            'row_alt': '#242424',              # Alternate row background
            'type_dir': '#8cc4ff',             # Directory rows
            'type_ps1': '#ffb070',             # PS1 save rows
            'type_pocketstation': '#c9a0ff',   # PocketStation rows
            'ps_triangle': '#3fc1a5',          # Controller face button colors
            'ps_circle': '#ff5a5f',
            'ps_cross': '#7ab8ff',
            'ps_square': '#e58fc2'
        }

        self.root.title("PS2 Memory Card Manager")
        self.root.geometry("1200x800")
        self.root.configure(bg=self.colors['bg_primary'])
        self.root.minsize(1000, 700)

        # Segoe UI and Consolas only exist on Windows, fall back to common Linux fonts
        families = set(tkfont.families(self.root))
        self.ui_font = next((f for f in ('Segoe UI', 'Inter', 'Cantarell', 'Noto Sans', 'DejaVu Sans')
                             if f in families), 'Helvetica')
        self.mono_font = next((f for f in ('Consolas', 'JetBrains Mono', 'DejaVu Sans Mono', 'Liberation Mono')
                               if f in families), 'Courier')

        # Enhanced style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Dark scrollbar instead of the light grey clam default
        self.style.configure('PS2.Vertical.TScrollbar',
                           background=self.colors['bg_elevated'],
                           troughcolor=self.colors['bg_secondary'],
                           bordercolor=self.colors['bg_secondary'],
                           lightcolor=self.colors['bg_elevated'],
                           darkcolor=self.colors['bg_elevated'],
                           arrowcolor=self.colors['text_muted'],
                           gripcount=0)
        self.style.map('PS2.Vertical.TScrollbar',
                      background=[('pressed', self.colors['accent_blue_bright']),
                                  ('active', self.colors['accent_blue'])],
                      arrowcolor=[('active', self.colors['text_primary'])])

        # Configure sleek dark theme styles
        self.style.configure('Title.TLabel', 
                           font=(self.ui_font, 22, 'bold'), 
                           foreground=self.colors['text_primary'],
                           background=self.colors['bg_primary'])
        self.style.configure('Header.TLabel', 
                           font=(self.ui_font, 12, 'bold'), 
                           foreground=self.colors['text_primary'],
                           background=self.colors['bg_secondary'])
        self.style.configure('Info.TLabel', 
                           font=(self.ui_font, 10), 
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
        
        # Dictionary to store hidden data for tree items
        self.tree_item_data = {}
        
        # Set while a background task talks to the card
        self.busy = False
        
        self.setup_menu_bar()
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
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
        self.file_menu.add_command(label="New Memory Card File...", command=self.new_memory_card_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.on_close)
        
        # Initialize menu state (will add connection options)
        self.update_menu_state()
        
        # Tools menu
        self.tools_menu = tk.Menu(menubar, tearoff=0,
                            bg=self.colors['bg_secondary'], 
                            fg=self.colors['text_primary'],
                            activebackground=self.colors['accent_blue'],
                            activeforeground=self.colors['text_primary'])
        menubar.add_cascade(label="Tools", menu=self.tools_menu)
        
        # Initialize tools menu state
        self.update_tools_menu_state()
        
    def setup_ui(self):
        """Setup the main UI components"""
        # Panels are packed straight into a canvas so its gradient shows between them
        self.bg_canvas = tk.Canvas(self.root, bg=self.colors['bg_primary'],
                                   highlightthickness=0, bd=0)
        self.bg_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Compact header drawn on the canvas: title on the left, connection on the right
        self.draw_face_buttons(24, 34)
        self.bg_canvas.create_text(116, 34, anchor=tk.W, text="PS2 Memory Card Manager",
                                   font=(self.ui_font, 18, 'bold'),
                                   fill=self.colors['text_primary'], tags='header')
        self.connection_text = self.bg_canvas.create_text(0, 34, anchor=tk.E, text="",
                                                          font=(self.ui_font, 11, 'bold'),
                                                          tags='header')
        self.bg_canvas.bind('<Configure>', self.draw_background)
        
        # Directory listing frame (with integrated navigation)
        self.setup_directory_frame(self.bg_canvas)
        
        # Progress bar frame
        self.setup_progress_frame(self.bg_canvas)
        
        # Status bar
        self.setup_status_bar(self.bg_canvas)
        
        self.update_connection_badge()
        
    def draw_face_buttons(self, x, y):
        """Draw the four controller shapes as a small logo, centered on y"""
        canvas = self.bg_canvas
        size, gap, width = 16, 6, 2.5
        half = size / 2
        top, bottom = y - half, y + half
        
        canvas.create_polygon(x + half, top, x + size, bottom, x, bottom, outline=self.colors['ps_triangle'],
                              fill='', width=width, joinstyle=tk.ROUND, tags='header')
        x += size + gap
        canvas.create_oval(x, top, x + size, bottom, outline=self.colors['ps_circle'], width=width, tags='header')
        x += size + gap
        canvas.create_line(x, top, x + size, bottom, fill=self.colors['ps_cross'], width=width,
                           capstyle=tk.ROUND, tags='header')
        canvas.create_line(x, bottom, x + size, top, fill=self.colors['ps_cross'], width=width,
                           capstyle=tk.ROUND, tags='header')
        x += size + gap
        canvas.create_rectangle(x, top, x + size, bottom, outline=self.colors['ps_square'], width=width,
                                tags='header')
        
    @staticmethod
    def blend_colors(start, end, ratio):
        """Linear blend between two #rrggbb colors"""
        a = [int(start[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(end[i:i + 2], 16) for i in (1, 3, 5)]
        return '#' + ''.join(f"{round(x + (y - x) * ratio):02x}" for x, y in zip(a, b))
        
    def draw_background(self, event):
        """Redraw the PS2 browser style gradient to fit the window"""
        canvas = self.bg_canvas
        canvas.delete('gradient')
        top = self.colors['ps2_gradient_end']
        middle = self.colors['ps2_gradient_start']
        bottom = self.colors['bg_primary']
        band = 4
        for y in range(0, event.height, band):
            ratio = y / max(event.height - 1, 1)
            if ratio < 0.5:
                color = self.blend_colors(top, middle, ratio * 2)
            else:
                color = self.blend_colors(middle, bottom, (ratio - 0.5) * 2)
            canvas.create_rectangle(0, y, event.width, y + band, fill=color, outline='',
                                    tags='gradient')
        canvas.tag_lower('gradient')
        canvas.coords(self.connection_text, event.width - 24, 34)
        
    def update_connection_badge(self):
        """Show what is currently loaded in the header"""
        if not self.current_reader:
            text, color = "No memory card loaded", self.colors['text_muted']
        elif self.is_physical:
            text, color = "Physical card  ·  PS3 Memory Card Adaptor", self.colors['accent_green']
        else:
            text = f"Virtual card  ·  {os.path.basename(self.current_file_path or '')}"
            color = self.colors['accent_green']
        self.bg_canvas.itemconfig(self.connection_text, text=text, fill=color)
        
    def setup_progress_frame(self, parent):
        """Setup the progress bar frame"""
        # Progress bar (initially hidden)
        self.progress_frame = tk.Frame(parent, bg=self.colors['bg_secondary'],
                                       padx=20, pady=12)
        
        self.progress_label = tk.Label(self.progress_frame, text="Dumping memory card...", 
                                      bg=self.colors['bg_secondary'], 
                                      fg=self.colors['text_primary'], 
                                      font=(self.ui_font, 10))
        self.progress_label.pack(anchor=tk.W)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, 
                                          mode='determinate', 
                                          length=400,
                                          style='PS2.Horizontal.TProgressbar')
        self.progress_bar.pack(fill=tk.X, pady=(8, 0))
        
    def show_progress(self):
        """Show the progress bar below the directory listing"""
        self.progress_frame.pack(fill=tk.X, padx=24, pady=(0, 12))
        
    def setup_directory_frame(self, parent):
        """Setup the directory listing frame with integrated navigation"""
        dir_frame = tk.Frame(parent, bg=self.colors['bg_secondary'],
                             highlightbackground=self.colors['border_accent'],
                             highlightthickness=1)
        dir_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(68, 12))
        
        # Navigation controls frame
        nav_controls = tk.Frame(dir_frame, bg=self.colors['bg_secondary'])
        nav_controls.pack(fill=tk.X, padx=16, pady=(14, 10))
        
        # Back button
        self.back_btn = tk.Button(nav_controls, text="Back", command=self.navigate_back,
                                 bg=self.colors['accent_blue'], 
                                 fg=self.colors['text_primary'], 
                                 font=(self.ui_font, 10, 'bold'),
                                 relief=tk.FLAT, 
                                 bd=0,
                                 highlightthickness=0,
                                 padx=16, 
                                 pady=5,
                                 cursor='hand2',
                                 activebackground=self.colors['accent_blue_bright'],
                                 activeforeground=self.colors['text_primary'],
                                 disabledforeground=self.colors['text_disabled'])
        self.back_btn.pack(side=tk.LEFT, padx=(0, 14))
        
        # Breadcrumb of the current path
        self.current_dir_label = tk.Label(nav_controls, text="/", 
                                         bg=self.colors['bg_secondary'], 
                                         fg=self.colors['text_accent'], 
                                         font=(self.ui_font, 11, 'bold'))
        self.current_dir_label.pack(side=tk.LEFT)
        
        # Card actions on the right, rebuilt when the connection changes
        self.toolbar = tk.Frame(nav_controls, bg=self.colors['bg_secondary'])
        self.toolbar.pack(side=tk.RIGHT)
        self.update_toolbar()
        
        tree_container = tk.Frame(dir_frame, bg=self.colors['bg_secondary'])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
        
        self.dir_tree = ttk.Treeview(tree_container, columns=('Type', 'Size', 'Created', 'Modified'), 
                                    show='tree headings', height=10)
        
        # Configure PS2 treeview styling
        self.style.configure('Treeview', 
                           background=self.colors['bg_tertiary'],
                           foreground=self.colors['text_primary'],
                           fieldbackground=self.colors['bg_tertiary'],
                           bordercolor=self.colors['bg_secondary'],
                           borderwidth=0,
                           rowheight=28,
                           font=(self.ui_font, 10))
        self.style.configure('Treeview.Heading',
                           background=self.colors['bg_elevated'],
                           foreground=self.colors['text_accent'],
                           bordercolor=self.colors['bg_secondary'],
                           lightcolor=self.colors['bg_elevated'],
                           darkcolor=self.colors['bg_elevated'],
                           relief=tk.FLAT,
                           padding=(8, 6),
                           font=(self.ui_font, 10, 'bold'))
        # Drop the clam field border, which draws a light frame around the tree
        self.style.layout('Treeview', [('Treeview.treearea', {'sticky': 'nswe'})])
        self.style.map('Treeview.Heading',
                      background=[('active', self.colors['border'])])
        self.style.map('Treeview',
                      background=[('selected', self.colors['accent_blue'])],
                      foreground=[('selected', self.colors['text_primary'])])
        
        # Zebra rows and per-type text colors
        self.dir_tree.tag_configure('odd', background=self.colors['row_alt'])
        self.dir_tree.tag_configure('dir', foreground=self.colors['type_dir'])
        self.dir_tree.tag_configure('ps1', foreground=self.colors['type_ps1'])
        self.dir_tree.tag_configure('pocketstation', foreground=self.colors['type_pocketstation'])
        self.dir_tree.tag_configure('parent', foreground=self.colors['text_muted'])
        
        # Configure columns
        self.dir_tree.heading('#0', text='Name', anchor=tk.W)
        self.dir_tree.heading('Type', text='Type', anchor=tk.CENTER)
        self.dir_tree.heading('Size', text='Size', anchor=tk.E)
        self.dir_tree.heading('Created', text='Created', anchor=tk.CENTER)
        self.dir_tree.heading('Modified', text='Modified', anchor=tk.CENTER)
        
        self.dir_tree.column('#0', width=280)
        self.dir_tree.column('Type', width=80, anchor=tk.CENTER, stretch=False)
        self.dir_tree.column('Size', width=110, anchor=tk.E, stretch=False)
        self.dir_tree.column('Created', width=170, anchor=tk.CENTER)
        self.dir_tree.column('Modified', width=170, anchor=tk.CENTER)
        
        # Scrollbar
        dir_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.dir_tree.yview,
                                      style='PS2.Vertical.TScrollbar')
        self.dir_tree.configure(yscrollcommand=dir_scrollbar.set)
        
        self.dir_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dir_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Hint shown over the tree when there is nothing to list
        self.empty_label = tk.Label(self.dir_tree, bg=self.colors['bg_tertiary'],
                                    fg=self.colors['text_muted'], font=(self.ui_font, 11),
                                    justify=tk.CENTER)
        
        # Open folders/files with double-click or Enter, go back with Backspace
        self.dir_tree.bind('<Double-1>', self.on_tree_double_click)
        self.dir_tree.bind('<Return>', self.on_tree_double_click)
        self.dir_tree.bind('<BackSpace>', lambda event: self.navigate_back())
        
        # Save actions on right-click, Delete key removes the selected save
        self.save_menu = tk.Menu(self.root, tearoff=0,
                                 bg=self.colors['bg_secondary'],
                                 fg=self.colors['text_primary'],
                                 activebackground=self.colors['accent_blue'],
                                 activeforeground=self.colors['text_primary'])
        self.dir_tree.bind('<Button-3>', self.show_save_menu)
        self.dir_tree.bind('<Delete>', lambda event: self.delete_selected_save())
        
        # Navigation state variables
        self.navigation_stack = []
        self.path_names = []
        self.current_directory = None
        
        self.update_navigation_state()
        
    def selected_save_name(self):
        """Name of the save folder selected at the root of the card, or None"""
        if not self.current_reader or self.navigation_stack:
            return None
        selection = self.dir_tree.selection()
        entry = self.tree_item_data.get(selection[0]) if selection else None
        if not entry or not entry['is_dir'] or entry['name'] == PARENT_DIRECTORY_LABEL:
            return None
        return entry['name']
        
    def show_save_menu(self, event):
        """Right-click menu for the save folder under the cursor"""
        if self.busy:
            return
        item = self.dir_tree.identify_row(event.y)
        if not item:
            return
        self.dir_tree.selection_set(item)
        self.dir_tree.focus(item)
        if not self.selected_save_name():
            return
        
        self.save_menu.delete(0, tk.END)
        self.save_menu.add_command(label="Export as .psu...", command=self.export_selected_save)
        self.save_menu.add_command(label="Extract to Folder...", command=self.extract_selected_save)
        if self.can_modify_card():
            self.save_menu.add_separator()
            self.save_menu.add_command(label="Delete Save", command=self.delete_selected_save)
        self.save_menu.tk_popup(event.x_root, event.y_root)
        
    def refresh_card(self):
        """Reload the listing and free space after the card content changed"""
        self.current_reader.clear_superblock_cache()
        self.load_directory_listing()
        self.update_free_space()
        
    def select_root_entry(self, name):
        for item, entry in self.tree_item_data.items():
            if entry['name'] == name:
                self.dir_tree.selection_set(item)
                self.dir_tree.focus(item)
                self.dir_tree.see(item)
                return
        
    def export_selected_save(self):
        """Export the selected save folder as a .psu file"""
        if self.busy:
            return
        name = self.selected_save_name()
        if not name:
            messagebox.showinfo("Export Save", "Select a save folder at the root of the card first.")
            return
        path = native_dialogs.asksaveasfilename(
            parent=self.root,
            title="Export Save",
            initialfile=f"{name}.psu",
            defaultextension=".psu",
            filetypes=[("PS2 Save (EMS / uLaunchELF)", "*.psu"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            ps2_saves.save_to_psu(ps2_saves.read_save(self.current_reader, name), path)
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export {name}:\n{e}")
            return
        self.status_var.set(f"Exported {name} to {os.path.basename(path)}")
        
    def extract_selected_save(self):
        """Copy the files of the selected save into a folder on disk"""
        if self.busy:
            return
        name = self.selected_save_name()
        if not name:
            return
        parent_folder = native_dialogs.askdirectory(parent=self.root, title="Extract Save To")
        if not parent_folder:
            return
        try:
            folder = ps2_saves.extract_to_folder(ps2_saves.read_save(self.current_reader, name), parent_folder)
        except Exception as e:
            messagebox.showerror("Extract Failed", f"Could not extract {name}:\n{e}")
            return
        self.status_var.set(f"Extracted {name} to {folder}")
        
    def can_modify_card(self):
        """Saves can be added or deleted: writable .ps2 files and physical cards"""
        return bool(self.current_reader) and (self.is_physical or self.current_reader.supports_writing())
        
    def save_names_on_card(self):
        root = self.current_reader.get_root_directory_cluster()
        return {entry['name'] for entry in self.current_reader.get_directory_content(root) if entry['is_dir']}
        
    def import_save(self):
        """Add a save from a .psu file to the card"""
        if self.busy or not self.can_modify_card():
            return
        path = native_dialogs.askopenfilename(
            parent=self.root,
            title="Import Save",
            filetypes=[("PS2 Save (EMS / uLaunchELF)", "*.psu"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            save = ps2_saves.load_psu(path)
        except Exception as e:
            messagebox.showerror("Import Failed", f"Could not read {os.path.basename(path)}:\n{e}")
            return
        
        replace = save.name in self.save_names_on_card()
        if replace and not messagebox.askyesno(
                "Replace Save",
                f"{save.name} already exists on this card.\n\n"
                f"Replace it with the save from {os.path.basename(path)}?"):
            return
        
        def imported():
            self.select_root_entry(save.name)
            self.status_var.set(f"Imported {save.name} ({self.format_size(save.size)})")
        
        self.run_card_change(f"Importing {save.name}",
                             lambda reader: ps2_saves.import_save(reader, save, replace=replace),
                             imported, "Import Failed")
        
    def delete_selected_save(self):
        """Delete the selected save folder from the card"""
        name = self.selected_save_name()
        if self.busy or not name or not self.can_modify_card():
            return
        if not messagebox.askyesno("Delete Save",
                                   f"Delete {name} from this card?\n\n"
                                   "This cannot be undone. Export it first to keep a copy."):
            return
        self.run_card_change(f"Deleting {name}",
                             lambda reader: ps2_saves.delete_save(reader, name),
                             lambda: self.status_var.set(f"Deleted {name}"), "Delete Failed")
        
    def run_card_change(self, description, change, on_done, failure_title):
        """
        Apply change(reader) to the card. A .ps2 file is changed directly, a physical
        card through a PhysicalCardSession in the background.
        """
        if not self.is_physical:
            try:
                change(self.current_reader)
            except Exception as e:
                self.show_change_error(failure_title, e)
                self.refresh_card()
                return
            self.refresh_card()
            on_done()
            return
        
        self.status_var.set(f"{description}...")
        
        def work(report):
            report(description, 0, 1)
            session = PhysicalCardSession(self.current_reader)
            session.progress = lambda done, total: report(f"{description}, writing", done, total)
            change(session)
        
        def finished(error):
            if error is not None:
                self.show_change_error(failure_title, error)
            self.refresh_card()
            if error is None:
                on_done()
        
        self.run_in_background(work, finished)
        
    def show_change_error(self, title, error):
        if isinstance(error, NotEnoughSpaceError):
            messagebox.showerror("Not Enough Space", str(error))
        elif isinstance(error, PhysicalWriteError):
            messagebox.showerror(title,
                                 f"Writing to the card failed: {error}.\n\n"
                                 "The card may be left in an inconsistent state. If you have a dump "
                                 "of it, restore it with Tools > Load from .ps2 File.")
        else:
            messagebox.showerror(title, str(error))
        
    def run_in_background(self, work, finished):
        """Run work(report) in a thread with the progress bar, then finished(error) in the UI thread"""
        self.set_busy(True)
        self.show_progress()
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Working...")
        
        def report(text, done, total):
            percent = done / total * 100 if total else 0
            self.root.after(0, lambda: (self.progress_label.config(text=f"{text}... {percent:.0f}%"),
                                        self.progress_bar.config(value=percent)))
        
        def thread():
            error = None
            try:
                work(report)
            except Exception as e:
                error = e
            self.root.after(0, lambda: self.background_done(finished, error))
        
        threading.Thread(target=thread, daemon=True).start()
        
    def background_done(self, finished, error):
        self.progress_frame.pack_forget()
        self.set_busy(False)
        finished(error)
        
    def set_busy(self, busy):
        """Block card actions while a background task talks to the card"""
        self.busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        for button in self.toolbar.winfo_children():
            button.config(state=state)
        if busy:
            self.back_btn.config(state=tk.DISABLED)
        else:
            self.update_navigation_state()
        
    def on_close(self):
        """Ask before quitting while a change is being written"""
        if self.busy and not messagebox.askyesno(
                "Quit",
                "The card is being written to. Quitting now can leave it damaged.\n\nQuit anyway?"):
            return
        self.root.destroy()
        
        
    def update_navigation_state(self):
        """Refresh the breadcrumb, the Back button and the empty hint"""
        self.current_dir_label.config(text="/  " + "  /  ".join(self.path_names) if self.path_names else "/")
        
        if self.navigation_stack:
            self.back_btn.config(state=tk.NORMAL, bg=self.colors['accent_blue'])
        else:
            self.back_btn.config(state=tk.DISABLED, bg=self.colors['bg_elevated'])
        
        if self.dir_tree.get_children():
            self.empty_label.place_forget()
        else:
            if self.current_reader:
                self.empty_label.config(text="This folder is empty")
            else:
                self.empty_label.config(text="No memory card loaded\n\n"
                                             "Open a .ps2 file or connect a physical card to get started")
            self.empty_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
    def setup_status_bar(self, parent):
        """Setup the status bar"""
        self.status_var = tk.StringVar(value="Ready to connect")
        status_bar = tk.Frame(parent, bg=self.colors['bg_secondary'], padx=16, pady=8)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=24, pady=(0, 20))
        
        tk.Label(status_bar, textvariable=self.status_var, 
                 anchor=tk.W, 
                 bg=self.colors['bg_secondary'], 
                 fg=self.colors['text_secondary'],
                 font=(self.ui_font, 10)).pack(side=tk.LEFT)
        
        # Free space gauge, shown while a formatted card is loaded
        self.space_frame = tk.Frame(status_bar, bg=self.colors['bg_secondary'])
        self.space_label = tk.Label(self.space_frame, bg=self.colors['bg_secondary'],
                                    fg=self.colors['text_secondary'], font=(self.ui_font, 10))
        self.space_label.pack(side=tk.LEFT, padx=(0, 10))
        self.space_bar = tk.Canvas(self.space_frame, width=160, height=8,
                                   bg=self.colors['bg_tertiary'], highlightthickness=0)
        self.space_bar.pack(side=tk.LEFT)
        
    def update_free_space(self):
        """Show the free space of the card, like the PS2 browser does"""
        self.space_frame.pack_forget()
        if not self.current_reader:
            return
        try:
            if not self.current_reader.is_formatted():
                return
            cluster_size = self.current_reader.get_cluster_size()
            total_kb = self.current_reader.get_superblock_info()['alloc_end'] * cluster_size // 1024
            free_kb = self.current_reader.get_free_cluster_count() * cluster_size // 1024
        except Exception:
            return
        if not total_kb:
            return
        
        free_ratio = free_kb / total_kb
        if free_ratio < 0.05:
            color = self.colors['accent_red']
        elif free_ratio < 0.15:
            color = self.colors['accent_orange']
        else:
            color = self.colors['accent_blue']
        
        self.space_label.config(text=f"{free_kb:,} KB free of {total_kb:,} KB")
        self.space_bar.delete('all')
        self.space_bar.create_rectangle(0, 0, int(self.space_bar['width']) * (1 - free_ratio), 8,
                                        fill=color, outline='')
        self.space_frame.pack(side=tk.RIGHT)
        
    def make_button(self, parent, text, command, kind='secondary'):
        """Flat button: primary (blue), secondary (dark) or danger (red)"""
        background, hover = {
            'primary': (self.colors['accent_blue'], self.colors['accent_blue_bright']),
            'secondary': (self.colors['bg_elevated'], self.colors['border']),
            'danger': (self.colors['accent_red'], self.colors['ps_circle']),
        }[kind]
        return tk.Button(parent, text=text, command=command,
                         bg=background,
                         fg=self.colors['text_primary'],
                         activebackground=hover,
                         activeforeground=self.colors['text_primary'],
                         font=(self.ui_font, 10, 'bold'),
                         relief=tk.FLAT,
                         bd=0,
                         highlightthickness=0,
                         padx=14,
                         pady=5,
                         cursor='hand2')
        
    def update_toolbar(self):
        """Rebuild the card actions shown next to the breadcrumb"""
        for child in self.toolbar.winfo_children():
            child.destroy()
        
        if not self.current_reader:
            actions = [("Open .ps2 File", self.load_memory_card_file, 'primary'),
                       ("Connect Physical Card", self.connect_to_physical_card, 'secondary')]
        else:
            actions = [("Card Information", self.show_card_info_popup, 'secondary')]
            if self.can_modify_card():
                actions.append(("Import Save", self.import_save, 'secondary'))
            actions.append(("Export Save", self.export_selected_save, 'secondary'))
            if self.is_physical:
                actions += [("Dump", self.dump_physical_card, 'secondary'),
                            ("Load", self.load_to_physical_card, 'secondary'),
                            ("Erase All", self.erase_physical_card, 'danger')]
            actions.append(("Disconnect" if self.is_physical else "Close", self.disconnect, 'secondary'))
        
        for text, command, kind in actions:
            self.make_button(self.toolbar, text, command, kind).pack(side=tk.LEFT, padx=(8, 0))
        
    def show_card_info_popup(self):
        """Show card information in a popup window"""
        if self.busy:
            return
        if not self.current_reader:
            messagebox.showwarning("No Connection", "Please connect to a memory card first.")
            return
            
        # Create popup window
        popup = tk.Toplevel(self.root)
        popup.title("Memory Card Information")
        popup.configure(bg=self.colors['bg_primary'])
        popup.resizable(False, False)
        
        # Center the popup
        popup.transient(self.root)
        popup.grab_set()
        
        # Main frame
        main_frame = tk.Frame(popup, bg=self.colors['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="Memory Card Information", 
                              font=(self.ui_font, 16, 'bold'), 
                              bg=self.colors['bg_primary'], 
                              fg=self.colors['text_primary'])
        title_label.pack(anchor=tk.W, pady=(0, 14))
        
        # Load card information
        try:
            reader = self.current_reader
            superblock = reader.get_superblock_info()
            
            # Calculate total size
            total_size_mb = (superblock['clusters_per_card'] * superblock['pages_per_cluster'] * 528) / (1024*1024)
            cluster_size = reader.get_cluster_size()
            free_kb = reader.get_free_cluster_count() * cluster_size // 1024
            total_kb = superblock['alloc_end'] * cluster_size // 1024
            
            sections = [
                ("Specifications", [
                    ("Size", f"{total_size_mb:.1f} MB ({superblock['clusters_per_card']:,} clusters)"),
                    ("Free space", f"{free_kb:,} KB of {total_kb:,} KB"),
                    ("Format", f"{superblock['magic'].strip()} v{superblock['version']}"),
                    ("Page size", f"{superblock['page_len']} bytes"),
                    ("Block size", f"{superblock['pages_per_block']} pages"),
                ]),
                ("Features", [
                    ("ECC support", "Yes" if reader.has_ecc_support() else "No"),
                    ("Bad block management", "Yes" if reader.has_bad_blocks() else "No"),
                    ("Erase mode", "Zero" if reader.erased_blocks_are_zeroes() else "One"),
                ]),
                ("Structure", [
                    ("Root directory", f"Cluster {superblock['rootdir_cluster']}"),
                    ("Allocation range", f"{superblock['alloc_offset']} - {superblock['alloc_end']}"),
                    ("Backup blocks", f"{superblock['backup_block1']}, {superblock['backup_block2']}"),
                ]),
            ]
        except Exception as e:
            sections = [("Error", [("Card info", f"Could not be loaded: {str(e)}")])]
        
        for title, rows in sections:
            section = tk.Frame(main_frame, bg=self.colors['bg_secondary'], padx=16, pady=12)
            section.pack(fill=tk.X, pady=(0, 12))
            # Same label width in every section so the values line up
            section.columnconfigure(0, minsize=190)
            section.columnconfigure(1, weight=1)
            
            tk.Label(section, text=title.upper(), bg=self.colors['bg_secondary'],
                     fg=self.colors['text_accent'], font=(self.ui_font, 9, 'bold')
                     ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))
            for row, (label, value) in enumerate(rows, start=1):
                tk.Label(section, text=label, bg=self.colors['bg_secondary'],
                         fg=self.colors['text_muted'], font=(self.ui_font, 10)
                         ).grid(row=row, column=0, sticky=tk.W, padx=(0, 24), pady=2)
                tk.Label(section, text=value, bg=self.colors['bg_secondary'],
                         fg=self.colors['text_primary'], font=(self.ui_font, 10)
                         ).grid(row=row, column=1, sticky=tk.W, pady=2)
        
        # Close button
        close_btn = self.make_button(main_frame, "Close", popup.destroy, 'primary')
        close_btn.pack(anchor=tk.E, pady=(4, 0))
        popup.bind('<Escape>', lambda event: popup.destroy())
        
        
    def update_menu_state(self):
        """Update menu items based on connection state"""
        # Clear existing disconnect/close commands if they exist
        try:
            self.file_menu.delete("Disconnect")
        except:
            pass
        try:
            self.file_menu.delete("Close Memory Card File")
        except:
            pass
            
        # Clear existing connection commands if they exist
        try:
            self.file_menu.delete("Load Memory Card File")
            self.file_menu.delete("Connect to Physical Memory Card")
        except:
            pass
            
        if self.current_reader:
            # Connected state - show disconnect option
            if self.is_physical:
                # Physical card connected - show disconnect
                self.file_menu.insert_command(0, label="Disconnect", command=self.disconnect)
            else:
                # Virtual card loaded - show close option
                self.file_menu.insert_command(0, label="Close Memory Card File", command=self.disconnect)
            # Hide connection options when connected
        else:
            # Not connected - show connection options
            self.file_menu.insert_command(0, label="Load Memory Card File", command=self.load_memory_card_file)
            self.file_menu.insert_command(1, label="Connect to Physical Memory Card", command=self.connect_to_physical_card)
        
    def update_tools_menu_state(self):
        """Rebuild the tools menu for the current card"""
        self.tools_menu.delete(0, tk.END)
        self.tools_menu.add_command(label="Card Information", command=self.show_card_info_popup)
        if self.current_reader and not self.is_physical and self.current_reader.supports_writing():
            self.tools_menu.add_command(label="Format Card...", command=self.format_card)
        
        # Physical card tools
        if self.current_reader and self.is_physical:
            self.tools_menu.add_separator()
            self.tools_menu.add_command(label="Dump to .ps2 File", command=self.dump_physical_card)
            self.tools_menu.add_command(label="Load from .ps2 File", command=self.load_to_physical_card)
            self.tools_menu.add_command(label="Erase All", command=self.erase_physical_card)
        
    def new_memory_card_file(self):
        """Create an empty formatted .ps2 file and open it"""
        if self.busy:
            return
        path = native_dialogs.asksaveasfilename(
            parent=self.root,
            title="New Memory Card File",
            initialfile="Mcd001.ps2",
            defaultextension=".ps2",
            filetypes=[("PS2 Memory Card", "*.ps2"), ("All Files", "*.*")]
        )
        if not path:
            return
        # The file may be the one open right now
        if self.current_reader:
            self.disconnect()
        try:
            ps2_format.format_file(path)
        except OSError as e:
            messagebox.showerror("New Memory Card File", f"Could not create {os.path.basename(path)}:\n{e}")
            return
        self.conn_var.set("virtual")
        self.file_path_var.set(path)
        self.current_file_path = path
        self.connect()
        self.status_var.set(f"Created {os.path.basename(path)}")
        
    def format_card(self):
        """Erase everything on the open .ps2 file and format it again"""
        if self.busy or not self.current_reader or self.is_physical or not self.current_reader.supports_writing():
            return
        name = os.path.basename(self.current_file_path)
        if not messagebox.askyesno("Format Card",
                                   f"Format {name}?\n\n"
                                   "Every save on it will be erased. This cannot be undone."):
            return
        try:
            self.current_reader.replace_image(ps2_format.format_image())
        except OSError as e:
            messagebox.showerror("Format Failed", f"Could not format {name}:\n{e}")
            self.refresh_card()
            return
        self.refresh_card()
        self.status_var.set(f"Formatted {name}")
        
    def load_memory_card_file(self):
        """Load a memory card file from File menu"""
        if self.busy:
            return
        self.conn_var.set("virtual")
        self.on_connection_change()
        
        # Browse for file and connect if selected
        file_path = native_dialogs.askopenfilename(
            parent=self.root,
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
        if self.busy:
            return
        self.conn_var.set("physical")
        self.on_connection_change()
        self.connect()
        
    def on_connection_change(self):
        """Handle connection type change"""
        if self.conn_var.get() == "physical":
            self.current_file_path = None
            
    def browse_file(self):
        """Browse for a .ps2 file"""
        file_path = native_dialogs.askopenfilename(
            parent=self.root,
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
        self.update_connection_badge()
        self.update_toolbar()
        self.update_free_space()
        
        self.status_var.set("Ready")
        
    def on_connection_error(self, error_msg):
        """Handle connection error"""
        self.status_var.set(f"Connection failed: {error_msg}")
        messagebox.showerror("Connection Error", f"Failed to connect: {error_msg}")
        
    def disconnect(self):
        """Disconnect from memory card"""
        if self.busy:
            return
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
        
        # Clear the hidden data dictionary
        self.tree_item_data.clear()
        
        self.navigation_stack = []
        self.path_names = []
        self.current_directory = None
        self.update_navigation_state()
        self.update_connection_badge()
        self.update_toolbar()
        self.update_free_space()
            
        # Update menu state
        self.update_menu_state()
        self.update_tools_menu_state()
            
        self.status_var.set("Disconnected")
              
    def load_directory_listing(self):
        """Load and display directory listing"""
        try:
            # Get root directory cluster
            root_cluster = self.current_reader.get_root_directory_cluster()
            
            # Get directory entries
            entries = self.current_reader.get_directory_content(root_cluster)
            
            self.navigation_stack = []
            self.path_names = []
            self.current_directory = root_cluster
            self.populate_directory_tree(entries)
            
        except Exception as e:
            messagebox.showerror("Directory Error", f"Failed to load directory: {str(e)}")

    def on_tree_double_click(self, event):
        """Handle double-click on the directory tree to navigate into folders"""
        if self.busy:
            return
        selected_item = self.dir_tree.selection()
        if not selected_item:
            return
            
        item_id = selected_item[0]
        item_values = self.dir_tree.item(item_id)['values']
        
        if not item_values:
            return
            
        # Retrieve hidden data from dictionary
        entry_data = self.tree_item_data.get(item_id)
        if not entry_data:
            return
            
        # The parent pointer goes back up instead of pushing a new level
        if entry_data['name'] == PARENT_DIRECTORY_LABEL:
            self.navigate_back()
            return
            
        # Check if it's a directory
        if item_values[0] == "DIR":
            # Get the cluster number from the values
            cluster_num = entry_data['cluster']  # Cluster column
            
            if cluster_num is not None:
                self.navigate_to_directory(cluster_num, entry_data['name'])

        if item_values[0] == "FILE":
            file_cluster = entry_data['cluster']
            file_data = self.current_reader.read_file(file_cluster, entry_data['length'])
            extension = entry_data['name'].split('.')[-1] if entry_data['name'].find('.') != -1 else ''
            if len(extension) > 0:
                extension = f".{extension}"

            file_path = native_dialogs.asksaveasfilename(
                parent=self.root,
                title="Save File",
                initialfile=entry_data['name'],
                defaultextension=f"{extension}",
                filetypes=[("All Files", "*.*")]
            )
            if file_path:
                with open(file_path, 'wb') as f:
                    f.write(file_data)
                messagebox.showinfo("File Saved", f"File saved to {file_path}")
    
    def navigate_to_directory(self, cluster_num, name):
        """Navigate to a specific directory cluster"""
        if not self.current_reader:
            messagebox.showwarning("Not Connected", "Please connect to a memory card first.")
            return
            
        try:
            # Navigate to the new directory using existing method
            entries = self.current_reader.get_directory_content(cluster_num)
            
            if entries:
                # Store current directory in navigation stack
                if self.current_directory is not None:
                    self.navigation_stack.append(self.current_directory)
                self.path_names.append(name)
                
                # Update current directory
                self.current_directory = cluster_num
                
                # Clear and repopulate the tree
                self.populate_directory_tree(entries)
                
                self.status_var.set(f"Opened {name}")
            else:
                messagebox.showinfo("Empty Directory", f"Directory cluster {cluster_num} is empty or could not be read.")
                
        except Exception as e:
            messagebox.showerror("Navigation Error", f"Failed to navigate to cluster {cluster_num}: {str(e)}")
            self.status_var.set(f"Navigation failed: {str(e)}")
    
    def navigate_back(self):
        """Navigate back to the previous directory"""
        if self.busy:
            return
        if not self.navigation_stack:
            return
            
        try:
            # Navigate back using existing method
            previous_cluster = self.navigation_stack[-1]
            entries = self.current_reader.get_directory_content(previous_cluster)
            
            if entries:
                self.navigation_stack.pop()
                self.path_names.pop()
                
                # Update current directory
                self.current_directory = previous_cluster
                
                # Clear and repopulate the tree
                self.populate_directory_tree(entries)
                
                self.status_var.set("Back to /" + "/".join(self.path_names))
            else:
                messagebox.showinfo("Navigation Error", f"Could not navigate back to cluster {previous_cluster}")
                
        except Exception as e:
            messagebox.showerror("Navigation Error", f"Failed to navigate back: {str(e)}")
            self.status_var.set(f"Navigation failed: {str(e)}")
            
    @staticmethod
    def format_size(length):
        """Human readable file size"""
        if length < 1024:
            return f"{length} B"
        if length < 1024 * 1024:
            return f"{length / 1024:.1f} KB"
        return f"{length / (1024 * 1024):.2f} MB"
    
    def populate_directory_tree(self, entries):
        """Populate the directory tree with entries"""
        # Clear existing items
        for item in self.dir_tree.get_children():
            self.dir_tree.delete(item)
        
        # Clear the hidden data dictionary
        self.tree_item_data.clear()
        
        # Parent pointer first, then entries by name in ascending order
        entries = sorted((entry for entry in entries if entry),
                         key=lambda x: (x['name'] != PARENT_DIRECTORY_LABEL, (x['name'] or '').lower()))
        
        # Populate tree with new entries
        for index, entry in enumerate(entries):
            # Type text and row color
            if entry['is_dir']:
                type_text = "DIR"
                type_tag = 'parent' if entry['name'] == PARENT_DIRECTORY_LABEL else 'dir'
                #if entry['is_hidden']:
                #    type_text = f"{type_text} [HIDDEN]"
            elif entry['is_ps1']:
                type_text = "PS1"
                type_tag = 'ps1'
            elif entry['is_pocketstation']:
                type_text = "PS"
                type_tag = 'pocketstation'
            else:
                type_text = "FILE"
                type_tag = 'file'
            
            # Directories already say DIR in the type column
            size_str = "" if entry['is_dir'] else self.format_size(entry['length'])
            
            tags = (type_tag, 'odd') if index % 2 else (type_tag,)
            
            # Insert into tree
            item = self.dir_tree.insert('', 'end', text=entry['name'], tags=tags,
                               values=(type_text, size_str, entry['created'], entry['modified']))
            
            # Store additional hidden data in dictionary
            self.tree_item_data[item] = entry
        
        self.update_navigation_state()

    def dump_physical_card(self):
        """Dump the physical memory card to a .ps2 file"""
        if self.busy:
            return
        if not self.current_reader or not self.is_physical:
            messagebox.showwarning("Not Connected", "Please connect to a physical memory card first.")
            return
            
        # Ask user for save location
        file_path = native_dialogs.asksaveasfilename(
            parent=self.root,
            title="Save Memory Card Dump",
            defaultextension=".ps2",
            filetypes=[("PS2 Memory Card", "*.ps2"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            self.status_var.set("Starting memory card dump...")
            
            # Show progress bar
            self.show_progress()
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
                            except Exception as e:
                                raise IOError(f"Failed to read page {page_num}: {e}") from e

                            # Write page data
                            f.write(bytes(cluster_data) + bytes(ecc))

                            # Update progress bar
                            progress = ((page_num + 1) / total_pages) * 100
                            self.root.after(0, lambda p=progress, c=page_num+1, t=total_pages:
                                          self.update_progress("Dumping memory card", p, c, t))

                    # Success message
                    self.root.after(0, lambda: self.on_dump_success(file_path))

                except Exception as e:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    error_msg = f"{e}\n\nThe incomplete dump file was deleted."
                    self.root.after(0, lambda: self.on_dump_error(error_msg))
                    
            self.set_busy(True)
            threading.Thread(target=dump_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Dump Error", f"Failed to start dump: {str(e)}")
            self.status_var.set("Dump failed")

    def load_to_physical_card(self):
        """Load a .ps2 file to the physical memory card"""
        if self.busy:
            return
        if not self.current_reader or not self.is_physical:
            messagebox.showwarning("Not Connected", "Please connect to a physical memory card first.")
            return
            
        # Ask user for source .ps2 file
        file_path = native_dialogs.askopenfilename(
            parent=self.root,
            title="Select PS2 Memory Card File to Load",
            filetypes=[("PS2 Memory Card", "*.ps2"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
            
        if not os.path.exists(file_path):
            messagebox.showerror("File Not Found", "The selected file does not exist")
            return
            
        try:
            self.status_var.set("Starting memory card load...")
            
            # Show progress bar
            self.show_progress()
            self.progress_bar['value'] = 0
            self.progress_label.config(text="Loading memory card from file...")
            
            # Run load in background thread
            def load_thread():
                virtual_reader = VirtualPs2MemoryCardReader(file_path)
                card_modified = False
                try:
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
                    card_modified = True
                    self.current_reader.erase_all()

                    sleep(5)

                    print("Loading physical card")
                    # Load all pages
                    for page_num in range(total_pages):
                        try:
                            cluster_data, ecc = virtual_reader.read_page(page_num)
                            self.current_reader.write_page(page_num, cluster_data, ecc)
                        except Exception as e:
                            raise IOError(f"Failed to write page {page_num}: {e}") from e

                        # Update progress bar
                        progress = ((page_num + 1) / total_pages) * 100
                        self.root.after(0, lambda p=progress, c=page_num+1, t=total_pages:
                                      self.update_progress("Importing file to physical card", p, c, t))

                    # Success message
                    self.root.after(0, lambda: self.on_load_success(file_path))

                except Exception as e:
                    error_msg = str(e)
                    if card_modified:
                        error_msg += "\n\nThe memory card is only partially written. Load the file again or erase the card."
                    self.root.after(0, lambda: self.on_load_error(error_msg))
                finally:
                    if virtual_reader.memory_card_file is not None:
                        virtual_reader.close()
                    self.current_reader.clear_superblock_cache()
                    
            self.set_busy(True)
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
        self.set_busy(False)
        self.status_var.set(f"Dump completed: {os.path.basename(file_path)}")
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        # Show success message
        messagebox.showinfo("Dump Complete", 
                          f"Memory card successfully dumped to:\n{file_path}\n\n"
                          f"File size: {os.path.getsize(file_path) / (1024*1024):.1f} MB")

    def on_dump_error(self, error_msg):
        """Handle dump error"""
        self.set_busy(False)
        self.status_var.set(f"Dump failed: {error_msg}")
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        messagebox.showerror("Dump Error", f"Failed to dump memory card:\n{error_msg}")

    def on_load_success(self, file_path):
        """Handle successful load completion"""
        self.set_busy(False)
        self.status_var.set(f"Load completed: {os.path.basename(file_path)}")
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        # The card content changed, reload what is shown
        self.current_reader.clear_superblock_cache()
        self.load_directory_listing()
        self.update_free_space()
        
        # Show success message
        messagebox.showinfo("Load Complete", 
                          f"Memory card successfully loaded from:\n{file_path}\n\n"
                          f"File size: {os.path.getsize(file_path) / (1024*1024):.1f} MB")

    def on_load_error(self, error_msg):
        """Handle load error"""
        self.set_busy(False)
        self.status_var.set(f"Load failed: {error_msg}")
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        messagebox.showerror("Load Error", f"Failed to load memory card:\n{error_msg}")

    def erase_physical_card(self):
        """Erase all content from the physical memory card"""
        if self.busy:
            return
        if not self.current_reader or not self.is_physical:
            messagebox.showerror("Error", "No physical memory card connected")
            return
            
        # Confirmation dialog
        result = messagebox.askyesno("Confirm Erase", 
                                   "WARNING: This will permanently erase ALL data on the memory card!\n\n"
                                   "This action cannot be undone. Are you sure you want to continue?")
        if not result:
            return
            
        # Show progress
        self.status_var.set("Erasing memory card...")
        
        # Show progress bar
        self.show_progress()
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
                
        self.set_busy(True)
        threading.Thread(target=erase_thread, daemon=True).start()

    def update_erase_progress(self, percentage, current, total):
        """Update the erase progress bar and label"""
        self.progress_bar['value'] = percentage
        self.progress_label.config(text=f"Erasing memory card... {current}/{total} pages ({percentage:.1f}%)")
        self.status_var.set(f"Erasing... {percentage:.1f}%")

    def on_erase_success(self):
        """Handle successful erase completion"""
        self.set_busy(False)
        self.status_var.set("Erase completed")
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        self.current_reader.clear_superblock_cache()
        for item in self.dir_tree.get_children():
            self.dir_tree.delete(item)
        self.tree_item_data.clear()
        self.navigation_stack.clear()
        self.path_names.clear()
        self.current_directory = None
        self.update_navigation_state()
        self.empty_label.config(text="Card erased")
        self.update_free_space()

        # Show success message
        messagebox.showinfo("Erase Complete", "Memory card has been completely erased!")

    def on_erase_error(self, error_msg):
        """Handle erase error"""
        self.set_busy(False)
        self.status_var.set(f"Erase failed: {error_msg}")
        
        # Hide progress bar
        self.progress_frame.pack_forget()
        
        messagebox.showerror("Erase Error", f"Failed to erase memory card:\n{error_msg}")

def main():
    root = tk.Tk()
    app = Ps2MemoryCardGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
