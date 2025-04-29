import os
import shutil
import threading
import time
from datetime import datetime

class FileManager:
    def __init__(self, app):
        self.app = app
        self.scanning_in_progress = False
        
    def scan_files(self, force_scan=False):
        """Scan the source directory for video files and populate the list
        
        Args:
            force_scan (bool): If True, forces a full scan ignoring cache
        """
        source_path = self.app.source_entry.get().strip()
        
        if not source_path or not os.path.exists(source_path):
            self.app.ui.show_notification("Please select a valid source folder", "warning")
            return
        
        # Check if scanning is already in progress
        if self.scanning_in_progress:
            self.app.ui.show_notification("File scanning already in progress", "warning")
            return
            
        self.scanning_in_progress = True
        self.app.source_path = source_path
        
        # Show different message based on force_scan
        if force_scan:
            self.app.ui.show_notification(f"Rescanning {source_path} for video files and changes...", "info")
        else:
            self.app.ui.show_notification(f"Scanning {source_path} for video files...", "info")
        
        # Clear current list
        self.app.clear_file_list()
        
        # Reset files to transfer
        self.app.files_to_transfer = []
        
        # Show scanning indicator
        self.app.status_label.configure(text="Scanning files...")
        
        # Switch to the file selection tab first, before scanning
        # This avoids the UI freeze when switching tabs after a scan
        self.app.tab_view.set("File Selection")
        
        # A small delay to ensure tab switch completes before scanning starts
        def delayed_scan():
            # Start scan in a background thread to keep UI responsive
            threading.Thread(target=self.scan_files_thread, args=(source_path, force_scan), daemon=True).start()
            
        self.app.root.after(50, delayed_scan)
    
    def scan_files_thread(self, source_path, force_scan=False):
        """Background thread for scanning files"""
        try:
            # Check if we already have a good cache for this directory and not forcing a scan
            if not force_scan and self.has_valid_cache_for_directory(source_path):
                self.app.ui.show_notification("Using cached file information for faster loading", "info")
                
                # Use fast path for existing cache
                self.use_cached_file_list(source_path)
                return
            
            # Otherwise, do a full scan
            # Find all video files
            file_list = []
            video_extensions = ['.mp4', '.mov', '.avi', '.mxf', '.m4v']
            
            # Track cache hits and new files for stats
            cache_hits = 0
            new_files = 0
            deleted_files = 0
            
            # Count total files for progress indication
            total_files = 0
            for root, _, files in os.walk(source_path):
                for file in files:
                    if os.path.splitext(file)[1].lower() in video_extensions:
                        total_files += 1
            
            # If forcing a scan with existing cache, prepare to check for deleted files
            existing_files_in_cache = set()
            if force_scan and self.app.cache_manager.file_metadata_cache:
                for file_path, data in self.app.cache_manager.file_metadata_cache.items():
                    if data.get('source_dir') == source_path:
                        existing_files_in_cache.add(file_path)
            
            # Set of files found in current scan
            current_files = set()
            
            # Update progress indicator
            def update_scan_progress(current, message):
                if total_files > 0:
                    percentage = current / total_files
                    self.app.root.after(0, lambda: self.app.ui.update_ui(percentage, total_files, 0, f"Scanning: {message}", "--:--"))
            
            # Track progress
            processed_files = 0
            
            for root, _, files in os.walk(source_path):
                for file in files:
                    # Check if it's a video file
                    ext = os.path.splitext(file)[1].lower()
                    if ext in video_extensions:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, source_path)
                        
                        # Add to set of current files
                        current_files.add(file_path)
                        
                        # Update progress
                        processed_files += 1
                        update_scan_progress(processed_files, f"{processed_files}/{total_files} - {file}")
                        
                        # Get fresh file info if forcing a scan or if not in cache
                        if force_scan or not self.app.cache_manager.is_file_in_cache(file_path):
                            # Get file info without opening the file
                            file_stat = os.stat(file_path)
                            mod_time = datetime.fromtimestamp(file_stat.st_mtime)
                            file_size = file_stat.st_size
                            
                            # Add to cache
                            self.app.cache_manager.add_file_to_metadata_cache(file_path, rel_path, mod_time, file_size)
                            new_files += 1
                        else:
                            # Use cached metadata
                            cached_data = self.app.cache_manager.file_metadata_cache[file_path]
                            mod_time = cached_data['mod_time']
                            file_size = cached_data['file_size']
                            cache_hits += 1
                        
                        # Track the source directory in the metadata
                        if file_path in self.app.cache_manager.file_metadata_cache:
                            self.app.cache_manager.file_metadata_cache[file_path]['source_dir'] = source_path
                        
                        # Add to list
                        file_list.append((file_path, rel_path, mod_time, file_size))
            
            # Check for deleted files
            if force_scan and existing_files_in_cache:
                deleted_files = existing_files_in_cache - current_files
                for file_path in deleted_files:
                    if file_path in self.app.cache_manager.file_metadata_cache:
                        del self.app.cache_manager.file_metadata_cache[file_path]
                deleted_files = len(deleted_files)
            
            # Sort by modification time (newest first)
            file_list.sort(key=lambda x: x[2], reverse=True)
            
            # Save the updated metadata cache
            self.app.cache_manager.save_metadata_cache()
            
            # Update UI in main thread - process in batches for better performance
            message = None
            if force_scan:
                message = f"Found {len(file_list)} video files ({new_files} new, {deleted_files} removed)"
            
            self.update_ui_with_file_list(file_list, cache_hits, new_files, message)
            
        except Exception as e:
            def show_error():
                self.app.ui.show_notification(f"Error scanning files: {str(e)}", "error")
                self.scanning_in_progress = False
                self.app.status_label.configure(text="Error scanning files")
            self.app.root.after(0, show_error)
    
    def has_valid_cache_for_directory(self, source_path):
        """Check if we have a valid cached file list for this directory"""
        # If cache is empty, definitely not valid
        if not self.app.cache_manager.file_metadata_cache:
            return False
            
        # Check for files from this source directory
        source_dir_files = [
            path for path, data in self.app.cache_manager.file_metadata_cache.items() 
            if data.get('source_dir') == source_path and os.path.exists(path)
        ]
        
        # If we have a good number of files from this directory
        return len(source_dir_files) > 0
    
    def use_cached_file_list(self, source_path):
        """Use the cached file list for faster loading"""
        try:
            # Get all files from this source directory
            cached_files = []
            for file_path, data in self.app.cache_manager.file_metadata_cache.items():
                if data.get('source_dir') == source_path and os.path.exists(file_path):
                    try:
                        rel_path = data.get('rel_path', '')
                        mod_time = data.get('mod_time')
                        file_size = data.get('file_size', 0)
                        cached_files.append((file_path, rel_path, mod_time, file_size))
                    except Exception as e:
                        print(f"Error processing cached file {file_path}: {str(e)}")
            
            # Skip files that no longer exist
            valid_files = [(path, rel, mod, size) for path, rel, mod, size in cached_files if os.path.exists(path)]
            
            # Sort by modification time (newest first)
            valid_files.sort(key=lambda x: x[2], reverse=True)
            
            # Update UI with this list - much faster than scanning
            self.update_ui_with_file_list(valid_files, len(valid_files), 0, "Using cached file list")
            
        except Exception as e:
            # Fall back to full scan if cache fails
            print(f"Error using cached file list: {str(e)}")
            # Start a full scan
            self.scan_files_thread(source_path)
    
    def update_ui_with_file_list(self, file_list, cache_hits=0, new_files=0, message=None):
        """Update the UI with a list of files, using batching for performance"""
        batch_size = 20  # Display files in batches
        
        def update_ui_batch(batch_start, files_added=0):
            end_index = min(batch_start + batch_size, len(file_list))
            current_batch = file_list[batch_start:end_index]
            
            # Files are not selected by default
            if batch_start == 0:  # Only on first batch
                self.app.files_to_transfer = file_list
                self.app.selected_files = []
                self.app.select_all_var.set(False)
            
            # Add batch to UI
            for i, (file_path, rel_path, mod_time, file_size) in enumerate(current_batch):
                # Check if we're dragging window - pause UI updates during drag
                if self.app.is_dragging:
                    # Resume from this point after dragging stops
                    self.app.root.after(50, lambda: update_ui_batch(batch_start, files_added))
                    return
                
                self.app.ui.add_file_entry(batch_start + i, file_path, rel_path, mod_time, file_size)
                files_added += 1
                
                # Update progress while adding files
                percentage = 1.0 if len(file_list) == 0 else files_added / len(file_list)
                self.app.ui.update_ui(percentage, len(file_list), 0, f"Loading files: {files_added}/{len(file_list)}", "--:--")
            
            # Schedule next batch if needed
            if end_index < len(file_list):
                self.app.root.after(5, lambda: update_ui_batch(end_index, files_added))
            else:
                # All batches done
                cache_message = message or f"Found {len(self.app.files_to_transfer)} video files (Cache: {cache_hits} hits, {new_files} new)"
                self.app.ui.show_notification(cache_message, "success")
                self.app.status_label.configure(text="Ready")
                self.scanning_in_progress = False
                self.app.ui.update_ui(0, 0, 0, "Ready", "--:--")
        
        # Start the batch update process with shorter delay
        self.app.root.after(0, lambda: update_ui_batch(0))
    
    def transfer_selected_files(self, source, destination):
        """Transfer only the selected files"""
        try:
            # Get information about the selected files
            files_to_transfer = []
            for file_path, rel_path, mod_time, file_size in self.app.files_to_transfer:
                if file_path in self.app.selected_files:
                    # Create corresponding destination path
                    dest_path = os.path.join(destination, rel_path)
                    files_to_transfer.append((file_path, dest_path))
            
            total_files = len(files_to_transfer)
            completed_files = 0
            total_size = sum(os.path.getsize(src) for src, _ in files_to_transfer)
            transferred_size = 0
            start_time = time.time()
            
            self.app.ui.update_ui(0, total_files, completed_files, "Starting transfer...", "--:--")
            self.app.ui.show_notification(f"Found {total_files} video files to transfer ({self.format_size(total_size)} total)", "info")
            
            for src, dest in files_to_transfer:
                if not self.app.transfer_in_progress:
                    self.app.ui.update_ui(0, total_files, completed_files, "Transfer cancelled", "--:--")
                    # Reset UI elements
                    self.app.root.after(0, lambda: self.app.current_file_label.configure(text="None"))
                    self.app.root.after(0, lambda: self.app.file_progress_bar.set(0))
                    self.app.root.after(0, lambda: self.app.file_size_label.configure(text="0 MB"))
                    self.app.root.after(0, lambda: self.app.speed_label.configure(text="0 MB/s"))
                    self.app.ui.show_notification(f"Transfer cancelled. {completed_files} of {total_files} files were transferred.", "warning")
                    return
                
                # Update current file info
                filename = os.path.basename(src)
                self.app.root.after(0, lambda: self.app.current_file_label.configure(text=filename))
                
                file_size = os.path.getsize(src)
                self.app.ui.update_ui(
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
                
                self.app.ui.update_ui(
                    transferred_size / total_size if total_size > 0 else 0, 
                    total_files, 
                    completed_files,
                    f"Transferred {completed_files} of {total_files} files",
                    self.estimate_time(start_time, transferred_size, total_size)
                )
            
            self.app.ui.update_ui(1.0, total_files, completed_files, "Transfer complete!", "--:--")
            self.app.root.after(0, lambda: self.app.current_file_label.configure(text="None"))
            self.app.root.after(0, lambda: self.app.file_progress_bar.set(0))
            self.app.root.after(0, lambda: self.app.file_size_label.configure(text="0 MB"))
            self.app.root.after(0, lambda: self.app.speed_label.configure(text="0 MB/s"))
            
            self.app.ui.show_notification(f"Transfer completed successfully! {completed_files} files transferred ({self.format_size(transferred_size)}).", "success")
            
        except Exception as e:
            self.app.ui.show_notification(f"Transfer failed: {str(e)}", "error")
            self.app.ui.update_ui(0, 0, 0, f"Error: {str(e)}", "--:--")
        finally:
            self.app.transfer_in_progress = False
            self.app.root.after(0, lambda: self.app.transfer_button.configure(state="normal"))
            self.app.root.after(0, lambda: self.app.cancel_button.configure(state="disabled"))
    
    def copy_with_progress(self, src, dst):
        """Copy a file with progress updates"""
        self.app.current_file_size = os.path.getsize(src)
        self.app.current_file_transferred = 0
        self.app.transfer_start_time = time.time()
        
        # Update UI with file size
        self.app.root.after(0, lambda: self.app.file_size_label.configure(
            text=f"{self.format_size(self.app.current_file_size)}"
        ))
        self.app.root.after(0, lambda: self.app.file_progress_bar.set(0))
        
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        # If destination exists and has same size, skip it
        if os.path.exists(dst) and os.path.getsize(dst) == self.app.current_file_size:
            self.app.ui.show_notification(f"Skipping duplicate file: {os.path.basename(src)}", "info")
            return True  # Skip file
        
        buffer_size = 1024 * 1024  # 1MB buffer
        last_update_time = time.time()
        last_bytes = 0
        
        try:
            with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
                while True:
                    if not self.app.transfer_in_progress:
                        # Transfer was canceled - close file handles and delete the partial file
                        fdst.close()  # Explicitly close file handle
                        if os.path.exists(dst):
                            try:
                                os.remove(dst)
                                print(f"Deleted partial file: {dst}")
                                self.app.ui.show_notification(f"Deleted partial file: {os.path.basename(dst)}", "info")
                            except Exception as e:
                                print(f"Error deleting partial file {dst}: {str(e)}")
                                self.app.ui.show_notification(f"Error deleting partial file: {str(e)}", "error")
                        return False  # Cancelled
                    
                    buf = fsrc.read(buffer_size)
                    if not buf:
                        break
                    
                    fdst.write(buf)
                    self.app.current_file_transferred += len(buf)
                    
                    # Update progress every 0.2 seconds to avoid UI freeze
                    current_time = time.time()
                    if current_time - last_update_time >= 0.2:
                        progress = (self.app.current_file_transferred / self.app.current_file_size)
                        
                        # Calculate transfer speed
                        elapsed = current_time - last_update_time
                        bytes_since_last = self.app.current_file_transferred - last_bytes
                        speed = bytes_since_last / elapsed if elapsed > 0 else 0
                        
                        def update_ui():
                            self.app.file_progress_bar.set(progress)
                            self.app.speed_label.configure(text=f"{self.format_size(speed)}/s")
                        
                        self.app.root.after(0, update_ui)
                        
                        last_update_time = current_time
                        last_bytes = self.app.current_file_transferred
            
            # Ensure progress is 100% at the end
            self.app.root.after(0, lambda: self.app.file_progress_bar.set(1.0))
            return True  # Successfully copied
        except Exception as e:
            # Error during copy - clean up the partial file
            print(f"Error during file copy: {str(e)}")
            self.app.ui.show_notification(f"Error copying file: {str(e)}", "error")
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                    print(f"Deleted partial file after error: {dst}")
                    self.app.ui.show_notification(f"Deleted partial file after error", "info")
                except Exception as delete_error:
                    print(f"Error deleting partial file after error: {str(delete_error)}")
                    self.app.ui.show_notification(f"Error deleting partial file: {str(delete_error)}", "error")
            return False
    
    def estimate_time(self, start_time, transferred_size, total_size):
        """Estimate the remaining time for a transfer"""
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
    
    def format_size(self, size_bytes):
        """Convert bytes to a human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0 or unit == 'GB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0 