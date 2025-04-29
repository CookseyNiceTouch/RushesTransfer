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

# Set appearance mode and default color theme
ctk.set_appearance_mode("dark")  # Options: "Dark", "Light", "System"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"

class RushesTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rushes Transfer Tool")
        self.root.geometry("900x750")
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
    
    def setup_ui(self):
        # Main frame that fills the window
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header with app name
        self.header_label = ctk.CTkLabel(
            self.main_frame,
            text="Rushes Transfer Tool",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.header_label.pack(pady=(0, 20))
        
        # Source section
        self.source_frame = ctk.CTkFrame(self.main_frame)
        self.source_frame.pack(fill=tk.X, pady=10)
        
        self.source_label = ctk.CTkLabel(
            self.source_frame,
            text="Memory Card Clips Location",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.source_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self.source_entry_frame = ctk.CTkFrame(self.source_frame, fg_color="transparent")
        self.source_entry_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.source_entry = ctk.CTkEntry(self.source_entry_frame, placeholder_text="Path to memory card clips", height=35)
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Set source entry value if we have it from config
        if self.source_path:
            self.source_entry.insert(0, self.source_path)
        
        self.browse_button = ctk.CTkButton(
            self.source_entry_frame,
            text="Browse",
            command=self.browse_source,
            width=100,
            height=35
        )
        self.browse_button.pack(side=tk.LEFT, padx=5)
        
        self.auto_detect_button = ctk.CTkButton(
            self.source_entry_frame,
            text="Auto-Detect",
            command=self.auto_detect_card,
            width=100,
            height=35
        )
        self.auto_detect_button.pack(side=tk.LEFT)
        
        # Project section
        self.project_frame = ctk.CTkFrame(self.main_frame)
        self.project_frame.pack(fill=tk.X, pady=10)
        
        self.project_label = ctk.CTkLabel(
            self.project_frame,
            text="Project Selection",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.project_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Existing project selection
        self.project_select_frame = ctk.CTkFrame(self.project_frame, fg_color="transparent")
        self.project_select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.project_combo_label = ctk.CTkLabel(self.project_select_frame, text="Select Project:")
        self.project_combo_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.project_combo_var = tk.StringVar()
        self.project_combo = ctk.CTkOptionMenu(
            self.project_select_frame,
            variable=self.project_combo_var,
            values=[],
            command=self.on_project_selected,
            width=300,
            height=35
        )
        self.project_combo.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        self.refresh_button = ctk.CTkButton(
            self.project_select_frame,
            text="Refresh",
            command=self.refresh_projects,
            width=100,
            height=35
        )
        self.refresh_button.pack(side=tk.LEFT)
        
        # New project creation
        self.new_project_frame = ctk.CTkFrame(self.project_frame, fg_color="transparent")
        self.new_project_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.new_project_label = ctk.CTkLabel(self.new_project_frame, text="New Project:")
        self.new_project_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.new_project_entry = ctk.CTkEntry(
            self.new_project_frame,
            placeholder_text="Enter new project name",
            height=35
        )
        self.new_project_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        self.create_button = ctk.CTkButton(
            self.new_project_frame,
            text="Create",
            command=self.create_project,
            width=100,
            height=35
        )
        self.create_button.pack(side=tk.LEFT)
        
        # Destination preview
        self.dest_frame = ctk.CTkFrame(self.main_frame)
        self.dest_frame.pack(fill=tk.X, pady=10)
        
        self.dest_label = ctk.CTkLabel(
            self.dest_frame,
            text="Destination",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.dest_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self.dest_path_frame = ctk.CTkFrame(self.dest_frame, fg_color="transparent")
        self.dest_path_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.dest_path_label = ctk.CTkLabel(self.dest_path_frame, text="Rushes will be copied to:")
        self.dest_path_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.destination_label = ctk.CTkLabel(self.dest_path_frame, text="")
        self.destination_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Transfer progress section
        self.progress_frame = ctk.CTkFrame(self.main_frame)
        self.progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Transfer Progress",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.progress_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Overall progress
        self.overall_progress_frame = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        self.overall_progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.overall_progress_label = ctk.CTkLabel(self.overall_progress_frame, text="Overall Progress:")
        self.overall_progress_label.pack(side=tk.LEFT, padx=(0, 10), pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self.overall_progress_frame, height=15)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)
        self.progress_bar.set(0)
        
        # Current file progress
        self.file_info_frame = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        self.file_info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.current_file_header = ctk.CTkLabel(self.file_info_frame, text="Current File:", anchor=tk.W)
        self.current_file_header.grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.current_file_label = ctk.CTkLabel(self.file_info_frame, text="None", anchor=tk.W)
        self.current_file_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.file_progress_label = ctk.CTkLabel(self.file_info_frame, text="File Progress:", anchor=tk.W)
        self.file_progress_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.file_progress_bar = ctk.CTkProgressBar(self.file_info_frame, height=15)
        self.file_progress_bar.grid(row=1, column=1, sticky=tk.EW, pady=2)
        self.file_progress_bar.set(0)
        
        self.file_size_header = ctk.CTkLabel(self.file_info_frame, text="File Size:", anchor=tk.W)
        self.file_size_header.grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.file_size_label = ctk.CTkLabel(self.file_info_frame, text="0 MB", anchor=tk.W)
        self.file_size_label.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        self.speed_header = ctk.CTkLabel(self.file_info_frame, text="Transfer Speed:", anchor=tk.W)
        self.speed_header.grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.speed_label = ctk.CTkLabel(self.file_info_frame, text="0 MB/s", anchor=tk.W)
        self.speed_label.grid(row=3, column=1, sticky=tk.W, pady=2)
        
        # Transfer status
        self.status_frame = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_header = ctk.CTkLabel(self.status_frame, text="Status:", anchor=tk.W)
        self.status_header.grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.status_label = ctk.CTkLabel(self.status_frame, text="Ready", anchor=tk.W)
        self.status_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        self.time_header = ctk.CTkLabel(self.status_frame, text="Time Remaining:", anchor=tk.W)
        self.time_header.grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.time_label = ctk.CTkLabel(self.status_frame, text="--:--", anchor=tk.W)
        self.time_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        self.files_header = ctk.CTkLabel(self.status_frame, text="Files:", anchor=tk.W)
        self.files_header.grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.files_label = ctk.CTkLabel(self.status_frame, text="0/0", anchor=tk.W)
        self.files_label.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # Configure grid column expansion
        self.file_info_frame.columnconfigure(1, weight=1)
        self.status_frame.columnconfigure(1, weight=1)
        
        # Add notification area
        self.notification_frame = ctk.CTkFrame(self.main_frame)
        self.notification_frame.pack(fill=tk.X, pady=10)
        
        self.notification_label = ctk.CTkLabel(
            self.notification_frame,
            text="Notifications",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.notification_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self.notification_text = ctk.CTkTextbox(
            self.notification_frame,
            height=80,
            wrap="word",
            font=ctk.CTkFont(size=13)
        )
        self.notification_text.pack(fill=tk.X, padx=10, pady=5)
        self.notification_text.insert("1.0", "Welcome to Rushes Transfer Tool\n")
        self.notification_text.configure(state="disabled")
        
        # Action buttons
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.pack(fill=tk.X, pady=10)
        
        self.transfer_button = ctk.CTkButton(
            self.button_frame,
            text="Start Transfer",
            command=self.start_transfer,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.transfer_button.pack(side=tk.RIGHT, padx=10)
        
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self.cancel_transfer,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            state="disabled",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.cancel_button.pack(side=tk.RIGHT, padx=10)
        
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
        
        # Start transfer in a separate thread
        self.transfer_in_progress = True
        self.transfer_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.show_notification(f"Starting transfer to {destination}", "info")
        self.current_transfer_thread = threading.Thread(
            target=self.transfer_files, 
            args=(self.source_path, destination)
        )
        self.current_transfer_thread.daemon = True
        self.current_transfer_thread.start()
    
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
    
    def transfer_files(self, source, destination):
        try:
            # Get list of files to transfer
            files_to_transfer = []
            for root, _, files in os.walk(source):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, source)
                    dest_path = os.path.join(destination, rel_path)
                    
                    # Only transfer video files
                    ext = os.path.splitext(file)[1].lower()
                    video_extensions = ['.mp4', '.mov', '.avi', '.mxf', '.m4v']
                    if ext in video_extensions:
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
