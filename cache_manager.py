import os
import json
import hashlib
import threading
import time
import queue
from datetime import datetime
from PIL import Image
import cv2
import customtkinter as ctk

class CacheManager:
    def __init__(self, app):
        self.app = app
        
        # Initialize caches
        self.thumbnail_cache = {}
        self.file_metadata_cache = {}
        
        # Thumbnail processing setup
        self.thumbnail_queue = queue.Queue()
        self.thumbnail_processing = False
        
        # Maximum concurrent thumbnail generation threads
        self.max_thumbnail_threads = 4
        self.active_thumbnail_threads = 0
        self.thumbnail_thread_lock = threading.Lock()
        
        # Create a placeholder thumbnail for use while loading
        self.placeholder_img = self.create_placeholder_thumbnail()
        self.error_img = self.create_error_thumbnail()
    
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
            # Reduce from 4 to 2 worker threads to lower CPU usage
            self.max_thumbnail_threads = 2
            for _ in range(self.max_thumbnail_threads):
                thread = threading.Thread(target=self.thumbnail_worker, daemon=True)
                thread.start()
    
    def thumbnail_worker(self):
        """Worker thread to process thumbnails in background"""
        try:
            with self.thumbnail_thread_lock:
                self.active_thumbnail_threads += 1
                
            while self.thumbnail_processing:
                try:
                    # Get file path and label widget from queue with timeout
                    file_path, label_widget = self.thumbnail_queue.get(timeout=1.0)
                    
                    # Generate thumbnail (will check disk cache first)
                    thumbnail = self.generate_thumbnail(file_path)
                    
                    # Update label in main thread
                    self.app.root.after(0, lambda w=label_widget, t=thumbnail: w.configure(image=t))
                    
                    # Mark task as done
                    self.thumbnail_queue.task_done()
                    
                    # Add small delay between processing thumbnails to reduce CPU load
                    time.sleep(0.05)
                except queue.Empty:
                    # No more thumbnails to process
                    if not self.thumbnail_queue.unfinished_tasks:
                        # If queue is empty and we're done with all tasks
                        time.sleep(0.2)  # Increased from 0.1 to 0.2 seconds
                except Exception as e:
                    print(f"Error in thumbnail worker: {str(e)}")
                    time.sleep(0.2)  # Increased from 0.1 to 0.2 seconds
        finally:
            with self.thumbnail_thread_lock:
                self.active_thumbnail_threads -= 1
                if self.active_thumbnail_threads == 0:
                    self.thumbnail_processing = False
    
    def generate_thumbnail(self, file_path):
        """Generate a thumbnail for the given video file"""
        if file_path in self.thumbnail_cache:
            return self.thumbnail_cache[file_path]
        
        # Check if we have a saved thumbnail on disk
        disk_thumbnail = self.load_thumbnail_from_disk(file_path)
        if disk_thumbnail:
            return disk_thumbnail
            
        try:
            # Use OpenCV to capture a frame
            cap = cv2.VideoCapture(file_path)
            
            # Set frame position to 20% of the video to get a meaningful frame
            if cap.isOpened():
                # Get total frames
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                # Set position to 20% through
                if total_frames > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(total_frames * 0.2))
            
            success, frame = cap.read()
            cap.release()  # Release the video capture resource immediately
            
            if success:
                # Convert from BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize to thumbnail size - use a more efficient method
                frame = cv2.resize(frame, (70, 40), interpolation=cv2.INTER_NEAREST)
                
                # Convert to PIL Image
                image = Image.fromarray(frame)
                
                # Save the thumbnail to disk for future use
                self.save_thumbnail_to_disk(file_path, image)
                
                # Convert to CTkImage for proper scaling
                ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(70, 40))
                
                # Store in cache
                self.thumbnail_cache[file_path] = ctk_image
                
                # Update metadata to indicate thumbnail exists
                if file_path in self.file_metadata_cache:
                    self.file_metadata_cache[file_path]['has_thumbnail'] = True
                
                # Return the image
                return ctk_image
            else:
                # Return an error thumbnail
                self.thumbnail_cache[file_path] = self.error_img
                return self.error_img
                
        except Exception as e:
            print(f"Error creating thumbnail: {str(e)}")
            # Return an error thumbnail
            self.thumbnail_cache[file_path] = self.error_img
            return self.error_img
    
    def get_thumbnail_path(self, file_path):
        """Generate a unique path for the thumbnail file based on the source file path"""
        # Create a hash of the file path to use as the filename
        file_hash = hashlib.md5(file_path.encode()).hexdigest()
        return os.path.join(self.app.thumbnails_dir, f"{file_hash}.png")
    
    def save_thumbnail_to_disk(self, file_path, image):
        """Save a thumbnail to disk"""
        try:
            thumbnail_path = self.get_thumbnail_path(file_path)
            image.save(thumbnail_path, "PNG")
            return True
        except Exception as e:
            print(f"Error saving thumbnail to disk: {str(e)}")
            return False
    
    def load_thumbnail_from_disk(self, file_path):
        """Load a thumbnail from disk if it exists"""
        thumbnail_path = self.get_thumbnail_path(file_path)
        if os.path.exists(thumbnail_path):
            try:
                # Load the image from disk
                pil_image = Image.open(thumbnail_path)
                # Convert to CTkImage
                ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(70, 40))
                # Store in cache and return
                self.thumbnail_cache[file_path] = ctk_image
                return ctk_image
            except Exception as e:
                print(f"Error loading thumbnail from disk: {str(e)}")
        return None
    
    def clear_thumbnails(self):
        """Clear all thumbnails from disk"""
        try:
            for file in os.listdir(self.app.thumbnails_dir):
                file_path = os.path.join(self.app.thumbnails_dir, file)
                if os.path.isfile(file_path) and file.endswith('.png'):
                    os.remove(file_path)
            self.app.ui.show_notification("All thumbnails cleared from disk", "info")
        except Exception as e:
            self.app.ui.show_notification(f"Error clearing thumbnails: {str(e)}", "error")
    
    def add_file_to_metadata_cache(self, file_path, rel_path, mod_time, file_size):
        """Add or update a file in the metadata cache"""
        self.file_metadata_cache[file_path] = {
            'rel_path': rel_path,
            'mod_time': mod_time,
            'file_size': file_size,
            'last_checked': datetime.now(),
            'has_thumbnail': os.path.exists(self.get_thumbnail_path(file_path))
        }
    
    def is_file_in_cache(self, file_path):
        """Check if a file is in the metadata cache and if its metadata is still valid"""
        if file_path in self.file_metadata_cache:
            cached_data = self.file_metadata_cache[file_path]
            
            # Check if the file still exists
            if not os.path.exists(file_path):
                return False
                
            # Check if the file size has changed
            try:
                current_size = os.path.getsize(file_path)
                if current_size != cached_data.get('file_size', 0):
                    return False
                    
                # Check if modified time has changed
                current_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                cached_mod_time = cached_data.get('mod_time')
                
                if cached_mod_time and abs((current_mod_time - cached_mod_time).total_seconds()) > 2:
                    return False
                    
                return True
            except:
                return False
        return False
    
    def refresh_file_cache(self):
        """Clear the file metadata cache and rescan"""
        self.file_metadata_cache = {}  # Clear the metadata cache
        self.thumbnail_cache = {}      # Clear the thumbnail cache
        
        # Show notification
        self.app.ui.show_notification("Clearing cache and rescanning files...", "info")
        
        # Start a new scan
        self.app.file_manager.scan_files(force_scan=True)
    
    def load_config(self):
        """Load saved configuration from JSON file"""
        try:
            if os.path.exists(self.app.config_file):
                print(f"Loading configuration from {self.app.config_file}")
                with open(self.app.config_file, 'r') as f:
                    config = json.load(f)
                
                print(f"Config loaded: {config}")
                
                # Load source path
                if 'source_path' in config and config['source_path']:
                    self.app.source_path = config['source_path']
                    print(f"Setting source path to: {self.app.source_path}")
                
                # Load destination base path
                if 'destination_base_path' in config and config['destination_base_path']:
                    self.app.destination_base_path = config['destination_base_path']
                    print(f"Setting destination base path to: {self.app.destination_base_path}")
                
                # Store last project to apply after UI setup
                if 'last_project' in config and config['last_project']:
                    self.app.last_project = config['last_project']
                    print(f"Stored last project: {self.app.last_project}")
                else:
                    self.app.last_project = ""
                
                self.app.config_loaded = True
            else:
                print(f"Configuration file {self.app.config_file} not found")
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
    
    def save_config(self):
        """Save current configuration to JSON file"""
        try:
            # Get source path from entry in case it was manually edited
            entered_source = self.app.source_entry.get().strip()
            if entered_source:
                self.app.source_path = entered_source
            
            # Get current project selection
            current_project = self.app.project_combo_var.get()
                
            config = {
                'source_path': self.app.source_path if self.app.source_path else "",
                'destination_base_path': self.app.destination_base_path,
                'last_project': current_project
            }
            
            print(f"Saving configuration: {config}")
            
            with open(self.app.config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
            print(f"Configuration saved to {self.app.config_file}")
            
            # Also update our last_project attribute
            self.app.last_project = current_project
        except Exception as e:
            print(f"Error saving configuration: {str(e)}")
    
    def load_metadata_cache(self):
        """Load file metadata cache from disk"""
        try:
            if os.path.exists(self.app.metadata_cache_file):
                print(f"Loading metadata cache from {self.app.metadata_cache_file}")
                with open(self.app.metadata_cache_file, 'r') as f:
                    cached_data = json.load(f)
                    
                # Process the loaded data
                self.file_metadata_cache = {}
                for file_path, data in cached_data.items():
                    # Convert string dates back to datetime objects
                    if 'mod_time' in data:
                        try:
                            data['mod_time'] = datetime.fromisoformat(data['mod_time'])
                        except Exception as e:
                            print(f"Error converting date: {e}")
                            # If conversion fails, use current time
                            data['mod_time'] = datetime.now()
                            
                    if 'last_checked' in data:
                        try:
                            data['last_checked'] = datetime.fromisoformat(data['last_checked'])
                        except Exception as e:
                            print(f"Error converting last_checked date: {e}")
                            # If conversion fails, use current time
                            data['last_checked'] = datetime.now()
                            
                    self.file_metadata_cache[file_path] = data
                    
                print(f"Loaded metadata for {len(self.file_metadata_cache)} files")
        except Exception as e:
            print(f"Error loading metadata cache: {str(e)}")
            self.file_metadata_cache = {}
    
    def save_metadata_cache(self):
        """Save file metadata cache to disk"""
        try:
            # Convert the cache to a serializable format
            serializable_cache = {}
            for file_path, data in self.file_metadata_cache.items():
                serializable_data = data.copy()
                # Convert datetime objects manually
                if 'mod_time' in serializable_data and isinstance(serializable_data['mod_time'], datetime):
                    serializable_data['mod_time'] = serializable_data['mod_time'].isoformat()
                if 'last_checked' in serializable_data and isinstance(serializable_data['last_checked'], datetime):
                    serializable_data['last_checked'] = serializable_data['last_checked'].isoformat()
                serializable_cache[file_path] = serializable_data
                
            with open(self.app.metadata_cache_file, 'w') as f:
                json.dump(serializable_cache, f, indent=4)
                
            print(f"Saved metadata for {len(self.file_metadata_cache)} files")
        except Exception as e:
            print(f"Error saving metadata cache: {str(e)}") 