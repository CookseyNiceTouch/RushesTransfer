import os
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
import threading
import time
from datetime import datetime

from file_manager import FileManager
from cache_manager import CacheManager
from ui_components import UIComponents

class RushesTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rushes Transfer Tool")
        self.root.geometry("850x680")
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
        self.metadata_cache_file = "rushes_transfer_metadata_cache.json"
        self.thumbnails_dir = "thumbnails"
        self.config_loaded = False
        self.files_to_transfer = []
        self.selected_files = []
        
        # UI rate limiting to reduce CPU usage
        self.last_ui_update_time = 0
        self.ui_update_interval = 1000 // 120     # Target 120 fps (8.33ms)
        
        # Ensure thumbnails directory exists
        os.makedirs(self.thumbnails_dir, exist_ok=True)
        
        # Initialize managers
        self.cache_manager = CacheManager(self)
        self.file_manager = FileManager(self)
        self.ui = UIComponents(self)
        
        # Define colors
        self.accent_color = "#1f538d"
        self.success_color = "#00cc66"
        self.warning_color = "#ff9900"
        self.error_color = "#e74c3c"
        
        # Load configuration before setting up UI
        self.cache_manager.load_config()
        self.cache_manager.load_metadata_cache()
        
        # Setup UI
        self.setup_ui()
        
        # Set up event handler for when window closes
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Rate limit UI updates to reduce CPU usage
        self.setup_update_rate_limiting()
        
        # Automatically scan source path if available, with a delay to ensure UI is ready
        if self.source_path and os.path.exists(self.source_path):
            self.root.after(1000, self.initial_scan)
            
    def setup_ui(self):
        """Set up the main UI components"""
        self.ui.setup_main_ui()
        self.ui.setup_transfer_tab()
        self.ui.setup_file_selection_tab()
        
        # Add configure event handler to limit refresh rate during dragging
        self.root.bind("<Configure>", self.on_configure)
        
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
                
    def initial_scan(self):
        """Scan the source path on initial load"""
        if self.source_path and os.path.exists(self.source_path):
            # Set source in entry if not already set
            if not self.source_entry.get():
                self.source_entry.insert(0, self.source_path)
            self.file_manager.scan_files()
    
    def browse_source(self):
        """Browse for source directory"""
        path = filedialog.askdirectory(title="Select Memory Card Clips Folder")
        if path:
            self.source_path = path
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, path)
            # Save configuration after browsing
            self.cache_manager.save_config()
            self.ui.show_notification(f"Source location set to: {path}", "success")
    
    def browse_projects_dir(self):
        """Browse for projects root directory"""
        path = filedialog.askdirectory(title="Select Projects Root Directory")
        if path:
            self.destination_base_path = path
            # Update the projects directory label
            self.projects_dir_path.configure(text=self.destination_base_path)
            # Save configuration after browsing
            self.cache_manager.save_config()
            # Refresh projects list
            self.refresh_projects()
            self.ui.show_notification(f"Projects location set to: {path}", "success")
    
    def auto_detect_card(self):
        """Try to auto-detect memory card location"""
        # Try to find the memory card at standard locations
        potential_paths = ["G:\\M4ROOT\\CLIP"]
        
        for path in potential_paths:
            if os.path.exists(path):
                self.source_path = path
                self.source_entry.delete(0, tk.END)
                self.source_entry.insert(0, path)
                # Save configuration after auto-detecting
                self.cache_manager.save_config()
                self.ui.show_notification(f"Memory card found at {path}", "success")
                return
        
        self.ui.show_notification("Memory card not detected. Please connect it or browse manually.", "warning")
    
    def refresh_projects(self):
        """Refresh the list of available projects"""
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
                
                self.ui.show_notification(f"Found {len(projects)} projects", "info")
        except Exception as e:
            self.ui.show_notification(f"Failed to load projects: {str(e)}", "error")
    
    def create_project(self):
        """Create a new project folder"""
        project_name = self.new_project_entry.get().strip()
        if not project_name:
            self.ui.show_notification("Please enter a project name", "warning")
            return
            
        project_path = os.path.join(self.destination_base_path, project_name)
        rushes_path = os.path.join(project_path, "Rushes", "Camera")
        
        try:
            if not os.path.exists(rushes_path):
                os.makedirs(rushes_path, exist_ok=True)
                self.ui.show_notification(f"Project '{project_name}' created successfully", "success")
                self.refresh_projects()
                # Select the newly created project
                self.project_combo.set(project_name)
                self.project_combo_var.set(project_name)
                self.update_destination_preview()
                # Save configuration after creating a new project
                self.cache_manager.save_config()
                # Clear the new project entry
                self.new_project_entry.delete(0, tk.END)
            else:
                self.ui.show_notification(f"Project '{project_name}' already exists", "info")
        except Exception as e:
            self.ui.show_notification(f"Failed to create project: {str(e)}", "error")
    
    def on_project_selected(self, choice):
        """Handler for when a project is selected from the combobox"""
        self.update_destination_preview()
    
    def update_destination_preview(self):
        """Update the destination path preview based on selected project"""
        selected_project = self.project_combo_var.get()
        if selected_project:
            destination = os.path.join(self.destination_base_path, selected_project, "Rushes", "Camera")
            self.destination_label.configure(text=destination)
            # Save configuration after changing project
            self.cache_manager.save_config()
        else:
            self.destination_label.configure(text="")
    
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
        self.ui.show_notification(f"{selected} of {total} files selected for transfer", "info")
    
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
    
    def start_transfer_with_selection(self):
        """Start transfer with the selected files"""
        # Use selected files instead of scanning everything
        if not self.selected_files:
            self.ui.show_notification("No files selected for transfer", "warning")
            return
            
        self.source_path = self.source_entry.get().strip()
        selected_project = self.project_combo_var.get()
        
        if not self.source_path or not os.path.exists(self.source_path):
            self.ui.show_notification("Please select a valid source folder", "warning")
            return
            
        if not selected_project:
            self.ui.show_notification("Please select or create a project", "warning")
            return
            
        destination = os.path.join(self.destination_base_path, selected_project, "Rushes", "Camera")
        
        # Make sure destination exists
        if not os.path.exists(destination):
            try:
                os.makedirs(destination, exist_ok=True)
            except Exception as e:
                self.ui.show_notification(f"Failed to create destination folder: {str(e)}", "error")
                return
        
        # Switch to the Transfer tab before starting
        self.tab_view.set("Transfer")
        
        # Start transfer in a separate thread
        self.transfer_in_progress = True
        self.transfer_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.ui.show_notification(f"Starting transfer to {destination}", "info")
        self.current_transfer_thread = threading.Thread(
            target=self.file_manager.transfer_selected_files, 
            args=(self.source_path, destination)
        )
        self.current_transfer_thread.daemon = True
        self.current_transfer_thread.start()
    
    def start_transfer(self):
        """Start the transfer process"""
        if not self.files_to_transfer:
            # If no files have been scanned yet, scan them first
            self.file_manager.scan_files()
            # After scanning, call transfer with selection
            if self.files_to_transfer:
                self.start_transfer_with_selection()
        else:
            # Files already scanned, start transfer with selection
            self.start_transfer_with_selection()
    
    def cancel_transfer(self):
        """Cancel an in-progress transfer"""
        if self.transfer_in_progress:
            # Show a message that we're canceling
            self.status_label.configure(text="Canceling transfer...")
            # Set the flag to indicate cancellation
            self.transfer_in_progress = False
            # Disable the cancel button to prevent multiple clicks
            self.cancel_button.configure(state="disabled")
            # Show message in notification area instead of popup
            self.ui.show_notification("Transfer is being cancelled. Any partially transferred files will be deleted.", "warning")
    
    def finish_tab_switch(self):
        """Called after tab switching to reset the flag"""
        self.ui.tab_switching = False
        # Force a UI update
        self.root.update_idletasks()
    
    def on_closing(self):
        """Handle window close event"""
        if self.transfer_in_progress:
            # Instead of a popup, we'll just show a confirmation in the UI
            self.ui.show_notification("A transfer is in progress. Click Cancel first before closing.", "warning")
            return
        
        # Save current configuration and metadata cache
        self.cache_manager.save_config()
        self.cache_manager.save_metadata_cache()
        
        # Close the window
        self.root.destroy()

    def setup_update_rate_limiting(self):
        """Set up rate limiting for UI updates to reduce CPU usage"""
        # Override update_idletasks to prevent excessive updates
        original_update_idletasks = self.root.update_idletasks
        
        def rate_limited_update_idletasks():
            current_time = time.time() * 1000  # Convert to ms
            if current_time - self.last_ui_update_time >= self.ui_update_interval:
                self.last_ui_update_time = current_time
                original_update_idletasks()
                
        self.root.update_idletasks = rate_limited_update_idletasks
        
        # Override update to prevent excessive updates
        original_update = self.root.update
        
        def rate_limited_update():
            current_time = time.time() * 1000  # Convert to ms
            if current_time - self.last_ui_update_time >= self.ui_update_interval:
                self.last_ui_update_time = current_time
                original_update()
                
        self.root.update = rate_limited_update 

    def on_configure(self, event):
        """Handle window configure events (resizing, moving)"""
        # Only process events for the main window
        if event.widget == self.root:
            # Small sleep to limit refresh rate during window movement
            # This mitigates issues with high polling rate mice
            time.sleep(0.015)  # 15ms delay helps with 1000Hz mice 