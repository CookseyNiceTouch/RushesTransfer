import os
import shutil
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
import threading
import time
from datetime import datetime
import hashlib
import json
from PIL import Image, ImageTk
import cv2
import io
from pathlib import Path
import queue

# Set appearance mode and default color theme
ctk.set_appearance_mode("dark")  # Options: "Dark", "Light", "System"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"

class RushesTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rushes Transfer Tool")
        self.root.geometry("850x680")  # Reduced height and width
        self.root.resizable(True, True)
        
        # Default settings
        self.source_path = None
        self.destination_base_path = "D:\\NextCloud\\Nice Touch\\Projects"
        self.transfer_in_progress = False
        self.current_transfer_thread = None
        self.current_file_size = 0
        self.current_file_transferred = 0
        self.transfer_start_time = 0
        self.config_file = "rushes_transfer_config.json"
        self.config_loaded = False
        self.files_to_transfer = []
        self.selected_files = []
        self.thumbnail_cache = {}
        
        # Thumbnail queue and worker thread
        self.thumbnail_queue = queue.Queue()
        self.thumbnail_processing = False
        
        # Create a placeholder thumbnail for use while loading
        self.placeholder_img = self.create_placeholder_thumbnail()
        
        # Define colors
        self.accent_color = "#1f538d"
        self.success_color = "#00cc66"
        self.warning_color = "#ff9900"
        self.error_color = "#e74c3c"
        
        # Load configuration before setting up UI
        self.load_config()
        
        # Setup UI
        self.setup_ui()
        
        # Set up event handler for when window closes
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Automatically scan source path if available
        if self.source_path and os.path.exists(self.source_path):
            self.root.after(500, self.scan_files)
    
    def setup_ui(self):
        # Main frame that fills the window
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)  # Reduced padding
        
        # Header with app name
        self.header_label = ctk.CTkLabel(
            self.main_frame,
            text="Rushes Transfer Tool",
            font=ctk.CTkFont(size=20, weight="bold")  # Reduced font size
        )
        self.header_label.pack(pady=(0, 10))  # Reduced padding
        
        # Add a tab view to organize the sections better
        self.tab_view = ctk.CTkTabview(self.main_frame)
        self.tab_view.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create tabs
        self.tab_view.add("Transfer")
        self.tab_view.add("File Selection")
        
        # Transfer tab content - Using direct content instead of moving existing panel
        self.transfer_tab = self.tab_view.tab("Transfer")
        
        # Create left and right panels for transfer tab
        self.panel_frame = ctk.CTkFrame(self.transfer_tab, fg_color="transparent")
        self.panel_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for source and project selection
        self.left_panel = ctk.CTkFrame(self.panel_frame)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        
        # Right panel for progress and notifications
        self.right_panel = ctk.CTkFrame(self.panel_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))
        
        # ===== LEFT PANEL =====
        
        # Source section
        self.source_frame = ctk.CTkFrame(self.left_panel)
        self.source_frame.pack(fill=tk.X, pady=5)
        
        self.source_label = ctk.CTkLabel(
            self.source_frame,
            text="Memory Card Clips Location",
            font=ctk.CTkFont(size=14, weight="bold")  # Reduced font size
        )
        self.source_label.pack(anchor=tk.W, padx=8, pady=(8, 2))  # Reduced padding
        
        self.source_entry_frame = ctk.CTkFrame(self.source_frame, fg_color="transparent")
        self.source_entry_frame.pack(fill=tk.X, padx=8, pady=2)  # Reduced padding
        
        self.source_entry = ctk.CTkEntry(
            self.source_entry_frame, 
            placeholder_text="Path to memory card clips", 
            height=30  # Reduced height
        )
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        
        # Set source entry value if we have it from config
        if self.source_path:
            self.source_entry.insert(0, self.source_path)
        
        self.browse_button = ctk.CTkButton(
            self.source_entry_frame,
            text="Browse",
            command=self.browse_source,
            width=80,  # Reduced width
            height=30  # Reduced height
        )
        self.browse_button.pack(side=tk.LEFT, padx=4)
        
        self.auto_detect_button = ctk.CTkButton(
            self.source_entry_frame,
            text="Auto-Detect",
            command=self.auto_detect_card,
            width=80,  # Reduced width
            height=30  # Reduced height
        )
        self.auto_detect_button.pack(side=tk.LEFT)
        
        # Project section
        self.project_frame = ctk.CTkFrame(self.left_panel)
        self.project_frame.pack(fill=tk.X, pady=5)
        
        self.project_label = ctk.CTkLabel(
            self.project_frame,
            text="Project Selection",
            font=ctk.CTkFont(size=14, weight="bold")  # Reduced font size
        )
        self.project_label.pack(anchor=tk.W, padx=8, pady=(8, 2))  # Reduced padding
        
        # Existing project selection
        self.project_select_frame = ctk.CTkFrame(self.project_frame, fg_color="transparent")
        self.project_select_frame.pack(fill=tk.X, padx=8, pady=2)  # Reduced padding
        
        self.project_combo_label = ctk.CTkLabel(self.project_select_frame, text="Select Project:")
        self.project_combo_label.pack(side=tk.LEFT, padx=(0, 8))
        
        self.project_combo_var = tk.StringVar()
        self.project_combo = ctk.CTkOptionMenu(
            self.project_select_frame,
            variable=self.project_combo_var,
            values=[],
            command=self.on_project_selected,
            width=220,  # Reduced width
            height=30  # Reduced height
        )
        self.project_combo.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        
        self.refresh_button = ctk.CTkButton(
            self.project_select_frame,
            text="Refresh",
            command=self.refresh_projects,
            width=80,  # Reduced width
            height=30  # Reduced height
        )
        self.refresh_button.pack(side=tk.LEFT)
        
        # New project creation
        self.new_project_frame = ctk.CTkFrame(self.project_frame, fg_color="transparent")
        self.new_project_frame.pack(fill=tk.X, padx=8, pady=2)  # Reduced padding
        
        self.new_project_label = ctk.CTkLabel(self.new_project_frame, text="New Project:")
        self.new_project_label.pack(side=tk.LEFT, padx=(0, 8))
        
        self.new_project_entry = ctk.CTkEntry(
            self.new_project_frame,
            placeholder_text="Enter new project name",
            height=30  # Reduced height
        )
        self.new_project_entry.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        
        self.create_button = ctk.CTkButton(
            self.new_project_frame,
            text="Create",
            command=self.create_project,
            width=80,  # Reduced width
            height=30  # Reduced height
        )
        self.create_button.pack(side=tk.LEFT)
        
        # Destination preview
        self.dest_frame = ctk.CTkFrame(self.left_panel)
        self.dest_frame.pack(fill=tk.X, pady=5)
        
        self.dest_label = ctk.CTkLabel(
            self.dest_frame,
            text="Destination",
            font=ctk.CTkFont(size=14, weight="bold")  # Reduced font size
        )
        self.dest_label.pack(anchor=tk.W, padx=8, pady=(8, 2))  # Reduced padding
        
        self.dest_path_frame = ctk.CTkFrame(self.dest_frame, fg_color="transparent")
        self.dest_path_frame.pack(fill=tk.X, padx=8, pady=2)  # Reduced padding
        
        self.dest_path_label = ctk.CTkLabel(self.dest_path_frame, text="Rushes will be copied to:")
        self.dest_path_label.pack(side=tk.LEFT, padx=(0, 8))
        
        self.destination_label = ctk.CTkLabel(self.dest_path_frame, text="")
        self.destination_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # ===== RIGHT PANEL =====
        
        # Transfer progress section
        self.progress_frame = ctk.CTkFrame(self.right_panel)
        self.progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Transfer Progress",
            font=ctk.CTkFont(size=14, weight="bold")  # Reduced font size
        )
        self.progress_label.pack(anchor=tk.W, padx=8, pady=(8, 2))  # Reduced padding
        
        # Overall progress
        self.overall_progress_frame = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        self.overall_progress_frame.pack(fill=tk.X, padx=8, pady=2)  # Reduced padding
        
        self.overall_progress_label = ctk.CTkLabel(self.overall_progress_frame, text="Overall Progress:")
        self.overall_progress_label.pack(side=tk.LEFT, padx=(0, 8), pady=2)  # Reduced padding
        
        self.progress_bar = ctk.CTkProgressBar(self.overall_progress_frame, height=12)  # Reduced height
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=2)  # Reduced padding
        self.progress_bar.set(0)
        
        # Status frame with two columns layout
        self.status_grid_frame = ctk.CTkFrame(self.progress_frame)
        self.status_grid_frame.pack(fill=tk.X, padx=8, pady=2)
        
        # First column - current file info
        self.file_info_frame = ctk.CTkFrame(self.status_grid_frame, fg_color="transparent")
        self.file_info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        
        # Second column - transfer status
        self.status_frame = ctk.CTkFrame(self.status_grid_frame, fg_color="transparent")
        self.status_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))
        
        # Current file info - left column
        self.current_file_header = ctk.CTkLabel(self.file_info_frame, text="Current File:", anchor=tk.W)
        self.current_file_header.grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.current_file_label = ctk.CTkLabel(self.file_info_frame, text="None", anchor=tk.W)
        self.current_file_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.file_progress_label = ctk.CTkLabel(self.file_info_frame, text="File Progress:", anchor=tk.W)
        self.file_progress_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.file_progress_bar = ctk.CTkProgressBar(self.file_info_frame, height=12)  # Reduced height
        self.file_progress_bar.grid(row=1, column=1, sticky=tk.EW, pady=1)
        self.file_progress_bar.set(0)
        
        self.file_size_header = ctk.CTkLabel(self.file_info_frame, text="File Size:", anchor=tk.W)
        self.file_size_header.grid(row=2, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.file_size_label = ctk.CTkLabel(self.file_info_frame, text="0 MB", anchor=tk.W)
        self.file_size_label.grid(row=2, column=1, sticky=tk.W, pady=1)
        
        self.speed_header = ctk.CTkLabel(self.file_info_frame, text="Transfer Speed:", anchor=tk.W)
        self.speed_header.grid(row=3, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.speed_label = ctk.CTkLabel(self.file_info_frame, text="0 MB/s", anchor=tk.W)
        self.speed_label.grid(row=3, column=1, sticky=tk.W, pady=1)
        
        # Transfer status - right column
        self.status_header = ctk.CTkLabel(self.status_frame, text="Status:", anchor=tk.W)
        self.status_header.grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.status_label = ctk.CTkLabel(self.status_frame, text="Ready", anchor=tk.W)
        self.status_label.grid(row=0, column=1, sticky=tk.W, pady=1)
        
        self.time_header = ctk.CTkLabel(self.status_frame, text="Time Remaining:", anchor=tk.W)
        self.time_header.grid(row=1, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.time_label = ctk.CTkLabel(self.status_frame, text="--:--", anchor=tk.W)
        self.time_label.grid(row=1, column=1, sticky=tk.W, pady=1)
        
        self.files_header = ctk.CTkLabel(self.status_frame, text="Files:", anchor=tk.W)
        self.files_header.grid(row=2, column=0, sticky=tk.W, padx=(0, 8), pady=1)
        
        self.files_label = ctk.CTkLabel(self.status_frame, text="0/0", anchor=tk.W)
        self.files_label.grid(row=2, column=1, sticky=tk.W, pady=1)
        
        # Configure grid column expansion
        self.file_info_frame.columnconfigure(1, weight=1)
        self.status_frame.columnconfigure(1, weight=1)
        
        # Add notification area
        self.notification_frame = ctk.CTkFrame(self.right_panel)
        self.notification_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.notification_label = ctk.CTkLabel(
            self.notification_frame,
            text="Notifications",
            font=ctk.CTkFont(size=14, weight="bold")  # Reduced font size
        )
        self.notification_label.pack(anchor=tk.W, padx=8, pady=(8, 2))  # Reduced padding
        
        self.notification_text = ctk.CTkTextbox(
            self.notification_frame,
            height=70,  # Reduced height
            wrap="word",
            font=ctk.CTkFont(size=12)  # Reduced font size
        )
        self.notification_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=2)  # Reduced padding
        self.notification_text.insert("1.0", "Welcome to Rushes Transfer Tool\n")
        self.notification_text.configure(state="disabled")
        
        # Action buttons at the bottom of main frame
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.pack(fill=tk.X, pady=5)
        
        self.transfer_button = ctk.CTkButton(
            self.button_frame,
            text="Start Transfer",
            command=self.start_transfer_with_selection,
            height=36,  # Reduced height
            font=ctk.CTkFont(size=13, weight="bold")  # Reduced font size
        )
        self.transfer_button.pack(side=tk.RIGHT, padx=8)
        
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self.cancel_transfer,
            height=36,  # Reduced height
            fg_color="#e74c3c",
            hover_color="#c0392b",
            state="disabled",
            font=ctk.CTkFont(size=13, weight="bold")  # Reduced font size
        )
        self.cancel_button.pack(side=tk.RIGHT, padx=8)
        
        # Create file selection tab content
        self.files_frame = ctk.CTkFrame(self.tab_view.tab("File Selection"))
        self.files_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Add header
        self.files_header_frame = ctk.CTkFrame(self.files_frame, fg_color="transparent")
        self.files_header_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.files_title = ctk.CTkLabel(
            self.files_header_frame,
            text="Files to Transfer",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.files_title.pack(side=tk.LEFT)
        
        self.select_all_var = tk.BooleanVar(value=False)
        self.select_all_cb = ctk.CTkCheckBox(
            self.files_header_frame,
            text="Select All",
            variable=self.select_all_var,
            command=self.toggle_select_all,
            onvalue=True,
            offvalue=False
        )
        self.select_all_cb.pack(side=tk.RIGHT)
        
        # Add file list with scrollbar
        self.files_list_frame = ctk.CTkScrollableFrame(self.files_frame)
        self.files_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Column headers
        self.list_headers = ctk.CTkFrame(self.files_list_frame, fg_color="transparent")
        self.list_headers.pack(fill=tk.X, pady=(0, 8))
        
        ctk.CTkLabel(self.list_headers, text="", width=30).pack(side=tk.LEFT)  # Checkbox column
        ctk.CTkLabel(self.list_headers, text="", width=80).pack(side=tk.LEFT, padx=4)  # Thumbnail column
        ctk.CTkLabel(self.list_headers, text="Filename", width=200, anchor="w").pack(side=tk.LEFT, padx=4)
        ctk.CTkLabel(self.list_headers, text="Date Modified", width=150, anchor="w").pack(side=tk.LEFT, padx=4)
        ctk.CTkLabel(self.list_headers, text="Size", width=80, anchor="w").pack(side=tk.LEFT, padx=4)
        
        # File entries will be dynamically created
        self.file_entries = []
        
        # Add scan button at the bottom
        self.scan_button = ctk.CTkButton(
            self.files_frame,
            text="Scan Source Directory",
            command=self.scan_files,
            height=36
        )
        self.scan_button.pack(pady=(8, 0))
        
        # Initialize projects list
        self.refresh_projects()
        
        # Apply last selected project if we have it from config
        if hasattr(self, 'last_project') and self.last_project and self.project_combo_var.get() != self.last_project:
            try:
                projects = self.project_combo._values
                if self.last_project in projects:
                    print(f"Setting project to saved value: {self.last_project}")
                    self.project_combo.set(self.last_project)
                    self.project_combo_var.set(self.last_project)
                    self.update_destination_preview()
            except Exception as e:
                print(f"Error setting last project: {str(e)}")
    
    def toggle_select_all(self):
        """Toggle all file selections"""
        select_all = self.select_all_var.get()
        
        # Update all checkboxes
        for entry in self.file_entries:
            entry["var"].set(select_all)
        
        # Update selected files list
        if select_all:
            self.selected_files = [file[0] for file in self.files_to_transfer]
        else:
            self.selected_files = []
            
        # Update UI
        self.update_selection_status()
    
    def update_selection_status(self):
        """Update UI to show how many files are selected"""
        total = len(self.files_to_transfer)
        selected = len(self.selected_files)
        self.show_notification(f"{selected} of {total} files selected for transfer", "info")
    
    def create_placeholder_thumbnail(self):
        """Create a placeholder thumbnail"""
        # Create a blank image with a "Loading..." text
        img = Image.new('RGB', (70, 40), color=(50, 50, 50))
        
        # Convert to CTkImage for proper scaling
        return ctk.CTkImage(light_image=img, dark_image=img, size=(70, 40))
    
    def create_error_thumbnail(self):
        """Create an error thumbnail"""
        # Create a red blank image
        img = Image.new('RGB', (70, 40), color=(100, 30, 30))
        
        # Convert to CTkImage for proper scaling
        return ctk.CTkImage(light_image=img, dark_image=img, size=(70, 40))
    
    def start_thumbnail_worker(self):
        """Start the thumbnail generation worker thread"""
        if not self.thumbnail_processing:
            self.thumbnail_processing = True
            thread = threading.Thread(target=self.thumbnail_worker, daemon=True)
            thread.start()
    
    def thumbnail_worker(self):
        """Worker thread to process thumbnails in background"""
        try:
            while self.thumbnail_processing:
                try:
                    # Get file path and label widget from queue with timeout
                    file_path, label_widget = self.thumbnail_queue.get(timeout=1.0)
                    
                    # Generate thumbnail
                    thumbnail = self.generate_thumbnail(file_path)
                    
                    # Update label in main thread
                    self.root.after(0, lambda w=label_widget, t=thumbnail: w.configure(image=t))
                    
                    # Mark task as done
                    self.thumbnail_queue.task_done()
                except queue.Empty:
                    # No more thumbnails to process
                    if not self.thumbnail_queue.unfinished_tasks:
                        # If queue is empty and we're done with all tasks
                        time.sleep(0.1)  # Prevent CPU thrashing
                except Exception as e:
                    print(f"Error in thumbnail worker: {str(e)}")
                    time.sleep(0.1)  # Prevent CPU thrashing on repeated errors
        finally:
            self.thumbnail_processing = False
    
    def generate_thumbnail(self, file_path):
        """Generate a thumbnail for the given video file"""
        if file_path in self.thumbnail_cache:
            return self.thumbnail_cache[file_path]
            
        try:
            # Use OpenCV to capture a frame
            cap = cv2.VideoCapture(file_path)
            success, frame = cap.read()
            cap.release()  # Release the video capture resource immediately
            
            if success:
                # Convert from BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize to thumbnail size
                frame = cv2.resize(frame, (70, 40))
                
                # Convert to PIL Image
                image = Image.fromarray(frame)
                
                # Convert to CTkImage for proper scaling
                ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(70, 40))
                
                # Store in cache
                self.thumbnail_cache[file_path] = ctk_image
                
                # Return the image
                return ctk_image
            else:
                # Return an error thumbnail
                error_thumb = self.create_error_thumbnail()
                self.thumbnail_cache[file_path] = error_thumb
                return error_thumb
                
        except Exception as e:
            print(f"Error creating thumbnail: {str(e)}")
            # Return an error thumbnail
            error_thumb = self.create_error_thumbnail()
            self.thumbnail_cache[file_path] = error_thumb
            return error_thumb
    
    def toggle_file_selection(self, file_path, var):
        """Handle toggling file selection"""
        is_selected = var.get()
        
        if is_selected and file_path not in self.selected_files:
            self.selected_files.append(file_path)
        elif not is_selected and file_path in self.selected_files:
            self.selected_files.remove(file_path)
            
        # Update Select All checkbox
        if len(self.selected_files) == len(self.files_to_transfer):
            self.select_all_var.set(True)
        else:
            self.select_all_var.set(False)
            
        # Update status
        self.update_selection_status()
    
    def clear_file_list(self):
        """Clear the file list UI"""
        for entry in self.file_entries:
            for widget in entry["frame"].winfo_children():
                widget.destroy()
            entry["frame"].destroy()
        
        self.file_entries = []
        self.selected_files = []
    
    def scan_files(self):
        """Scan the source directory for video files and populate the list"""
        source_path = self.source_entry.get().strip()
        
        if not source_path or not os.path.exists(source_path):
            self.show_notification("Please select a valid source folder", "warning")
            return
            
        self.source_path = source_path
        self.show_notification(f"Scanning {source_path} for video files...", "info")
        
        # Clear current list
        self.clear_file_list()
        
        # Reset files to transfer
        self.files_to_transfer = []
        
        # Start scan in a background thread to keep UI responsive
        threading.Thread(target=self.scan_files_thread, args=(source_path,), daemon=True).start()
    
    def scan_files_thread(self, source_path):
        """Background thread for scanning files"""
        try:
            # Find all video files
            file_list = []
            video_extensions = ['.mp4', '.mov', '.avi', '.mxf', '.m4v']
            
            for root, _, files in os.walk(source_path):
                for file in files:
                    # Check if it's a video file
                    ext = os.path.splitext(file)[1].lower()
                    if ext in video_extensions:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, source_path)
                        
                        # Get file info without opening the file
                        file_stat = os.stat(file_path)
                        mod_time = datetime.fromtimestamp(file_stat.st_mtime)
                        file_size = file_stat.st_size
                        
                        # Add to list
                        file_list.append((file_path, rel_path, mod_time, file_size))
            
            # Sort by modification time (newest first)
            file_list.sort(key=lambda x: x[2], reverse=True)
            
            # Update UI in main thread
            def update_ui():
                # Store the files in instance variable
                self.files_to_transfer = file_list
                
                # Files are not selected by default
                self.selected_files = []
                self.select_all_var.set(False)
                
                # Add to UI
                for i, (file_path, rel_path, mod_time, file_size) in enumerate(self.files_to_transfer):
                    self.add_file_entry(i, file_path, rel_path, mod_time, file_size)
                
                # Update status
                self.show_notification(f"Found {len(self.files_to_transfer)} video files", "success")
                self.tab_view.set("File Selection")  # Switch to file selection tab
                
            # Schedule UI update in main thread
            self.root.after(0, update_ui)
            
        except Exception as e:
            def show_error():
                self.show_notification(f"Error scanning files: {str(e)}", "error")
            self.root.after(0, show_error)
    
    def add_file_entry(self, index, file_path, rel_path, mod_time, file_size):
        """Add a file entry to the list"""
        # Create the entry frame
        entry_frame = ctk.CTkFrame(self.files_list_frame)
        entry_frame.pack(fill=tk.X, pady=2)
        
        # Checkbox for selection
        var = tk.BooleanVar(value=False)  # Not selected by default
        checkbox = ctk.CTkCheckBox(
            entry_frame, 
            text="", 
            variable=var,
            onvalue=True,
            offvalue=False,
            width=30,
            command=lambda p=file_path, v=var: self.toggle_file_selection(p, v)
        )
        checkbox.pack(side=tk.LEFT)
        
        # Add thumbnail placeholder initially, then queue up for real thumbnail
        thumb_label = ctk.CTkLabel(entry_frame, text="", image=self.placeholder_img)
        thumb_label.pack(side=tk.LEFT, padx=4)
        
        # Queue this file for thumbnail generation
        self.thumbnail_queue.put((file_path, thumb_label))
        
        # Start the thumbnail worker if not already running
        if not self.thumbnail_processing:
            self.start_thumbnail_worker()
        
        # Filename (just the base name, not the full path)
        filename = os.path.basename(file_path)
        file_label = ctk.CTkLabel(
            entry_frame, 
            text=filename, 
            width=200,
            anchor="w",
            justify="left"
        )
        file_label.pack(side=tk.LEFT, padx=4)
        
        # Date modified
        date_str = mod_time.strftime("%Y-%m-%d %H:%M")
        date_label = ctk.CTkLabel(
            entry_frame, 
            text=date_str, 
            width=150,
            anchor="w"
        )
        date_label.pack(side=tk.LEFT, padx=4)
        
        # File size
        size_str = self.format_size(file_size)
        size_label = ctk.CTkLabel(
            entry_frame, 
            text=size_str, 
            width=80,
            anchor="w"
        )
        size_label.pack(side=tk.LEFT, padx=4)
        
        # Store entry data
        self.file_entries.append({
            "frame": entry_frame,
            "checkbox": checkbox,
            "var": var,
            "file_path": file_path,
            "rel_path": rel_path
        })
    
    def start_transfer_with_selection(self):
        """Start transfer with the selected files"""
        # Use selected files instead of scanning everything
        if not self.selected_files:
            self.show_notification("No files selected for transfer", "warning")
            return
            
        self.source_path = self.source_entry.get().strip()
        selected_project = self.project_combo_var.get()
        
        if not self.source_path or not os.path.exists(self.source_path):
            self.show_notification("Please select a valid source folder", "warning")
            return
            
        if not selected_project:
            self.show_notification("Please select or create a project", "warning")
            return
            
        destination = os.path.join(self.destination_base_path, selected_project, "Rushes", "Camera")
        
        # Make sure destination exists
        if not os.path.exists(destination):
            try:
                os.makedirs(destination, exist_ok=True)
            except Exception as e:
                self.show_notification(f"Failed to create destination folder: {str(e)}", "error")
                return
        
        # Switch to the Transfer tab before starting
        self.tab_view.set("Transfer")
        
        # Start transfer in a separate thread
        self.transfer_in_progress = True
        self.transfer_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.show_notification(f"Starting transfer to {destination}", "info")
        self.current_transfer_thread = threading.Thread(
            target=self.transfer_selected_files, 
            args=(self.source_path, destination)
        )
        self.current_transfer_thread.daemon = True
        self.current_transfer_thread.start()
    
    def transfer_selected_files(self, source, destination):
        """Transfer only the selected files"""
        try:
            # Get information about the selected files
            files_to_transfer = []
            for file_path, rel_path, mod_time, file_size in self.files_to_transfer:
                if file_path in self.selected_files:
                    # Create corresponding destination path
                    dest_path = os.path.join(destination, rel_path)
                    files_to_transfer.append((file_path, dest_path))
            
            total_files = len(files_to_transfer)
            completed_files = 0
            total_size = sum(os.path.getsize(src) for src, _ in files_to_transfer)
            transferred_size = 0
            start_time = time.time()
            
            self.update_ui(0, total_files, completed_files, "Starting transfer...", "--:--")
            self.show_notification(f"Found {total_files} video files to transfer ({self.format_size(total_size)} total)", "info")
            
            for src, dest in files_to_transfer:
                if not self.transfer_in_progress:
                    self.update_ui(0, total_files, completed_files, "Transfer cancelled", "--:--")
                    # Reset UI elements
                    self.root.after(0, lambda: self.current_file_label.configure(text="None"))
                    self.root.after(0, lambda: self.file_progress_bar.set(0))
                    self.root.after(0, lambda: self.file_size_label.configure(text="0 MB"))
                    self.root.after(0, lambda: self.speed_label.configure(text="0 MB/s"))
                    self.show_notification(f"Transfer cancelled. {completed_files} of {total_files} files were transferred.", "warning")
                    return
                
                # Update current file info
                filename = os.path.basename(src)
                self.root.after(0, lambda: self.current_file_label.configure(text=filename))
                
                file_size = os.path.getsize(src)
                self.update_ui(
                    transferred_size / total_size if total_size > 0 else 0, 
                    total_files, 
                    completed_files,
                    f"Processing {filename}...",
                    self.estimate_time(start_time, transferred_size, total_size)
                )
                
                # Copy the file with progress tracking
                success = self.copy_with_progress(src, dest)
                
                if success:
                    transferred_size += file_size
                    completed_files += 1
                
                self.update_ui(
                    transferred_size / total_size if total_size > 0 else 0, 
                    total_files, 
                    completed_files,
                    f"Transferred {completed_files} of {total_files} files",
                    self.estimate_time(start_time, transferred_size, total_size)
                )
            
            self.update_ui(1.0, total_files, completed_files, "Transfer complete!", "--:--")
            self.root.after(0, lambda: self.current_file_label.configure(text="None"))
            self.root.after(0, lambda: self.file_progress_bar.set(0))
            self.root.after(0, lambda: self.file_size_label.configure(text="0 MB"))
            self.root.after(0, lambda: self.speed_label.configure(text="0 MB/s"))
            
            self.show_notification(f"Transfer completed successfully! {completed_files} files transferred ({self.format_size(transferred_size)}).", "success")
            
        except Exception as e:
            self.show_notification(f"Transfer failed: {str(e)}", "error")
            self.update_ui(0, 0, 0, f"Error: {str(e)}", "--:--")
        finally:
            self.transfer_in_progress = False
            self.root.after(0, lambda: self.transfer_button.configure(state="normal"))
            self.root.after(0, lambda: self.cancel_button.configure(state="disabled"))
    
    def show_notification(self, message, message_type="info"):
        """Display a notification in the notification text box"""
        # Set color based on message type
        color_map = {
            "info": "white",
            "success": self.success_color,
            "warning": self.warning_color,
            "error": self.error_color
        }
        color = color_map.get(message_type, "white")
        
        # Get current time for timestamp
        timestamp = time.strftime("%H:%M:%S")
        
        # Enable the text box, insert message, and scroll to the end
        self.notification_text.configure(state="normal")
        self.notification_text.insert("end", f"[{timestamp}] ", "timestamp")
        self.notification_text.insert("end", f"{message}\n", message_type)
        
        # Configure tags with colors
        self.notification_text.tag_config("timestamp", foreground="#aaaaaa")
        self.notification_text.tag_config(message_type, foreground=color)
        
        # Autoscroll to the end
        self.notification_text.see("end")
        self.notification_text.configure(state="disabled")
        
        # Print to console as well
        print(f"{message_type.upper()}: {message}")
    
    def load_config(self):
        """Load saved configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                print(f"Loading configuration from {self.config_file}")
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                print(f"Config loaded: {config}")
                
                # Load source path
                if 'source_path' in config and config['source_path']:
                    self.source_path = config['source_path']
                    print(f"Setting source path to: {self.source_path}")
                
                # Load destination base path
                if 'destination_base_path' in config and config['destination_base_path']:
                    self.destination_base_path = config['destination_base_path']
                    print(f"Setting destination base path to: {self.destination_base_path}")
                
                # Store last project to apply after UI setup
                if 'last_project' in config and config['last_project']:
                    self.last_project = config['last_project']
                    print(f"Stored last project: {self.last_project}")
                else:
                    self.last_project = ""
                
                self.config_loaded = True
            else:
                print(f"Configuration file {self.config_file} not found")
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
    
    def save_config(self):
        """Save current configuration to JSON file"""
        try:
            # Get source path from entry in case it was manually edited
            entered_source = self.source_entry.get().strip()
            if entered_source:
                self.source_path = entered_source
            
            # Get current project selection
            current_project = self.project_combo_var.get()
                
            config = {
                'source_path': self.source_path if self.source_path else "",
                'destination_base_path': self.destination_base_path,
                'last_project': current_project
            }
            
            print(f"Saving configuration: {config}")
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
            print(f"Configuration saved to {self.config_file}")
            
            # Also update our last_project attribute
            self.last_project = current_project
        except Exception as e:
            print(f"Error saving configuration: {str(e)}")
    
    def on_closing(self):
        """Handle window close event"""
        if self.transfer_in_progress:
            # Instead of a popup, we'll just show a confirmation in the UI
            self.show_notification("A transfer is in progress. Click Cancel first before closing.", "warning")
            return
        
        # Save current configuration
        self.save_config()
        
        # Close the window
        self.root.destroy()
    
    def browse_source(self):
        path = filedialog.askdirectory(title="Select Memory Card Clips Folder")
        if path:
            self.source_path = path
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, path)
            # Save configuration after browsing
            self.save_config()
            self.show_notification(f"Source location set to: {path}", "success")
    
    def auto_detect_card(self):
        # Try to find the memory card at standard locations
        potential_paths = ["G:\\M4ROOT\\CLIP"]
        
        for path in potential_paths:
            if os.path.exists(path):
                self.source_path = path
                self.source_entry.delete(0, tk.END)
                self.source_entry.insert(0, path)
                # Save configuration after auto-detecting
                self.save_config()
                self.show_notification(f"Memory card found at {path}", "success")
                return
        
        self.show_notification("Memory card not detected. Please connect it or browse manually.", "warning")
    
    def refresh_projects(self):
        try:
            if os.path.exists(self.destination_base_path):
                projects = [d for d in os.listdir(self.destination_base_path) 
                            if os.path.isdir(os.path.join(self.destination_base_path, d))]
                
                # Store the currently selected project before updating
                current_selection = self.project_combo_var.get() if hasattr(self, 'project_combo_var') else ""
                
                self.project_combo.configure(values=projects)
                
                # If we had a selection and it's still valid, restore it
                if current_selection and current_selection in projects:
                    self.project_combo.set(current_selection)
                    self.project_combo_var.set(current_selection)
                    self.update_destination_preview()
                # Otherwise, select first project if available and we don't have a saved last project
                elif projects and not (hasattr(self, 'last_project') and self.last_project):
                    self.project_combo.set(projects[0])
                    self.project_combo_var.set(projects[0])
                    self.update_destination_preview()
                
                self.show_notification(f"Found {len(projects)} projects", "info")
        except Exception as e:
            self.show_notification(f"Failed to load projects: {str(e)}", "error")
    
    def create_project(self):
        project_name = self.new_project_entry.get().strip()
        if not project_name:
            self.show_notification("Please enter a project name", "warning")
            return
            
        project_path = os.path.join(self.destination_base_path, project_name)
        rushes_path = os.path.join(project_path, "Rushes", "Camera")
        
        try:
            if not os.path.exists(rushes_path):
                os.makedirs(rushes_path, exist_ok=True)
                self.show_notification(f"Project '{project_name}' created successfully", "success")
                self.refresh_projects()
                # Select the newly created project
                self.project_combo.set(project_name)
                self.project_combo_var.set(project_name)
                self.update_destination_preview()
                # Save configuration after creating a new project
                self.save_config()
                # Clear the new project entry
                self.new_project_entry.delete(0, tk.END)
            else:
                self.show_notification(f"Project '{project_name}' already exists", "info")
        except Exception as e:
            self.show_notification(f"Failed to create project: {str(e)}", "error")
    
    def on_project_selected(self, choice):
        """Handler for when a project is selected from the combobox"""
        self.update_destination_preview()
    
    def update_destination_preview(self):
        selected_project = self.project_combo_var.get()
        if selected_project:
            destination = os.path.join(self.destination_base_path, selected_project, "Rushes", "Camera")
            self.destination_label.configure(text=destination)
            # Save configuration after changing project
            self.save_config()
        else:
            self.destination_label.configure(text="")
    
    def start_transfer(self):
        if not self.files_to_transfer:
            # If no files have been scanned yet, scan them first
            self.scan_files()
            # After scanning, call transfer with selection
            if self.files_to_transfer:
                self.start_transfer_with_selection()
        else:
            # Files already scanned, start transfer with selection
            self.start_transfer_with_selection()
    
    def format_size(self, size_bytes):
        """Convert bytes to a human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0 or unit == 'GB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
    
    def copy_with_progress(self, src, dst):
        """Copy a file with progress updates"""
        self.current_file_size = os.path.getsize(src)
        self.current_file_transferred = 0
        self.transfer_start_time = time.time()
        
        # Update UI with file size
        self.root.after(0, lambda: self.file_size_label.configure(
            text=f"{self.format_size(self.current_file_size)}"
        ))
        self.root.after(0, lambda: self.file_progress_bar.set(0))
        
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        # If destination exists and has same size, skip it
        if os.path.exists(dst) and os.path.getsize(dst) == self.current_file_size:
            self.show_notification(f"Skipping duplicate file: {os.path.basename(src)}", "info")
            return True  # Skip file
        
        buffer_size = 1024 * 1024  # 1MB buffer
        last_update_time = time.time()
        last_bytes = 0
        
        try:
            with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
                while True:
                    if not self.transfer_in_progress:
                        # Transfer was canceled - close file handles and delete the partial file
                        fdst.close()  # Explicitly close file handle
                        if os.path.exists(dst):
                            try:
                                os.remove(dst)
                                print(f"Deleted partial file: {dst}")
                                self.show_notification(f"Deleted partial file: {os.path.basename(dst)}", "info")
                            except Exception as e:
                                print(f"Error deleting partial file {dst}: {str(e)}")
                                self.show_notification(f"Error deleting partial file: {str(e)}", "error")
                        return False  # Cancelled
                    
                    buf = fsrc.read(buffer_size)
                    if not buf:
                        break
                    
                    fdst.write(buf)
                    self.current_file_transferred += len(buf)
                    
                    # Update progress every 0.2 seconds to avoid UI freeze
                    current_time = time.time()
                    if current_time - last_update_time >= 0.2:
                        progress = (self.current_file_transferred / self.current_file_size)
                        
                        # Calculate transfer speed
                        elapsed = current_time - last_update_time
                        bytes_since_last = self.current_file_transferred - last_bytes
                        speed = bytes_since_last / elapsed if elapsed > 0 else 0
                        
                        def update_ui():
                            self.file_progress_bar.set(progress)
                            self.speed_label.configure(text=f"{self.format_size(speed)}/s")
                        
                        self.root.after(0, update_ui)
                        
                        last_update_time = current_time
                        last_bytes = self.current_file_transferred
            
            # Ensure progress is 100% at the end
            self.root.after(0, lambda: self.file_progress_bar.set(1.0))
            return True  # Successfully copied
        except Exception as e:
            # Error during copy - clean up the partial file
            print(f"Error during file copy: {str(e)}")
            self.show_notification(f"Error copying file: {str(e)}", "error")
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                    print(f"Deleted partial file after error: {dst}")
                    self.show_notification(f"Deleted partial file after error", "info")
                except Exception as delete_error:
                    print(f"Error deleting partial file after error: {str(delete_error)}")
                    self.show_notification(f"Error deleting partial file: {str(delete_error)}", "error")
            return False
    
    def update_ui(self, progress_percentage, total_files, completed_files, status_text, time_text):
        def update():
            self.progress_bar.set(progress_percentage)
            self.status_label.configure(text=status_text)
            self.time_label.configure(text=time_text)
            self.files_label.configure(text=f"{completed_files}/{total_files}")
        
        self.root.after(0, update)
    
    def estimate_time(self, start_time, transferred_size, total_size):
        if transferred_size == 0:
            return "--:--"
        
        elapsed_time = time.time() - start_time
        if elapsed_time == 0:
            return "--:--"
            
        bytes_per_second = transferred_size / elapsed_time
        if bytes_per_second == 0:
            return "--:--"
            
        remaining_bytes = total_size - transferred_size
        remaining_seconds = remaining_bytes / bytes_per_second
        
        # Format the time
        minutes, seconds = divmod(int(remaining_seconds), 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def cancel_transfer(self):
        if self.transfer_in_progress:
            # Show a message that we're canceling
            self.status_label.configure(text="Canceling transfer...")
            # Set the flag to indicate cancellation
            self.transfer_in_progress = False
            # Disable the cancel button to prevent multiple clicks
            self.cancel_button.configure(state="disabled")
            # Show message in notification area instead of popup
            self.show_notification("Transfer is being cancelled. Any partially transferred files will be deleted.", "warning")


def main():
    root = ctk.CTk()
    app = RushesTransferApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
