import tkinter as tk
import customtkinter as ctk
import time
import os

class UIComponents:
    def __init__(self, app):
        self.app = app
        self.tab_switching = False
        
    def setup_main_ui(self):
        """Set up the main UI structure"""
        # Main frame that fills the window
        self.app.main_frame = ctk.CTkFrame(self.app.root)
        self.app.main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Header with app name
        self.app.header_label = ctk.CTkLabel(
            self.app.main_frame,
            text="Rushes Transfer Tool",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.app.header_label.pack(pady=(0, 10))
        
        # Add a tab view to organize the sections better
        self.app.tab_view = ctk.CTkTabview(self.app.main_frame)
        self.app.tab_view.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create tabs
        self.app.tab_view.add("Transfer")
        self.app.tab_view.add("File Selection")
        
        # Track tab switching to optimize performance
        def on_tab_change(*args):
            self.tab_switching = True
            # Schedule a reset of the switching flag after UI updates
            self.app.root.after(100, self.app.finish_tab_switch)
        
        # Store the current tab to detect changes
        self.app.current_tab = "Transfer"
        
        # Override the set method on the tab view to track tab changes
        original_set = self.app.tab_view.set
        
        def tracked_set(name):
            if name != self.app.current_tab:
                self.tab_switching = True
                self.app.current_tab = name
                self.app.root.after(100, self.app.finish_tab_switch)
            return original_set(name)
            
        self.app.tab_view.set = tracked_set
        
        # Try to bind to tab change event by hooking into the underlying tkinter event
        notebook_found = False
        for child in self.app.tab_view.winfo_children():
            if isinstance(child, ctk.CTkFrame) and hasattr(child, 'winfo_children'):
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.ttk.Notebook):
                        subchild.bind("<<NotebookTabChanged>>", on_tab_change)
                        notebook_found = True
                        break
                if notebook_found:
                    break
        
        # Action buttons at the bottom of main frame
        self.app.button_frame = ctk.CTkFrame(self.app.main_frame, fg_color="transparent")
        self.app.button_frame.pack(fill=tk.X, pady=5)
        
        self.app.transfer_button = ctk.CTkButton(
            self.app.button_frame,
            text="Start Transfer",
            command=self.app.start_transfer_with_selection,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.app.transfer_button.pack(side=tk.RIGHT, padx=8)
        
        self.app.cancel_button = ctk.CTkButton(
            self.app.button_frame,
            text="Cancel",
            command=self.app.cancel_transfer,
            height=36,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            state="disabled",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.app.cancel_button.pack(side=tk.RIGHT, padx=8)
    
    def setup_transfer_tab(self):
        """Set up the transfer tab UI"""
        self.app.transfer_tab = self.app.tab_view.tab("Transfer")
        
        # Create left and right panels for transfer tab
        self.app.panel_frame = ctk.CTkFrame(self.app.transfer_tab, fg_color="transparent")
        self.app.panel_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for source and project selection
        self.app.left_panel = ctk.CTkFrame(self.app.panel_frame)
        self.app.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        
        # Right panel for progress and notifications
        self.app.right_panel = ctk.CTkFrame(self.app.panel_frame)
        self.app.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))
        
        # ===== LEFT PANEL =====
        self._setup_source_section()
        self._setup_project_section()
        self._setup_destination_section()
        
        # ===== RIGHT PANEL =====
        self._setup_progress_section()
        self._setup_notification_section()
    
    def _setup_source_section(self):
        """Set up the source input section"""
        # Source section
        self.app.source_frame = ctk.CTkFrame(self.app.left_panel)
        self.app.source_frame.pack(fill=tk.X, pady=5)
        
        self.app.source_label = ctk.CTkLabel(
            self.app.source_frame,
            text="Memory Card Clips Location",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.app.source_label.pack(anchor=tk.W, padx=8, pady=(8, 2))
        
        self.app.source_entry_frame = ctk.CTkFrame(self.app.source_frame, fg_color="transparent")
        self.app.source_entry_frame.pack(fill=tk.X, padx=8, pady=2)
        
        self.app.source_entry = ctk.CTkEntry(
            self.app.source_entry_frame, 
            placeholder_text="Path to memory card clips", 
            height=30
        )
        self.app.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        
        # Set source entry value if we have it from config
        if self.app.source_path:
            self.app.source_entry.insert(0, self.app.source_path)
        
        self.app.browse_button = ctk.CTkButton(
            self.app.source_entry_frame,
            text="Browse",
            command=self.app.browse_source,
            width=80,
            height=30
        )
        self.app.browse_button.pack(side=tk.LEFT, padx=4)
        
        self.app.auto_detect_button = ctk.CTkButton(
            self.app.source_entry_frame,
            text="Auto-Detect",
            command=self.app.auto_detect_card,
            width=80,
            height=30
        )
        self.app.auto_detect_button.pack(side=tk.LEFT)
    
    def _setup_project_section(self):
        """Set up the project selection section"""
        # Project section
        self.app.project_frame = ctk.CTkFrame(self.app.left_panel)
        self.app.project_frame.pack(fill=tk.X, pady=5)
        
        self.app.project_label = ctk.CTkLabel(
            self.app.project_frame,
            text="Project Selection",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.app.project_label.pack(anchor=tk.W, padx=8, pady=(8, 2))
        
        # Projects root directory selection
        self.app.projects_dir_frame = ctk.CTkFrame(self.app.project_frame, fg_color="transparent")
        self.app.projects_dir_frame.pack(fill=tk.X, padx=8, pady=2)
        
        self.app.projects_dir_label = ctk.CTkLabel(self.app.projects_dir_frame, text="Projects Location:")
        self.app.projects_dir_label.pack(side=tk.LEFT, padx=(0, 8))
        
        self.app.projects_dir_path = ctk.CTkLabel(
            self.app.projects_dir_frame, 
            text=self.app.destination_base_path,
            anchor="w"
        )
        self.app.projects_dir_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        self.app.browse_projects_button = ctk.CTkButton(
            self.app.projects_dir_frame,
            text="Browse",
            command=self.app.browse_projects_dir,
            width=80,
            height=30
        )
        self.app.browse_projects_button.pack(side=tk.LEFT)
        
        # Existing project selection
        self.app.project_select_frame = ctk.CTkFrame(self.app.project_frame, fg_color="transparent")
        self.app.project_select_frame.pack(fill=tk.X, padx=8, pady=2)
        
        self.app.project_combo_label = ctk.CTkLabel(self.app.project_select_frame, text="Select Project:")
        self.app.project_combo_label.pack(side=tk.LEFT, padx=(0, 8))
        
        self.app.project_combo_var = tk.StringVar()
        self.app.project_combo = ctk.CTkOptionMenu(
            self.app.project_select_frame,
            variable=self.app.project_combo_var,
            values=[],
            command=self.app.on_project_selected,
            width=220,
            height=30
        )
        self.app.project_combo.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        
        self.app.refresh_button = ctk.CTkButton(
            self.app.project_select_frame,
            text="Refresh",
            command=self.app.refresh_projects,
            width=80,
            height=30
        )
        self.app.refresh_button.pack(side=tk.LEFT)
        
        # New project creation
        self.app.new_project_frame = ctk.CTkFrame(self.app.project_frame, fg_color="transparent")
        self.app.new_project_frame.pack(fill=tk.X, padx=8, pady=2)
        
        self.app.new_project_label = ctk.CTkLabel(self.app.new_project_frame, text="New Project:")
        self.app.new_project_label.pack(side=tk.LEFT, padx=(0, 8))
        
        self.app.new_project_entry = ctk.CTkEntry(
            self.app.new_project_frame,
            placeholder_text="Enter new project name",
            height=30
        )
        self.app.new_project_entry.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        
        self.app.create_button = ctk.CTkButton(
            self.app.new_project_frame,
            text="Create",
            command=self.app.create_project,
            width=80,
            height=30
        )
        self.app.create_button.pack(side=tk.LEFT)
    
    def _setup_destination_section(self):
        """Set up the destination path preview section"""
        # Destination preview
        self.app.dest_frame = ctk.CTkFrame(self.app.left_panel)
        self.app.dest_frame.pack(fill=tk.X, pady=5)
        
        self.app.dest_label = ctk.CTkLabel(
            self.app.dest_frame,
            text="Destination",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.app.dest_label.pack(anchor=tk.W, padx=8, pady=(8, 2))
        
        self.app.dest_path_frame = ctk.CTkFrame(self.app.dest_frame, fg_color="transparent")
        self.app.dest_path_frame.pack(fill=tk.X, padx=8, pady=2)
        
        self.app.dest_path_label = ctk.CTkLabel(self.app.dest_path_frame, text="Rushes will be copied to:")
        self.app.dest_path_label.pack(side=tk.LEFT, padx=(0, 8))
        
        self.app.destination_label = ctk.CTkLabel(self.app.dest_path_frame, text="")
        self.app.destination_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _setup_progress_section(self):
        """Set up the transfer progress section"""
        # Transfer progress section
        self.app.progress_frame = ctk.CTkFrame(self.app.right_panel)
        self.app.progress_frame.pack(fill=tk.X, pady=5)
        
        self.app.progress_label = ctk.CTkLabel(
            self.app.progress_frame,
            text="Transfer Progress",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.app.progress_label.pack(anchor=tk.W, padx=8, pady=(8, 2))
        
        # Overall progress
        self.app.overall_progress_frame = ctk.CTkFrame(self.app.progress_frame, fg_color="transparent")
        self.app.overall_progress_frame.pack(fill=tk.X, padx=8, pady=2)
        
        self.app.overall_progress_label = ctk.CTkLabel(self.app.overall_progress_frame, text="Overall Progress:")
        self.app.overall_progress_label.pack(side=tk.LEFT, padx=(0, 8), pady=2)
        
        self.app.progress_bar = ctk.CTkProgressBar(self.app.overall_progress_frame, height=12)
        self.app.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=2)
        self.app.progress_bar.set(0)
        
        # Status frame with two columns layout
        self.app.status_grid_frame = ctk.CTkFrame(self.app.progress_frame)
        self.app.status_grid_frame.pack(fill=tk.X, padx=8, pady=2)
        
        # First column - current file info
        self.app.file_info_frame = ctk.CTkFrame(self.app.status_grid_frame, fg_color="transparent")
        self.app.file_info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        
        # Second column - transfer status
        self.app.status_frame = ctk.CTkFrame(self.app.status_grid_frame, fg_color="transparent")
        self.app.status_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))
        
        # Current file info - left column
        self.app.current_file_header = ctk.CTkLabel(self.app.file_info_frame, text="Current File:", anchor=tk.W)
        self.app.current_file_header.grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.app.current_file_label = ctk.CTkLabel(self.app.file_info_frame, text="None", anchor=tk.W)
        self.app.current_file_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.app.file_progress_label = ctk.CTkLabel(self.app.file_info_frame, text="File Progress:", anchor=tk.W)
        self.app.file_progress_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.app.file_progress_bar = ctk.CTkProgressBar(self.app.file_info_frame, height=12)
        self.app.file_progress_bar.grid(row=1, column=1, sticky=tk.EW, pady=1)
        self.app.file_progress_bar.set(0)
        
        self.app.file_size_header = ctk.CTkLabel(self.app.file_info_frame, text="File Size:", anchor=tk.W)
        self.app.file_size_header.grid(row=2, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.app.file_size_label = ctk.CTkLabel(self.app.file_info_frame, text="0 MB", anchor=tk.W)
        self.app.file_size_label.grid(row=2, column=1, sticky=tk.W, pady=1)
        
        self.app.speed_header = ctk.CTkLabel(self.app.file_info_frame, text="Transfer Speed:", anchor=tk.W)
        self.app.speed_header.grid(row=3, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.app.speed_label = ctk.CTkLabel(self.app.file_info_frame, text="0 MB/s", anchor=tk.W)
        self.app.speed_label.grid(row=3, column=1, sticky=tk.W, pady=1)
        
        # Transfer status - right column
        self.app.status_header = ctk.CTkLabel(self.app.status_frame, text="Status:", anchor=tk.W)
        self.app.status_header.grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.app.status_label = ctk.CTkLabel(self.app.status_frame, text="Ready", anchor=tk.W)
        self.app.status_label.grid(row=0, column=1, sticky=tk.W, pady=1)
        
        self.app.time_header = ctk.CTkLabel(self.app.status_frame, text="Time Remaining:", anchor=tk.W)
        self.app.time_header.grid(row=1, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.app.time_label = ctk.CTkLabel(self.app.status_frame, text="--:--", anchor=tk.W)
        self.app.time_label.grid(row=1, column=1, sticky=tk.W, pady=1)
        
        self.app.files_header = ctk.CTkLabel(self.app.status_frame, text="Files:", anchor=tk.W)
        self.app.files_header.grid(row=2, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.app.files_label = ctk.CTkLabel(self.app.status_frame, text="0/0", anchor=tk.W)
        self.app.files_label.grid(row=2, column=1, sticky=tk.W, pady=1)
        
        # Configure grid column expansion
        self.app.file_info_frame.columnconfigure(1, weight=1)
        self.app.status_frame.columnconfigure(1, weight=1)
    
    def _setup_notification_section(self):
        """Set up the notification area"""
        # Add notification area
        self.app.notification_frame = ctk.CTkFrame(self.app.right_panel)
        self.app.notification_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.app.notification_label = ctk.CTkLabel(
            self.app.notification_frame,
            text="Notifications",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.app.notification_label.pack(anchor=tk.W, padx=8, pady=(8, 2))
        
        self.app.notification_text = ctk.CTkTextbox(
            self.app.notification_frame,
            height=70,
            wrap="word",
            font=ctk.CTkFont(size=12)
        )
        self.app.notification_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=2)
        self.app.notification_text.insert("1.0", "Welcome to Rushes Transfer Tool\n")
        self.app.notification_text.configure(state="disabled")
    
    def setup_file_selection_tab(self):
        """Set up the file selection tab UI"""
        self.app.files_frame = ctk.CTkFrame(self.app.tab_view.tab("File Selection"))
        self.app.files_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Add header
        self.app.files_header_frame = ctk.CTkFrame(self.app.files_frame, fg_color="transparent")
        self.app.files_header_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.app.files_title = ctk.CTkLabel(
            self.app.files_header_frame,
            text="Files to Transfer",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.app.files_title.pack(side=tk.LEFT)
        
        self.app.select_all_var = tk.BooleanVar(value=False)
        self.app.select_all_cb = ctk.CTkCheckBox(
            self.app.files_header_frame,
            text="Select All",
            variable=self.app.select_all_var,
            command=self.app.toggle_select_all,
            onvalue=True,
            offvalue=False
        )
        self.app.select_all_cb.pack(side=tk.RIGHT)
        
        # Add thumbnail management - keep only the clear thumbnails button
        self.app.clear_thumbs_button = ctk.CTkButton(
            self.app.files_header_frame,
            text="Clear Thumbnails",
            command=self.app.cache_manager.clear_thumbnails,
            width=120,
            height=30
        )
        self.app.clear_thumbs_button.pack(side=tk.RIGHT, padx=10)
        
        # Add file list with scrollbar
        self.app.files_list_frame = ctk.CTkScrollableFrame(self.app.files_frame)
        self.app.files_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Column headers
        self.app.list_headers = ctk.CTkFrame(self.app.files_list_frame, fg_color="transparent")
        self.app.list_headers.pack(fill=tk.X, pady=(0, 8))
        
        ctk.CTkLabel(self.app.list_headers, text="", width=30).pack(side=tk.LEFT)  # Checkbox column
        ctk.CTkLabel(self.app.list_headers, text="", width=80).pack(side=tk.LEFT, padx=4)  # Thumbnail column
        ctk.CTkLabel(self.app.list_headers, text="Filename", width=200, anchor="w").pack(side=tk.LEFT, padx=4)
        ctk.CTkLabel(self.app.list_headers, text="Date Modified", width=150, anchor="w").pack(side=tk.LEFT, padx=4)
        ctk.CTkLabel(self.app.list_headers, text="Size", width=80, anchor="w").pack(side=tk.LEFT, padx=4)
        
        # File entries will be dynamically created
        self.app.file_entries = []
        
        # Add scan button at the bottom
        self.app.scan_button = ctk.CTkButton(
            self.app.files_frame,
            text="Rescan Source Directory",
            command=lambda: self.app.file_manager.scan_files(force_scan=True),
            height=36
        )
        self.app.scan_button.pack(pady=(8, 0))
    
    def add_file_entry(self, index, file_path, rel_path, mod_time, file_size):
        """Add a file entry to the list"""
        # Skip if we're in the middle of a tab switch to avoid UI glitches
        if self.tab_switching:
            return
            
        # Batch UI updates - create and configure widgets before adding to the UI
        entry_frame = ctk.CTkFrame(self.app.files_list_frame)
        
        # Checkbox for selection
        var = tk.BooleanVar(value=False)  # Not selected by default
        checkbox = ctk.CTkCheckBox(
            entry_frame, 
            text="", 
            variable=var,
            onvalue=True,
            offvalue=False,
            width=30,
            command=lambda p=file_path, v=var: self.app.toggle_file_selection(p, v)
        )
        
        # Add thumbnail placeholder initially, then queue up for real thumbnail
        thumb_label = ctk.CTkLabel(entry_frame, text="", image=self.app.cache_manager.placeholder_img)
        
        # Check if thumbnail is already in cache
        if file_path in self.app.cache_manager.thumbnail_cache:
            # Use cached thumbnail directly
            thumbnail = self.app.cache_manager.thumbnail_cache[file_path]
            thumb_label.configure(image=thumbnail)
        else:
            # Queue this file for thumbnail generation - no need to check for dragging now
            self.app.cache_manager.thumbnail_queue.put((file_path, thumb_label))
            
            # Start the thumbnail worker if not already running
            if not self.app.cache_manager.thumbnail_processing:
                self.app.cache_manager.start_thumbnail_worker()
        
        # Filename (just the base name, not the full path)
        filename = os.path.basename(file_path)
        file_label = ctk.CTkLabel(
            entry_frame, 
            text=filename, 
            width=200,
            anchor="w",
            justify="left"
        )
        
        # Date modified
        date_str = mod_time.strftime("%Y-%m-%d %H:%M")
        date_label = ctk.CTkLabel(
            entry_frame, 
            text=date_str, 
            width=150,
            anchor="w"
        )
        
        # File size
        size_str = self.format_size(file_size)
        size_label = ctk.CTkLabel(
            entry_frame, 
            text=size_str, 
            width=80,
            anchor="w"
        )
        
        # Now pack everything - reduces layout recalculations
        checkbox.pack(side=tk.LEFT)
        thumb_label.pack(side=tk.LEFT, padx=4)
        file_label.pack(side=tk.LEFT, padx=4)
        date_label.pack(side=tk.LEFT, padx=4)
        size_label.pack(side=tk.LEFT, padx=4)
        
        # Add the frame to the UI last
        entry_frame.pack(fill=tk.X, pady=2)
        
        # Store entry data
        self.app.file_entries.append({
            "frame": entry_frame,
            "checkbox": checkbox,
            "var": var,
            "file_path": file_path,
            "rel_path": rel_path
        })
    
    def format_size(self, size_bytes):
        """Convert bytes to a human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0 or unit == 'GB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0 
    
    def show_notification(self, message, message_type="info"):
        """Display a notification in the notification text box"""
        # No need to skip notifications during window drag anymore
            
        # Set color based on message type
        color_map = {
            "info": "white",
            "success": self.app.success_color,
            "warning": self.app.warning_color,
            "error": self.app.error_color
        }
        color = color_map.get(message_type, "white")
        
        # Get current time for timestamp
        timestamp = time.strftime("%H:%M:%S")
        
        # Enable the text box, insert message, and scroll to the end
        self.app.notification_text.configure(state="normal")
        self.app.notification_text.insert("end", f"[{timestamp}] ", "timestamp")
        self.app.notification_text.insert("end", f"{message}\n", message_type)
        
        # Configure tags with colors
        self.app.notification_text.tag_config("timestamp", foreground="#aaaaaa")
        self.app.notification_text.tag_config(message_type, foreground=color)
        
        # Autoscroll to the end
        self.app.notification_text.see("end")
        self.app.notification_text.configure(state="disabled")
        
        # Print to console as well
        print(f"{message_type.upper()}: {message}")
    
    def update_ui(self, progress_percentage, total_files, completed_files, status_text, time_text):
        """Update the UI with progress information"""
        # No need to skip UI updates during window dragging anymore
            
        def update():
            self.app.progress_bar.set(progress_percentage)
            self.app.status_label.configure(text=status_text)
            self.app.time_label.configure(text=time_text)
            self.app.files_label.configure(text=f"{completed_files}/{total_files}")
        
        self.app.root.after(0, update) 